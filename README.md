# Little Jukebox

Little Jukebox is a small web player designed for an older appliance browser.
It has no JavaScript framework or third-party assets.

[`data/catalog.json`](data/catalog.json) is the source of truth for the
playlist. The server never scans `data/music` or `data/covers`; files that are
not listed in the catalog are not shown by the player.

The catalog and media directories are mounted read-only into the container at
runtime. They are deliberately not copied into the image, so changing the
catalog, audio, or covers does not require rebuilding or restarting the
container. The page checks the catalog every 30 seconds. Reloading the page
also picks up changes immediately.

Each catalog entry must provide an `id`, a user-facing `title`, and paths to
its cover and audio file relative to the application:

```json
{
  "tracks": [
    {
      "id": "song-id",
      "title": "Song title",
      "cover": "covers/song-id.jpg",
      "audio": "audio/song-id.mp3"
    }
  ]
}
```

Place the referenced files in `data/covers/` and `data/music/`, respectively.
The paths need not share the same filename.

## Deployments

The shared Tailscale gateway must already be running, because it creates the
external `tailscale-ingress` network.

Staging and production run from separate directories. Each directory contains
the same `docker-compose.yml`, its own `.env`, and its own `data/` directory.
Use distinct Compose project names, ingress aliases, and application base paths
so both installations can join the shared ingress network at the same time.

Copy `.env.example` to `.env` in the staging directory. The example already
selects the single shared local image tag. Build and reuse that exact tag for
all local and staging tests:

```bash
cp .env.example .env
docker build -t little-jukebox:local .
docker compose config -q
docker compose up -d
```

Do not create task-specific, agent-specific, branch-specific, commit-specific,
or timestamped local image tags. Rebuilding `little-jukebox:local` replaces
the previous development image instead of accumulating disposable images.

Production uses a published immutable version. Its `.env` follows the same
format but uses production-specific values, for example:

```dotenv
COMPOSE_PROJECT_NAME=little-jukebox-production
JUKEBOX_IMAGE=ghcr.io/<owner>/little-jukebox:1.0.0
JUKEBOX_PULL_POLICY=always
JUKEBOX_DOCKER_ALIAS=little-jukebox-production
JUKEBOX_BASE_PATH=/apps/little-jukebox
```

Start or update production from its deployment directory:

```bash
docker compose config -q
docker compose pull
docker compose up -d
```

`JUKEBOX_BASE_PATH` must start with `/` and must not end with `/`. Configure the
Tailscale gateway route to use the matching `JUKEBOX_DOCKER_ALIAS` and path.
For example, the production settings above expose the app at:

```text
https://<funnel-hostname>.<tailnet>.ts.net/apps/little-jukebox/
```

The browser saves playback state under the configured URL path, so staging and
production do not overwrite each other's state when they share a hostname.

On the refrigerator, open that address in its browser and tap a cover. Covers
appear in a swipeable carousel near the bottom of the screen. The selected
cover is centered automatically. Tap a different cover to start that song, or
tap the selected carousel cover, the large cover, or the center control to
pause and resume it without losing the current position.

Songs continue automatically in catalog order. The left control enables or
disables wrapping from the last song back to the first, and the right control
starts the next song immediately. The selected song, playback position, and
repeat setting are saved locally. After a page or browser restart, the player
restores that position in a paused state so it never attempts to bypass the
browser's autoplay policy.

## Updating the library

1. Add or replace media files under `data/music/` and `data/covers/`.
2. Update `data/catalog.json` so it contains exactly the tracks that should be
   visible.
3. Wait up to 30 seconds, or reload the player page.

No image build, `docker compose up`, or container restart is needed. For reliable
updates, write a complete JSON file and then replace `data/catalog.json`; the
whole `data` directory is mounted, so an atomic file replacement is visible to
Nginx.

## Stop

```bash
docker compose down
```
