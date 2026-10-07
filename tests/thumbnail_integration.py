"""Test thumbnail responses and persistence with Docker Compose."""

import concurrent.futures
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.request import urlopen
import zlib


ROOT = Path(__file__).resolve().parents[1]


def png(width, height):
    def chunk(kind, data):
        return (struct.pack("!I", len(data)) + kind + data
                + struct.pack("!I", zlib.crc32(kind + data)))

    pixels = b"".join(
        b"\0" + bytes(value for x in range(width)
                       for value in (x % 256, y % 256, (x * y) % 256))
        for y in range(height)
    )
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack("!2I5B", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(pixels)) + chunk(b"IEND", b""))


def main():
    port = int(os.environ.get("THUMBNAIL_TEST_PORT", "18089"))
    env = dict(os.environ, COMPOSE_PROJECT_NAME="little-jukebox-thumbnail-test",
               JUKEBOX_IMAGE="little-jukebox:local", JUKEBOX_PULL_POLICY="never",
               JUKEBOX_DOCKER_ALIAS="little-jukebox-thumbnail-test",
               JUKEBOX_BASE_PATH="/apps/thumbnail-test")
    base_url = f"http://127.0.0.1:{port}/apps/thumbnail-test/"
    workspace = ROOT / ".ai"
    workspace.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="thumbnail-test-", dir=workspace) as temporary:
        directory = Path(temporary)
        data = directory / "data"
        covers = data / "covers"
        covers.mkdir(parents=True)
        cache = directory / "cache"
        cache.mkdir(mode=0o777)
        cache.chmod(0o777)
        original = png(720, 400)
        for name in ("cover.png", "parallel.png", "replacement.png"):
            (covers / name).write_bytes(original)
        (covers / "small.png").write_bytes(png(120, 80))
        (covers / "broken.png").write_bytes(b"invalid image")
        (covers / "oversized.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"x" * (10 * 1024 * 1024))
        catalog = {"tracks": [
            {"id": "one", "title": "One", "cover": "covers/cover.png", "audio": "audio/one.mp3"},
            {"id": "two", "title": "Two", "cover": "covers/cover.png", "audio": "audio/two.mp3"},
            {"id": "external", "title": "External", "cover": "https://example.invalid/cover.png", "audio": "audio/three.mp3"},
        ]}
        (data / "catalog.json").write_text(json.dumps(catalog))
        override = directory / "compose.json"
        override.write_text(json.dumps({"services": {"web": {
            "ports": [f"127.0.0.1:{port}:8080"],
            "volumes": [
                {"type": "bind", "source": str(data), "target": "/data", "read_only": True},
                {"type": "bind", "source": str(cache), "target": "/var/cache/nginx/thumbnails"},
            ],
        }}}))
        command = ["docker", "compose", "--project-directory", str(ROOT),
                   "-f", str(ROOT / "docker-compose.yml"), "-f", str(override)]

        def compose(*args):
            subprocess.run(command + list(args), env=env, check=True)

        def fetch(path):
            started = time.monotonic()
            try:
                with urlopen(base_url + path, timeout=35) as response:
                    result = response.status, response.headers, response.read()
            except HTTPError as error:
                result = error.code, error.headers, error.read()
            return (*result, time.monotonic() - started)

        def ready():
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                try:
                    if fetch("")[0] == 200:
                        return
                except (URLError, TimeoutError, ConnectionError):
                    pass
                time.sleep(0.25)
            raise AssertionError("The application did not start")

        compose("config", "-q")
        try:
            compose("up", "-d")
            ready()
            compose("exec", "-T", "web", "nginx", "-t")
            cold = fetch("thumbs/cover.png?version=one")
            warm = fetch("thumbs/cover.png?version=one")
            assert cold[0] == warm[0] == 200
            assert cold[1]["X-Thumbnail-Cache"] == "MISS"
            assert warm[1]["X-Thumbnail-Cache"] == "HIT"
            assert cold[2] == warm[2]
            assert struct.unpack("!II", cold[2][16:24]) == (360, 200)
            assert len(cold[2]) < len(original)
            assert "max-age=604800" in warm[1]["Cache-Control"]
            assert fetch("covers/cover.png")[2] == original
            assert struct.unpack("!II", fetch("thumbs/small.png")[2][16:24]) == (120, 80)
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
                parallel = list(pool.map(lambda _: fetch("thumbs/parallel.png"), range(8)))
            assert all(result[0] == 200 for result in parallel)
            assert sum(result[1]["X-Thumbnail-Cache"] == "MISS" for result in parallel) == 1
            assert fetch("thumbs/replacement.png")[1]["X-Thumbnail-Cache"] == "MISS"
            for filename, expected in (("missing.png", 404), ("broken.png", 415), ("oversized.png", 415)):
                for _ in range(2):
                    response = fetch("thumbs/" + filename)
                    assert response[0] == expected, (filename, response[0])
                    assert response[1]["X-Thumbnail-Cache"] != "HIT"
                    assert "max-age=604800" not in response[1].get("Cache-Control", "")
            for _ in range(2):
                result = subprocess.run([sys.executable, str(ROOT / "scripts/warm_thumbnails.py"), base_url],
                                        capture_output=True, text=True)
                assert result.returncode == 0, result.stderr
                assert "Successful thumbnails: 1. Errors: 0." in result.stdout
            catalog["tracks"].append({"cover": "covers/missing.png"})
            (data / "catalog.json").write_text(json.dumps(catalog))
            result = subprocess.run([sys.executable, str(ROOT / "scripts/warm_thumbnails.py"), base_url],
                                    capture_output=True, text=True)
            assert result.returncode == 1
            assert "Errors: 1." in result.stdout
            compose("up", "-d", "--force-recreate")
            ready()
            restored = fetch("thumbs/cover.png?version=one")
            assert restored[1]["X-Thumbnail-Cache"] == "HIT"
            assert restored[2] == cold[2]
            print(f"Original: {len(original)} bytes. Thumbnail: {len(cold[2])} bytes.")
            print(f"Cold request: {cold[3]:.3f}s. Cached request: {warm[3]:.3f}s.")
            print("Thumbnail integration tests passed.")
        finally:
            subprocess.run(command + ["exec", "-T", "web", "find",
                                      "/var/cache/nginx/thumbnails", "-mindepth", "1", "-delete"],
                           env=env, check=False)
            compose("down")


if __name__ == "__main__":
    main()
