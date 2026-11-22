"""YouTube Data API v3: sign-in, resumable video upload, thumbnail. Standard library only.

Adapted from sceneloom/publish/youtube.py. upload.py is the only caller; nothing in run.py uploads.

One-time setup (references/upload-setup.md): save the OAuth "Desktop app" client JSON as
<config>/youtube_client.json and run `upload.py auth`. The refresh token is kept in
<config>/youtube_token.json (mode 600). <config> is ~/.config/vocab-to-video, or $VOCAB_TO_VIDEO_CONFIG.

Protocol: https://developers.google.com/youtube/v3/guides/using_resumable_upload_protocol
"""
from __future__ import annotations

import base64
import hashlib
import http.server
import json
import os
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path
from typing import Callable

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status"
THUMBNAIL_URL = "https://www.googleapis.com/upload/youtube/v3/thumbnails/set?uploadType=media&videoId="
SCOPE = "https://www.googleapis.com/auth/youtube.upload"
RETRY = {500, 502, 503, 504}
CHUNK = 8 * 1024 * 1024


class UploadError(RuntimeError):
    pass


def config_dir() -> Path:
    """Where the channel connection lives: outside the skill, the episodes and every repo."""
    d = Path(os.environ.get("VOCAB_TO_VIDEO_CONFIG") or Path.home() / ".config" / "vocab-to-video")
    d.mkdir(parents=True, exist_ok=True)
    try:
        d.chmod(0o700)
    except OSError:
        pass
    return d


def client_file() -> Path:
    return config_dir() / "youtube_client.json"


def token_file() -> Path:
    return config_dir() / "youtube_token.json"


def connected() -> bool:
    return client_file().is_file() and token_file().is_file()


def _client() -> dict:
    try:
        raw = json.loads(client_file().read_text(encoding="utf-8"))
    except OSError:
        raise UploadError(f"no YouTube OAuth client yet: save the Desktop-app client JSON as {client_file()} "
                          "(see references/upload-setup.md)")
    except ValueError:
        raise UploadError(f"{client_file()} is not valid JSON")
    c = raw.get("installed") or raw.get("web") or raw
    if not c.get("client_id"):
        raise UploadError(f"{client_file()} has no client_id")
    return c


def _post_form(url: str, fields: dict) -> dict:
    req = urllib.request.Request(url, data=urllib.parse.urlencode(fields).encode(), method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read(2000).decode("utf-8", "replace")
        try:
            why = json.loads(body).get("error_description") or json.loads(body).get("error")
        except ValueError:
            why = body[:160]
        raise UploadError(f"Google refused the sign-in request (HTTP {e.code}): {why}")
    except (urllib.error.URLError, TimeoutError) as e:
        raise UploadError(f"cannot reach Google: {e}")


def authorize(say: Callable[[str], None] = print, open_browser: bool = True, timeout: float = 300) -> None:
    """Sign in once in the browser; keeps a refresh token for later uploads."""
    c = _client()
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    state = secrets.token_urlsafe(16)
    got: dict[str, str] = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            q = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(self.path).query))
            if q.get("state") == state:
                got.update(q)
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write("<p>vocab-to-video: you can close this tab.</p>".encode())

        def log_message(self, *a):
            pass

    server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    redirect = f"http://127.0.0.1:{server.server_port}"
    url = AUTH_URL + "?" + urllib.parse.urlencode({
        "client_id": c["client_id"], "redirect_uri": redirect, "response_type": "code", "scope": SCOPE,
        "code_challenge": challenge, "code_challenge_method": "S256", "state": state,
        "access_type": "offline", "prompt": "consent"})
    say("Open this address, choose the channel's Google account and allow uploading:\n" + url)
    if open_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass
    server.timeout = 1
    deadline = time.monotonic() + timeout
    try:
        while not got and time.monotonic() < deadline:
            server.handle_request()
    finally:
        server.server_close()
    if not got.get("code"):
        raise UploadError("sign-in was not finished: " + (got.get("error") or f"no answer within {timeout:.0f}s"))
    tok = _post_form(TOKEN_URL, {"client_id": c["client_id"], "client_secret": c.get("client_secret", ""),
                                 "code": got["code"], "code_verifier": verifier,
                                 "grant_type": "authorization_code", "redirect_uri": redirect})
    if not tok.get("refresh_token"):
        raise UploadError("Google returned no refresh token; remove this app's access in the Google account and try again")
    f = token_file()
    f.write_text(json.dumps({"refresh_token": tok["refresh_token"], "scope": tok.get("scope", SCOPE),
                             "saved": time.strftime("%Y-%m-%d %H:%M:%S")}), encoding="utf-8")
    f.chmod(0o600)
    say(f"Connected. Token saved in {f}")


def access_token() -> str:
    c = _client()
    try:
        refresh = json.loads(token_file().read_text(encoding="utf-8"))["refresh_token"]
    except (OSError, ValueError, KeyError):
        raise UploadError("YouTube is not connected: run `uv run python upload.py auth`")
    tok = _post_form(TOKEN_URL, {"client_id": c["client_id"], "client_secret": c.get("client_secret", ""),
                                 "grant_type": "refresh_token", "refresh_token": refresh})
    return tok["access_token"]


def video_body(meta: dict) -> dict:
    """The videos.insert resource for one upload. Always private; `publish_at` schedules the release."""
    status = {"privacyStatus": "private", "selfDeclaredMadeForKids": bool(meta["made_for_kids"]),
              "containsSyntheticMedia": bool(meta["synthetic_media"])}
    if meta.get("publish_at"):
        status["publishAt"] = meta["publish_at"]
    return {"snippet": {"title": meta["title"], "description": meta["description"], "tags": meta["tags"],
                        "categoryId": str(meta["category_id"]), "defaultLanguage": meta["language"],
                        "defaultAudioLanguage": meta["language"]},
            "status": status}


