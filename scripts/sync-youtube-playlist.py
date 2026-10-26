#!/usr/bin/env python3
"""Sync a public YouTube playlist into the static HOME MV carousel data.

Uses the official YouTube Data API; the API key is a server-side environment secret.
Fails closed: on API, pagination or validation errors, existing JSON is unchanged.
"""
import argparse
import json
import os
import re
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

PLAYLIST = "PL-_eiIqHx28VibKnWYhwaQRc6WBaLeSvN"
API = "https://www.googleapis.com/youtube/v3/playlistItems"
ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "data" / "mv-playlist.json"
VIDEO_ID = re.compile(r"[A-Za-z0-9_-]{11}\Z")
UNAVAILABLE = {"private video", "deleted video"}


def fetch_page(key, token=""):
    query = {
        "part": "snippet,contentDetails",
        "playlistId": PLAYLIST,
        "maxResults": 50,
        "key": key,
    }
    if token:
        query["pageToken"] = token
    url = API + "?" + urllib.parse.urlencode(query)
    request = urllib.request.Request(url, headers={
        "Accept": "application/json", "User-Agent": "rilke-mv-sync/1.0",
    })
    with urllib.request.urlopen(request, timeout=25) as response:
        payload = json.load(response)
    if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
        raise ValueError("Unexpected playlistItems response")
    return payload


def collect(key, reader=fetch_page):
    """Fetch all API pages, dropping unavailable entries and duplicates."""
    videos = []
    seen_ids = set()
    seen_tokens = set()
    token = ""
    for _ in range(100):
        page = reader(key, token)
        for record in page["items"]:
            if not isinstance(record, dict):
                continue
            snippet = record.get("snippet") or {}
            details = record.get("contentDetails") or {}
            resource = snippet.get("resourceId") or {}
            video_id = resource.get("videoId") or details.get("videoId")
            title = snippet.get("title")
            if not (isinstance(video_id, str) and VIDEO_ID.fullmatch(video_id)):
                continue
            if not (isinstance(title, str) and title.strip()):
                continue
            title = title.strip()
            if title.lower() in UNAVAILABLE or video_id in seen_ids:
                continue
            seen_ids.add(video_id)
            videos.append({
                "id": video_id,
                "title": title[:180],
                "thumbnail": f"https://i.ytimg.com/vi/{video_id}/mqdefault.jpg",
                "url": f"https://www.youtube.com/watch?v={video_id}",
            })
        nxt = page.get("nextPageToken") or ""
        if not nxt:
            break
        if not isinstance(nxt, str) or nxt in seen_tokens or nxt == token:
            raise ValueError("Playlist pagination loop")
        seen_tokens.add(nxt)
        token = nxt
    else:
        raise ValueError("Playlist pagination limit exceeded")
    if not videos:
        raise ValueError("No accessible public MV entries; previous catalog retained")
    return videos


def save(videos, dest=OUTPUT, dry_run=False):
    """Only change the file if actual video metadata changed."""
    previous = json.loads(dest.read_text(encoding="utf-8")) if dest.exists() else {}
    if previous.get("playlistId") == PLAYLIST and previous.get("videos") == videos:
        print(f"UNCHANGED: {len(videos)} videos")
        return False
    if dry_run:
        print(f"DRY RUN: {len(videos)} videos would replace {dest}")
        return True
    snapshot = {
        "schema": 1,
        "playlistId": PLAYLIST,
        "updatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "videos": videos,
    }
    dest.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=".mv-playlist-", dir=str(dest.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as out:
            json.dump(snapshot, out, ensure_ascii=False, indent=2)
            out.write("\n")
        os.replace(temp, dest)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)
    print(f"UPDATED: {len(videos)} videos")
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    key = os.environ.get("YOUTUBE_API_KEY", "").strip()
    if not key:
        parser.error("YOUTUBE_API_KEY is not configured; existing file unchanged")
    try:
        save(collect(key), args.output, args.dry_run)
    except urllib.error.HTTPError as exc:
        # HTTPError can contain the full request URL, including the API key.
        print(f"Playlist sync failed; kept last working metadata: API HTTP {exc.code}", file=sys.stderr)
        return 1
    except (OSError, urllib.error.URLError, ValueError, RuntimeError) as exc:
        print(f"Playlist sync failed; kept last working metadata: {type(exc).__name__}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
