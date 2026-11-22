"""upload.py and youtube.py against a fake YouTube. Run from scripts/pipeline:
uv run python -m unittest discover -s tests -v
"""
import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import upload  # noqa: E402
import youtube  # noqa: E402
from common import load_config, read_json, write_json  # noqa: E402

NOW = datetime(2026, 11, 21, 12, 0, tzinfo=timezone.utc)
WHEN = "2026-11-25T18:00:00+01:00"


class FakeYouTube(youtube.Uploader):
    """Answers like the resumable upload protocol; `drop_after` chunks, the connection is lost for good."""

    def __init__(self, drop_after=None, thumbnail_status=200):
        super().__init__("token", sleep=lambda s: None)
        self.calls, self.sessions, self.videos = [], {}, []
        self.drop_after, self.thumbnail_status = drop_after, thumbnail_status

    def request(self, method, url, headers, data=None):
        self.calls.append((method, url, headers, data))
        if url == youtube.UPLOAD_URL:
            sid = f"https://upload.test/session/{len(self.sessions) + 1}"
            self.sessions[sid] = {"body": json.loads(data), "size": int(headers["X-Upload-Content-Length"]), "got": 0}
            return 200, {"Location": sid}, b""
        if url.startswith(youtube.THUMBNAIL_URL):
            return self.thumbnail_status, {}, b'{"error": {"message": "no custom thumbnails", "errors": [{"reason": "forbidden"}]}}'
        s = self.sessions[url]
        if data:
            if self.drop_after is not None:
                if self.drop_after == 0:
                    return 0, {}, b""
                self.drop_after -= 1
            s["got"] += len(data)
        if s["got"] >= s["size"]:
            if "id" not in s:
                s["id"] = f"vid{len(self.videos) + 1}"
                self.videos.append(s)
            return 200, {}, json.dumps({"id": s["id"], "status": {
                "privacyStatus": s["body"]["status"]["privacyStatus"],
                "publishAt": s["body"]["status"].get("publishAt")}}).encode()
        return 308, ({"Range": f"bytes=0-{s['got'] - 1}"} if s["got"] else {}), b""


def make_level(root: Path) -> Path:
    d = root / "2026-11-21_logement" / "A2"
    (d / "out").mkdir(parents=True)
    base = "2026-11-21_logement_A2"
    common = {"language": "fr", "made_for_kids": False, "category": "Education", "category_id": 27}
    write_json(d / "out" / "publish.json", {
        "youtube": {"file": f"{base}_16x9.mp4", "title": "Dialogue en français A2 : déménager",
                    "description": "Intro\n\n#français #A2", "tags": ["dialogue en français", "français A2"],
                    "hashtags": ["#français", "#A2"], "thumbnail_file": f"{base}_thumbnail.jpg", **common},
        "youtube_shorts": {"file": f"{base}_short_9x16.mp4", "title": "Tu comprends ce dialogue A2 ?",
                           "description": "Un extrait.\n\n#français #Shorts", "hashtags": ["#français", "#Shorts"],
                           **common}})
    write_json(d / "state.json", {"steps": {"check": {"16x9": {"problems": []}, "9x16": {"problems": []},
                                                      "short_9x16": {"problems": []}}}})
    (d / "out" / f"{base}_16x9.mp4").write_bytes(b"L" * 3000)
    (d / "out" / f"{base}_short_9x16.mp4").write_bytes(b"S" * 1000)
    (d / "out" / f"{base}_thumbnail.jpg").write_bytes(b"JPEG")
    return d


class UploadTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.d = make_level(Path(self.tmp.name))
        self.cfg = load_config()
        self.chunk, youtube.CHUNK = youtube.CHUNK, 1000
        self.addCleanup(setattr, youtube, "CHUNK", self.chunk)

    def jobs(self, done, kinds=upload.KINDS, when=WHEN, short_when=None):
        return upload.build_jobs(self.d, self.cfg, done, kinds, when, short_when, NOW)

    def run_push(self, yt, done=None, **kw):
        done = {} if done is None else done
        jobs, problems = self.jobs(done, **kw)
        self.assertEqual(problems, [])
        return done, upload.push(self.d, jobs, done, self.cfg, yt, say=lambda s: None)

    def test_sends_both_videos_private_and_scheduled(self):
        yt = FakeYouTube()
        done, warnings = self.run_push(yt)
        self.assertEqual(warnings, [])
        long_body, short_body = (v["body"] for v in yt.videos)
        self.assertEqual(long_body["snippet"]["title"], "Dialogue en français A2 : déménager")
        self.assertEqual(long_body["snippet"]["categoryId"], "27")
        self.assertEqual(long_body["snippet"]["tags"], ["dialogue en français", "français A2"])
        for body in (long_body, short_body):
            self.assertEqual(body["status"]["privacyStatus"], "private")
            self.assertEqual(body["status"]["publishAt"], "2026-11-25T17:00:00Z")
            self.assertIs(body["status"]["selfDeclaredMadeForKids"], False)
        self.assertEqual(short_body["snippet"]["description"],
                         "Un extrait.\n\n▶️ Le dialogue complet : https://www.youtube.com/watch?v=vid1\n\n#français #Shorts")
        self.assertEqual(done["long"]["url"], "https://www.youtube.com/watch?v=vid1")
        self.assertEqual(done["short"]["url"], "https://www.youtube.com/shorts/vid2")
        self.assertEqual(done["long"]["thumbnail"], "set")
        thumb = [c for c in yt.calls if c[1].startswith(youtube.THUMBNAIL_URL)]
        self.assertEqual([(c[1], c[3]) for c in thumb], [(youtube.THUMBNAIL_URL + "vid1", b"JPEG")])
        self.assertEqual(read_json(self.d / "out" / "uploaded.json"), done)

    def test_second_run_sends_nothing(self):
        done, _ = self.run_push(FakeYouTube())
        again = FakeYouTube()
        # the schedule has passed by the second run: finished videos must not need a valid time
        jobs, problems = upload.build_jobs(self.d, self.cfg, done, upload.KINDS, "2026-11-01T10:00:00+01:00", None, NOW)
        self.assertEqual(problems, [])
        upload.push(self.d, jobs, done, self.cfg, again, say=lambda s: None)
        self.assertEqual(again.calls, [])

    def test_interrupted_upload_is_continued_not_restarted(self):
        yt = FakeYouTube(drop_after=1)
        done = {}
        jobs, _ = self.jobs(done)
        with self.assertRaises(youtube.UploadError):
            upload.push(self.d, jobs, done, self.cfg, yt, say=lambda s: None)
        saved = read_json(self.d / "out" / "uploaded.json")
        self.assertTrue(saved["long"]["session"])       # written before the bytes went out
        self.assertNotIn("id", saved["long"])
        yt.drop_after = None
        self.run_push(yt, done=saved)
        self.assertEqual(len([c for c in yt.calls if c[1] == youtube.UPLOAD_URL]), 2)  # long once, short once
        self.assertEqual([v["got"] for v in yt.videos], [3000, 1000])

    def test_thumbnail_refusal_is_a_warning(self):
        yt = FakeYouTube(thumbnail_status=403)
        done, warnings = self.run_push(yt)
        self.assertEqual(len(yt.videos), 2)
        self.assertTrue(done["long"]["thumbnail"].startswith("failed"))
        self.assertEqual(len(warnings), 1)
        yt.thumbnail_status = 200                         # a later push only retries the thumbnail
        before = len(yt.calls)
        self.run_push(yt, done=done)
        self.assertEqual(len(yt.calls), before + 1)
        self.assertEqual(done["long"]["thumbnail"], "set")

    def test_bad_times_are_refused(self):
        for when, word in (("2026-11-21T12:05:00+00:00", "minutes from now"), ("2026-11-20T10:00:00+01:00", "minutes from now"),
                           ("2026-11-25T18:00:00", "time zone"), ("mardi", "ISO 8601"), (None, "no publish time")):
            _, problems = self.jobs({}, when=when)
            self.assertTrue(problems and all(word in p for p in problems), (when, problems))

    def test_failed_check_or_missing_file_is_refused(self):
        state = read_json(self.d / "state.json")
        state["steps"]["check"]["16x9"]["problems"] = ["black frames"]
        write_json(self.d / "state.json", state)
        (self.d / "out" / "2026-11-21_logement_A2_short_9x16.mp4").unlink()
        _, problems = self.jobs({})
        self.assertEqual(len(problems), 2)
        self.assertIn("failed its checks", problems[0])
        self.assertIn("missing", problems[1])

    def test_short_alone_needs_the_long_video(self):
        _, problems = self.jobs({}, kinds=("short",))
        self.assertTrue(any("long video is not uploaded" in p for p in problems))

    def test_short_time_and_delay(self):
        jobs, _ = self.jobs({}, short_when="2026-11-26T09:30:00+01:00")
        self.assertEqual(jobs["short"]["publish_at"], "2026-11-26T08:30:00Z")
        self.cfg["upload"]["short_delay_minutes"] = 90
        jobs, _ = self.jobs({})
        self.assertEqual(jobs["short"]["publish_at"], "2026-11-25T18:30:00Z")


if __name__ == "__main__":
    unittest.main()
