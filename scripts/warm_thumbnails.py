#!/usr/bin/env python3
"""Fill the thumbnail cache through the public application URL."""

import argparse
import json
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import urlopen


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base_url", help="Application URL, including its base path")
    args = parser.parse_args()
    parsed = urlsplit(args.base_url)
    if (parsed.scheme not in ("http", "https") or not parsed.netloc
            or parsed.query or parsed.fragment or parsed.username or parsed.password):
        parser.error("Use an HTTP or HTTPS application URL without credentials, a query, or a fragment.")
    base_url = args.base_url.rstrip("/") + "/"
    try:
        with urlopen(base_url + "catalog.json", timeout=30) as response:
            catalog = json.load(response)
        tracks = catalog["tracks"]
        if not isinstance(tracks, list):
            raise ValueError("Invalid tracks list")
    except (HTTPError, URLError, TimeoutError, ValueError, KeyError, TypeError):
        print("The catalog could not be loaded.", file=sys.stderr)
        return 1

    covers = dict.fromkeys(
        track["cover"] for track in tracks
        if isinstance(track, dict) and isinstance(track.get("cover"), str)
        and track["cover"].startswith("covers/")
    )
    successes = 0
    errors = 0
    for index, cover in enumerate(covers, 1):
        try:
            with urlopen(base_url + "thumbs/" + cover[7:], timeout=30) as response:
                while response.read(65536):
                    pass
                cache_status = response.headers.get("X-Thumbnail-Cache", "unknown")
            successes += 1
            print(f"Thumbnail {index}/{len(covers)}: {cache_status}")
        except (HTTPError, URLError, TimeoutError, ValueError):
            errors += 1
            print(f"Thumbnail {index}/{len(covers)} failed.", file=sys.stderr)
    print(f"Successful thumbnails: {successes}. Errors: {errors}.")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