class Uploader:
    """Resumable uploads. `request` is the only HTTP entry point, so tests can replace it."""

    def __init__(self, token: str, sleep: Callable[[float], None] = time.sleep):
        self.token, self.sleep = token, sleep

    def request(self, method: str, url: str, headers: dict, data: bytes | None = None) -> tuple[int, dict, bytes]:
        req = urllib.request.Request(url, data=data, method=method,
                                     headers={"Authorization": f"Bearer {self.token}", **headers})
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                return r.status, dict(r.headers.items()), r.read()
        except urllib.error.HTTPError as e:
            return e.code, dict(e.headers.items()), e.read(4000)
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            return 0, {}, b""  # no answer: ask how far the upload got, then go on

    @staticmethod
    def _why(body: bytes) -> str:
        try:
            err = json.loads(body.decode("utf-8"))["error"]
            return f'{err.get("message", "")} ({(err.get("errors") or [{}])[0].get("reason", "")})'
        except (ValueError, KeyError, TypeError, AttributeError):
            return body.decode("utf-8", "replace")[:160]

    def start(self, meta: dict, size: int) -> str:
        status, headers, raw = self.request("POST", UPLOAD_URL, {
            "Content-Type": "application/json; charset=UTF-8", "X-Upload-Content-Length": str(size),
            "X-Upload-Content-Type": "video/mp4"}, json.dumps(video_body(meta)).encode("utf-8"))
        session = {k.lower(): v for k, v in headers.items()}.get("location")
        if status != 200 or not session:
            raise UploadError(f"YouTube did not start the upload (HTTP {status}): {self._why(raw)}")
        return session

    def received(self, session: str, size: int) -> tuple[int, dict | None]:
        """(bytes YouTube already has, the finished video if it is complete)."""
        status, headers, raw = self.request("PUT", session, {"Content-Length": "0", "Content-Range": f"bytes */{size}"})
        if status in (200, 201):
            return size, json.loads(raw.decode("utf-8"))
        if status == 308:
            rng = {k.lower(): v for k, v in headers.items()}.get("range", "")
            return (int(rng.rsplit("-", 1)[1]) + 1 if "-" in rng else 0), None
        if status == 404:
            raise UploadError("the upload session expired; run push again to start a new upload")
        raise UploadError(f"YouTube upload status check failed (HTTP {status}): {self._why(raw)}")

    def send(self, session: str, path: Path, on_progress: Callable[[int, int], None] = lambda a, b: None) -> dict:
        """Send the file from wherever YouTube says it stopped; returns the video resource."""
        size = path.stat().st_size
        done, video = self.received(session, size)
        tries = 0
        with open(path, "rb") as f:
            while video is None:
                f.seek(done)
                chunk = f.read(CHUNK)
                status, headers, raw = self.request("PUT", session, {
                    "Content-Length": str(len(chunk)), "Content-Type": "video/mp4",
                    "Content-Range": f"bytes {done}-{done + len(chunk) - 1}/{size}"}, chunk)
                if status in (200, 201):
                    video = json.loads(raw.decode("utf-8"))
                elif status == 308:
                    rng = {k.lower(): v for k, v in headers.items()}.get("range", "")
                    done, tries = (int(rng.rsplit("-", 1)[1]) + 1 if "-" in rng else 0), 0
                    on_progress(done, size)
                elif status == 0 or status in RETRY:
                    tries += 1
                    if tries > 6:
                        raise UploadError("YouTube keeps failing; run push again later, the upload continues where it stopped")
                    self.sleep(min(60, 2 ** tries))
                    done, video = self.received(session, size)
                else:
                    raise UploadError(f"YouTube rejected the upload (HTTP {status}): {self._why(raw)}")
        return video

    def set_thumbnail(self, video_id: str, path: Path) -> None:
        data = path.read_bytes()
        status, _, raw = self.request("POST", THUMBNAIL_URL + urllib.parse.quote(video_id), {
            "Content-Type": "image/jpeg", "Content-Length": str(len(data))}, data)
        if status != 200:
            raise UploadError(f"YouTube did not take the thumbnail (HTTP {status}): {self._why(raw)}")


def upload_video(meta: dict, state: dict, save: Callable[[], None], uploader: Uploader,
                 say: Callable[[str], None] = print) -> dict:
    """Upload one video once. `state` is this video's entry in out/uploaded.json; it is saved before
    any byte is sent, so an interrupted upload is continued and a finished one is never repeated."""
    if state.get("id"):
        return state
    path = Path(meta["file"])
    size = path.stat().st_size
    fingerprint = hashlib.md5(json.dumps([video_body(meta), size], sort_keys=True).encode()).hexdigest()
    if state.get("session") and state.get("asked") != fingerprint:
        state.pop("session")  # texts, schedule or file changed since the unfinished upload: start over
    if not state.get("session"):
        state.update(session=uploader.start(meta, size), asked=fingerprint, status="uploading")
        save()
    try:
        video = uploader.send(state["session"], path,
                              lambda done, total: say(f"  {path.name}: {done * 100 // total}%"))
    except UploadError as e:
        if "expired" in str(e):
            state.pop("session", None)
            save()
        raise
    got = video.get("status") or {}
    state.pop("session", None)
    state.update(id=video["id"], url=meta["url"].format(id=video["id"]), status="uploaded", title=meta["title"],
                 privacy=got.get("privacyStatus", "private"), publish_at=got.get("publishAt"),
                 asked_publish_at=meta.get("publish_at"), at=time.strftime("%Y-%m-%d %H:%M:%S"))
    save()
    return state
