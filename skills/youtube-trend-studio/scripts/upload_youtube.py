#!/usr/bin/env python3
"""Upload a video to the user's own YouTube channel (Data API v3, OAuth).

Requires  pip install google-api-python-client google-auth-oauthlib google-auth-httplib2
          An OAuth "Desktop app" client file (client_secret.json). See references/setup.md.

Safety defaults
  * Privacy is "private" unless told otherwise, so nothing goes live by accident.
  * "public" also needs --confirm-public. Pass it only after the channel owner
    has watched the video and said, in so many words, to publish it.
  * --dry-run validates everything and prints the request without contacting YouTube.

Example
  python upload_youtube.py --file build/video.mp4 --title "..." \
      --description-file build/description.txt --tags "khoa học,giải thích" \
      --language vi --thumbnail build/thumbnail.png --captions build/captions.srt
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

SCOPE_UPLOAD = "https://www.googleapis.com/auth/youtube.upload"
SCOPE_CAPTIONS = "https://www.googleapis.com/auth/youtube.force-ssl"  # captions.insert needs it
DEFAULT_TOKEN = Path.home() / ".config" / "youtube-trend-studio" / "token.json"


def fail(message: str) -> None:
    sys.exit(f"[upload] {message}")


def validate(args) -> dict:
    video = Path(args.file)
    if not video.exists():
        fail(f"Video not found: {video}")
    title = args.title.strip()
    if not title or len(title) > 100 or re.search(r"[<>]", title):
        fail("Title must be 1-100 characters and must not contain < or >.")
    description = args.description or ""
    if args.description_file:
        description = Path(args.description_file).read_text(encoding="utf-8")
    if len(description.encode("utf-8")) > 5000 or re.search(r"[<>]", description):
        fail("Description must be at most 5000 bytes and must not contain < or >.")
    tags = [t.strip() for t in (args.tags or "").split(",") if t.strip()]
    if sum(len(t) + (2 if " " in t else 0) for t in tags) + max(len(tags) - 1, 0) > 500:
        fail("Tags are too long: YouTube allows about 500 characters in total.")
    if args.privacy == "public" and not args.confirm_public:
        fail("Refusing to publish publicly without --confirm-public. Upload as private, let the "
             "channel owner review it, and only then publish.")
    if args.publish_at and args.privacy != "private":
        fail("--publish-at (scheduled release) only works with --privacy private.")
    if args.publish_at and not re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(\.\d+)?(Z|[+-]\d\d:\d\d)", args.publish_at):
        fail("--publish-at must be ISO 8601 with a time zone, e.g. 2026-12-01T19:00:00+07:00")
    for label, path, limit in (("Thumbnail", args.thumbnail, 2 * 1024 * 1024), ("Captions", args.captions, None)):
        if path:
            if not Path(path).exists():
                fail(f"{label} file not found: {path}")
            if limit and Path(path).stat().st_size > limit:
                fail(f"{label} is larger than 2 MB. Re-export it smaller (JPEG works well).")

    status = {
        "privacyStatus": args.privacy,
        "selfDeclaredMadeForKids": args.made_for_kids,
        "containsSyntheticMedia": args.synthetic_media,
        "embeddable": True,
    }
    if args.publish_at:
        status["publishAt"] = args.publish_at
    snippet = {"title": title, "description": description, "tags": tags, "categoryId": str(args.category)}
    if args.language:
        snippet["defaultLanguage"] = args.language
        snippet["defaultAudioLanguage"] = args.language
    return {"snippet": snippet, "status": status}


def credentials(client_secrets: Path, token_path: Path, scopes: list[str]):
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    creds = None
    if token_path.exists():
        saved = json.loads(token_path.read_text())
        if set(scopes) <= set(saved.get("scopes") or []):
            creds = Credentials.from_authorized_user_info(saved, saved.get("scopes"))
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception:
            creds = None  # refresh tokens of apps in "Testing" mode expire after 7 days
    if not creds or not creds.valid:
        if not client_secrets.exists():
            fail(f"OAuth client file not found: {client_secrets}. See references/setup.md.")
        flow = InstalledAppFlow.from_client_secrets_file(str(client_secrets), scopes)
        print("[upload] A browser window will open. Sign in with the Google account that owns "
              "the channel and approve access.", file=sys.stderr)
        creds = flow.run_local_server(port=0, prompt="consent")
    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(creds.to_json())
    try:
        os.chmod(token_path, 0o600)
    except OSError:
        pass
    return creds


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--file", required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--description", default="")
    p.add_argument("--description-file")
    p.add_argument("--tags", default="", help="comma-separated")
    p.add_argument("--category", default="27", help="YouTube category id (27 Education, 28 Science & Tech, "
                   "24 Entertainment, 22 People & Blogs, 25 News, 26 Howto & Style)")
    p.add_argument("--language", default=None, help="language of title and audio, e.g. vi, en")
    p.add_argument("--privacy", choices=["private", "unlisted", "public"], default="private")
    p.add_argument("--confirm-public", action="store_true", help="required together with --privacy public")
    p.add_argument("--publish-at", help="schedule a private video, ISO 8601 with time zone")
    p.add_argument("--thumbnail", help="1280x720 JPG/PNG under 2 MB")
    p.add_argument("--captions", help="SRT file to attach")
    p.add_argument("--made-for-kids", action="store_true", help="declare the video as made for kids")
    p.add_argument("--synthetic-media", action="store_true",
                   help="declare realistic altered or synthetic content (YouTube's disclosure label)")
    p.add_argument("--client-secrets", default="client_secret.json")
    p.add_argument("--token", default=str(DEFAULT_TOKEN))
    p.add_argument("--dry-run", action="store_true", help="validate and print the request, upload nothing")
    args = p.parse_args()

    body = validate(args)
    if args.dry_run:
        print(json.dumps({"dry_run": True, "file": args.file, "thumbnail": args.thumbnail,
                          "captions": args.captions, "request": body}, ensure_ascii=False, indent=2))
        return

    try:
        from googleapiclient.discovery import build
        from googleapiclient.errors import HttpError
        from googleapiclient.http import MediaFileUpload
    except ImportError:
        fail("Missing libraries: pip install google-api-python-client google-auth-oauthlib google-auth-httplib2")

    scopes = [SCOPE_UPLOAD] + ([SCOPE_CAPTIONS] if args.captions else [])
    youtube = build("youtube", "v3", credentials=credentials(Path(args.client_secrets), Path(args.token), scopes))

    media = MediaFileUpload(args.file, chunksize=8 * 1024 * 1024, resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    response, retries = None, 0
    while response is None:
        try:
            progress, response = request.next_chunk()
            if progress:
                print(f"[upload] {int(progress.progress() * 100)}%", file=sys.stderr)
        except HttpError as err:
            if err.resp.status in (500, 502, 503, 504) and retries < 6:
                retries += 1
                time.sleep(2 ** retries)
                continue
            fail(f"YouTube rejected the upload ({err.resp.status}): {err}")
        except (ConnectionError, TimeoutError, OSError) as err:
            if retries < 6:
                retries += 1
                time.sleep(2 ** retries)
                continue
            fail(f"Network error during upload: {err}")
    video_id = response["id"]
    warnings = []

    if args.thumbnail:
        try:
            youtube.thumbnails().set(videoId=video_id, media_body=MediaFileUpload(args.thumbnail)).execute()
        except HttpError as err:
            warnings.append(f"Thumbnail not set ({err.resp.status}). Custom thumbnails need a phone-verified "
                            "channel; set it by hand in YouTube Studio.")
    if args.captions:
        try:
            youtube.captions().insert(
                part="snippet",
                body={"snippet": {"videoId": video_id, "language": args.language or "en", "name": "", "isDraft": False}},
                media_body=MediaFileUpload(args.captions, mimetype="application/octet-stream"),
            ).execute()
        except HttpError as err:
            warnings.append(f"Captions not attached ({err.resp.status}); upload the SRT in YouTube Studio.")

    actual = response.get("status", {}).get("privacyStatus")
    if actual != args.privacy:
        warnings.append(f"Requested privacy '{args.privacy}' but YouTube set '{actual}'. Unaudited API projects "
                        "have uploads locked to private; see references/setup.md.")
    print(json.dumps({
        "video_id": video_id,
        "url": f"https://youtu.be/{video_id}",
        "studio": f"https://studio.youtube.com/video/{video_id}/edit",
        "privacy": actual,
        "scheduled_for": args.publish_at,
        "warnings": warnings,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
