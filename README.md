# Rilke Mado public MV feed

This repository publishes only public YouTube playlist metadata for the official site's HOME MV card: video ID, title, YouTube URL, and thumbnail URL. The GitHub Pages artifact contains only `mv-playlist.json`.

The workflow fetches the public playlist with the YouTube Data API v3. Its API key is an Actions Secret, never a site asset. A failed API request or invalid response stops before deployment, leaving the last successful Pages feed in place. An unchanged video list skips artifact upload and deployment. The 6-hour schedule is gated by `MV_FEED_SYNC_ENABLED=true`; keep it unset until the manual run and HTTPS checks pass.

No credential in this repository can write to `rilkemado/rilke-official-site`. Production publication and the site's external feed URL are separate changes.
