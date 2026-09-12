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

## Start

The shared Tailscale gateway must already be running, because it creates the
external `tailscale-ingress` network. Build and start the app once with:

```bash
docker compose up -d --build
```

Open the app at:

```text
https://wabelfish-funnel.taild8e94b.ts.net/apps/little-jukebox/
```

On the refrigerator, open that address in its browser and tap a cover. Covers
appear two per row. Tapping the currently selected cover again stops and
rewinds its audio; tapping another cover starts that track instead.

## Updating the library

1. Add or replace media files under `data/music/` and `data/covers/`.
2. Update `data/catalog.json` so it contains exactly the tracks that should be
   visible.
3. Wait up to 30 seconds, or reload the player page.

No `docker compose build`, `up`, or container restart is needed. For reliable
updates, write a complete JSON file and then replace `data/catalog.json`; the
whole `data` directory is mounted, so an atomic file replacement is visible to
Nginx.

## Stop

```bash
docker compose down
```
