#!/usr/bin/env python3
"""Publish only when the live Pages feed differs from the new API result."""
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

LIVE_URL = "https://rilkemado.github.io/rilke-mv-public-feed/mv-playlist.json"


def main():
    proposed = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    request = urllib.request.Request(
        LIVE_URL,
        headers={"Accept": "application/json", "Cache-Control": "no-cache"},
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            published = json.load(response)
    except urllib.error.HTTPError as error:
        if error.code != 404:
            print(f"Published feed check failed: HTTP {error.code}", file=sys.stderr)
            return 1
        published = None  # First deployment only.
    except (OSError, ValueError) as error:
        print(f"Published feed check failed: {type(error).__name__}", file=sys.stderr)
        return 1

    unchanged = (
        isinstance(published, dict)
        and published.get("playlistId") == proposed.get("playlistId")
        and published.get("videos") == proposed.get("videos")
    )
    changed = not unchanged
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
        output.write(f"changed={'true' if changed else 'false'}\n")
    print(f"{'CHANGED' if changed else 'UNCHANGED'}: {len(proposed['videos'])} public videos")
    return 0


if __name__ == "__main__":
    sys.exit(main())
