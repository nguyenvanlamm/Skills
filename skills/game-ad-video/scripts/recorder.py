#!/usr/bin/env python3
"""Run a game, let the agent play it, and record real gameplay takes.

One long-lived server holds the game open; short client calls drive it, so the agent can look
(shot), act (tap / swipe / key), and record between thinking steps without restarting the game.

  recorder.py serve --url http://localhost:8080 [--out marketing/video] [--audio] [--headed]
  recorder.py serve --android [--serial SERIAL] [--out marketing/video]
  recorder.py shot [NAME]                 # PNG in <out>/shots/, coordinates = image pixels
  recorder.py tap X Y
  recorder.py swipe X1 Y1 X2 Y2 [--ms 250]
  recorder.py key KEY                     # web only: ArrowLeft, Space, …
  recorder.py wait MS
  recorder.py rec start NAME | rec stop   # manual take around interactive play
  recorder.py mark LABEL                  # timestamp a moment in the current take
  recorder.py play SCRIPT.json [--take NAME] [--reload]
  recorder.py status | stop

Web: Playwright + Chrome, frames from CDP Page.startScreencast (works on Wayland and headless),
encoded to constant 30 fps H.264 with each frame held for its real duration. Coordinates are CSS
pixels, which is what `shot` images use. --audio also records the PulseAudio/PipeWire default
monitor in parallel (it hears every app on the machine, so keep the machine quiet).
Android: adb screencap / input / screenrecord; coordinates are device pixels.

Each take writes <out>/takes/NAME.mp4 and NAME.marks.json ({"duration": s, "marks": [{t, label}]}).
`serve` writes <out>/.gitignore so takes, shots, sheets and every video stay out of git.
"""
import argparse
import asyncio
import base64
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

DEFAULT_OUT = "marketing/video"
FPS = 30
# Footage never goes to GitHub: the output folder carries its own .gitignore for it.
MEDIA_IGNORE = ["*.mp4", "*.mov", "*.m4v", "*.webm", "*.mkv", "takes/", "shots/", "sheets/", ".build-*/"]


def ignore_media(folder):
    gi = Path(folder) / ".gitignore"
    text = gi.read_text() if gi.exists() else ""
    missing = [p for p in MEDIA_IGNORE if p not in text.splitlines()]
    if missing:
        head = "" if text else "# game-ad-video: videos and raw footage stay on this machine, never in git\n"
        sep = "\n" if text and not text.endswith("\n") else ""
        gi.write_text(text + sep + head + "".join(p + "\n" for p in missing))


def sock_path(out):
    # Unix socket paths are capped at ~107 bytes, so the socket lives in a short runtime dir,
    # keyed by the output folder so two games can be recorded at once.
    import hashlib
    key = hashlib.sha1(str(Path(out).resolve()).encode()).hexdigest()[:12]
    return os.path.join(os.environ.get("XDG_RUNTIME_DIR") or "/tmp", f"game-ad-{key}.sock")


def encode_frames(frames, end_time, frames_dir, mp4, audio=None):
    """frames: [(timestamp, filename)] in order, arriving only when the page repaints.

    Resample to constant FPS by hard-linking, for each output tick, the newest frame captured by
    then; ffmpeg's concat `duration` lines are unreliable for short JPEG durations.
    """
    if not frames:
        raise RuntimeError("no frames captured — is the page rendering?")
    cfr = frames_dir / "cfr"
    cfr.mkdir(exist_ok=True)
    j = 0
    for k in range(max(int(end_time * FPS), 1)):
        while j + 1 < len(frames) and frames[j + 1][0] <= k / FPS:
            j += 1
        os.link(frames_dir / frames[j][1], cfr / f"{k:06d}.jpg")
    cmd = ["ffmpeg", "-v", "error", "-y", "-framerate", str(FPS), "-i", str(cfr / "%06d.jpg")]
    if audio and Path(audio).exists() and Path(audio).stat().st_size > 1024:
        cmd += ["-i", str(audio), "-map", "0:v", "-map", "1:a", "-c:a", "aac", "-b:a", "192k", "-shortest"]
    cmd += ["-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2:out_range=tv,format=yuv420p", "-color_range", "tv",
            "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-movflags", "+faststart", str(mp4)]
    subprocess.run(cmd, check=True)


class Take:
    def __init__(self, out, name):
        self.name = name
        self.mp4 = Path(out) / "takes" / f"{name}.mp4"
        self.mp4.parent.mkdir(parents=True, exist_ok=True)
        self.t0 = time.monotonic()
        self.marks = []

    def mark(self, label):
        t = round(time.monotonic() - self.t0, 2)
        self.marks.append({"t": t, "label": label})
        return t

    def write_marks(self, duration):
        meta = {"take": str(self.mp4), "duration": round(duration, 2), "marks": self.marks}
        self.mp4.with_suffix(".marks.json").write_text(json.dumps(meta, indent=2))
        return meta


class WebBackend:
    def __init__(self, args):
        self.args = args
        self.take = None
        self.frames = []
        self.audio_proc = None

    async def start(self):
        from playwright.async_api import async_playwright
        self.pw = await async_playwright().start()
        launch = {"headless": not self.args.headed,
                  "args": ["--autoplay-policy=no-user-gesture-required",
                           # without this, screencast frames come at CSS size, not device size
                           f"--force-device-scale-factor={self.args.dpr}"]}
        try:
            self.browser = await self.pw.chromium.launch(channel="chrome", **launch)
        except Exception:
            self.browser = await self.pw.chromium.launch(**launch)
        self.context = await self.browser.new_context(
            viewport={"width": self.args.width, "height": self.args.height},
            device_scale_factor=self.args.dpr)
        self.page = await self.context.new_page()
        await self.page.goto(self.args.url, wait_until="load")
        await self.page.wait_for_timeout(self.args.boot_ms)
        self.cdp = await self.context.new_cdp_session(self.page)
        self.cdp.on("Page.screencastFrame", self._on_frame)

    def _on_frame(self, ev):
        if self.take is not None:
            name = f"{len(self.frames):06d}.jpg"
            (self.frames_dir / name).write_bytes(base64.b64decode(ev["data"]))
            self.frames.append((time.monotonic() - self.take.t0, name))
        asyncio.ensure_future(self.cdp.send("Page.screencastFrameAck", {"sessionId": ev["sessionId"]}))

    async def shot(self, path):
        await self.page.screenshot(path=str(path), scale="css")

    async def tap(self, x, y):
        await self.page.mouse.click(x, y)

    async def swipe(self, x1, y1, x2, y2, ms):
        steps = max(int(ms / 16), 2)
        await self.page.mouse.move(x1, y1)
        await self.page.mouse.down()
        for i in range(1, steps + 1):
            await self.page.mouse.move(x1 + (x2 - x1) * i / steps, y1 + (y2 - y1) * i / steps)
            await asyncio.sleep(ms / 1000 / steps)
        await self.page.mouse.up()

    async def key(self, key):
        await self.page.keyboard.press(key)

    async def reload(self):
        await self.page.reload(wait_until="load")
        await self.page.wait_for_timeout(self.args.boot_ms)

    async def rec_start(self, name):
        self.take = Take(self.args.out, name)
        self.frames_dir = self.take.mp4.parent / f".{name}.frames"
        shutil.rmtree(self.frames_dir, ignore_errors=True)
        self.frames_dir.mkdir(parents=True)
        self.frames = []
        if self.args.audio:
            wav = self.frames_dir / "audio.wav"
            self.audio_proc = subprocess.Popen(
                ["ffmpeg", "-v", "error", "-y", "-f", "pulse", "-i", self.args.audio_source,
                 "-ac", "2", "-ar", "48000", str(wav)],
                stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        w, h = int(self.args.width * self.args.dpr), int(self.args.height * self.args.dpr)
        await self.cdp.send("Page.startScreencast",
                            {"format": "jpeg", "quality": 90, "maxWidth": w, "maxHeight": h})

    async def rec_stop(self):
        take = self.take
        await self.cdp.send("Page.stopScreencast")
        await asyncio.sleep(0.1)
        end = time.monotonic() - take.t0
        self.take = None
        audio = None
        if self.audio_proc:
            try:
                self.audio_proc.communicate(b"q", timeout=5)
            except subprocess.TimeoutExpired:
                self.audio_proc.kill()
            self.audio_proc = None
            audio = self.frames_dir / "audio.wav"
        await asyncio.to_thread(encode_frames, self.frames, end, self.frames_dir, take.mp4, audio)
        if not self.args.keep_frames:
            shutil.rmtree(self.frames_dir, ignore_errors=True)
        meta = take.write_marks(end)
        meta["frames"] = len(self.frames)
        return meta

    async def close(self):
        await self.browser.close()
        await self.pw.stop()


class AndroidBackend:
    def __init__(self, args):
        self.args = args
        self.take = None
        self.proc = None
        adb = shutil.which("adb") or os.path.expanduser("~/Android/Sdk/platform-tools/adb")
        self.adb = [adb] + (["-s", args.serial] if args.serial else [])

    def _run(self, *a, **kw):
        return subprocess.run(self.adb + list(a), check=True, **kw)

    async def start(self):
        await asyncio.to_thread(self._run, "get-state", capture_output=True)

    async def shot(self, path):
        png = await asyncio.to_thread(self._run, "exec-out", "screencap", "-p", capture_output=True)
        Path(path).write_bytes(png.stdout)

    async def tap(self, x, y):
        await asyncio.to_thread(self._run, "shell", "input", "tap", str(int(x)), str(int(y)))

    async def swipe(self, x1, y1, x2, y2, ms):
        await asyncio.to_thread(self._run, "shell", "input", "swipe",
                                *[str(int(v)) for v in (x1, y1, x2, y2, ms)])

    async def key(self, key):
        await asyncio.to_thread(self._run, "shell", "input", "keyevent", key)

    async def reload(self):
        raise RuntimeError("reload is web-only; restart the app with adb shell am start")

    async def rec_start(self, name):
        self.take = Take(self.args.out, name)
        # screenrecord stops by itself after 180 s; takes are meant to be short.
        self.proc = subprocess.Popen(self.adb + ["shell", "screenrecord", "--bit-rate", "12000000",
                                                 "/sdcard/game-ad-take.mp4"])

    async def rec_stop(self):
        take = self.take
        end = time.monotonic() - take.t0
        self.take = None
        await asyncio.to_thread(self._run, "shell", "pkill", "-INT", "screenrecord", check=False)
        await asyncio.to_thread(self.proc.wait)
        await asyncio.sleep(1)
        raw = take.mp4.with_suffix(".raw.mp4")
        await asyncio.to_thread(self._run, "pull", "/sdcard/game-ad-take.mp4", str(raw),
                                capture_output=True)
        await asyncio.to_thread(subprocess.run, [
            "ffmpeg", "-v", "error", "-y", "-i", str(raw), "-vf",
            f"fps={FPS},scale=trunc(iw/2)*2:trunc(ih/2)*2:out_range=tv,format=yuv420p", "-color_range", "tv",
            "-c:v", "libx264", "-crf", "16", "-an", str(take.mp4)], check=True)
        raw.unlink()
        return take.write_marks(end)

    async def close(self):
        pass


class Server:
    def __init__(self, args):
        self.args = args
        self.backend = AndroidBackend(args) if args.android else WebBackend(args)
        self.lock = asyncio.Lock()
        self.done = asyncio.Event()
        self.shots = Path(args.out) / "shots"
        self.shots.mkdir(parents=True, exist_ok=True)

    async def run_actions(self, actions):
        b = self.backend
        for a in actions:
            if "repeat" in a:
                for _ in range(int(a["repeat"])):
                    await self.run_actions(a["actions"])
            elif "tap" in a:
                await b.tap(*a["tap"])
            elif "swipe" in a:
                await b.swipe(*a["swipe"], a.get("ms", 250))
            elif "key" in a:
                await b.key(a["key"])
            elif "wait" in a:
                await asyncio.sleep(a["wait"] / 1000)
            elif "mark" in a:
                if b.take:
                    b.take.mark(a["mark"])
            elif "shot" in a:
                await b.shot(self.shots / a["shot"])
            else:
                raise ValueError(f"unknown action: {a}")
            if "after" in a:
                await asyncio.sleep(a["after"] / 1000)

    async def handle(self, req):
        b, cmd = self.backend, req["cmd"]
        if cmd == "shot":
            name = req.get("name") or time.strftime("shot-%H%M%S")
            path = self.shots / (name if name.endswith(".png") else f"{name}.png")
            await b.shot(path)
            return {"shot": str(path.resolve())}
        if cmd == "tap":
            await b.tap(req["x"], req["y"])
        elif cmd == "swipe":
            await b.swipe(req["x1"], req["y1"], req["x2"], req["y2"], req["ms"])
        elif cmd == "key":
            await b.key(req["key"])
        elif cmd == "wait":
            await asyncio.sleep(req["ms"] / 1000)
        elif cmd == "mark":
            if not b.take:
                raise RuntimeError("not recording")
            return {"t": b.take.mark(req["label"])}
        elif cmd == "rec":
            if req["action"] == "start":
                if b.take:
                    raise RuntimeError(f"already recording {b.take.name}")
                await b.rec_start(req["name"])
                return {"recording": req["name"]}
            if not b.take:
                raise RuntimeError("not recording")
            return await b.rec_stop()
        elif cmd == "play":
            script = json.loads(Path(req["script"]).read_text())
            if b.take:
                raise RuntimeError(f"already recording {b.take.name}")
            if req.get("reload"):
                await b.reload()
            await b.rec_start(req["take"])
            try:
                await asyncio.sleep(script.get("lead_in_ms", 500) / 1000)
                await self.run_actions(script["actions"])
                await asyncio.sleep(script.get("tail_ms", 1000) / 1000)
            finally:
                meta = await b.rec_stop()
            return meta
        elif cmd == "status":
            return {"recording": b.take.name if b.take else None,
                    "elapsed": round(time.monotonic() - b.take.t0, 2) if b.take else None}
        elif cmd == "stop":
            if b.take:
                await b.rec_stop()
            self.done.set()
        else:
            raise ValueError(f"unknown command {cmd}")
        return {}

    async def client(self, reader, writer):
        try:
            req = json.loads(await reader.readline())
            async with self.lock:
                try:
                    resp = {"ok": True, **(await self.handle(req))}
                except Exception as e:  # report to the client, keep serving
                    resp = {"ok": False, "error": f"{type(e).__name__}: {e}"}
            writer.write((json.dumps(resp) + "\n").encode())
            await writer.drain()
        finally:
            writer.close()

    async def serve(self):
        path = sock_path(self.args.out)
        if os.path.exists(path):
            os.unlink(path)
        await self.backend.start()
        server = await asyncio.start_unix_server(self.client, path=path)
        print(json.dumps({"ready": True, "socket": path}), flush=True)
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, self.done.set)
        await self.done.wait()
        server.close()
        await self.backend.close()
        os.unlink(path)


def send(out, req):
    import socket
    path = sock_path(out)
    if not os.path.exists(path):
        sys.exit(f"no recorder running for {out} (start: recorder.py serve --url …)")
    with socket.socket(socket.AF_UNIX) as s:
        s.connect(path)
        s.sendall((json.dumps(req) + "\n").encode())
        data = b""
        while not data.endswith(b"\n"):
            chunk = s.recv(65536)
            if not chunk:
                break
            data += chunk
    resp = json.loads(data)
    print(json.dumps(resp, indent=2))
    sys.exit(0 if resp.get("ok") else 1)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out", default=os.environ.get("GAME_AD_OUT", DEFAULT_OUT))
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("serve")
    s.add_argument("--url")
    s.add_argument("--android", action="store_true")
    s.add_argument("--serial")
    s.add_argument("--width", type=int, default=430)
    s.add_argument("--height", type=int, default=932)
    s.add_argument("--dpr", type=float, default=2.5)
    s.add_argument("--boot-ms", type=int, default=3000, help="wait after load for the engine to boot")
    s.add_argument("--headed", action="store_true")
    s.add_argument("--audio", action="store_true", help="also record the system audio monitor")
    s.add_argument("--audio-source", default="@DEFAULT_MONITOR@")
    s.add_argument("--keep-frames", action="store_true")
    sh = sub.add_parser("shot")
    sh.add_argument("name", nargs="?")
    t = sub.add_parser("tap")
    t.add_argument("x", type=float)
    t.add_argument("y", type=float)
    sw = sub.add_parser("swipe")
    for k in ("x1", "y1", "x2", "y2"):
        sw.add_argument(k, type=float)
    sw.add_argument("--ms", type=int, default=250)
    k = sub.add_parser("key")
    k.add_argument("key")
    w = sub.add_parser("wait")
    w.add_argument("ms", type=int)
    r = sub.add_parser("rec")
    r.add_argument("action", choices=["start", "stop"])
    r.add_argument("name", nargs="?")
    m = sub.add_parser("mark")
    m.add_argument("label")
    pl = sub.add_parser("play")
    pl.add_argument("script")
    pl.add_argument("--take")
    pl.add_argument("--reload", action="store_true", help="web: reload the game before the take")
    sub.add_parser("status")
    sub.add_parser("stop")
    a = p.parse_args()

    if a.cmd == "serve":
        if not a.android and not a.url:
            p.error("serve needs --url (web) or --android")
        Path(a.out).mkdir(parents=True, exist_ok=True)
        ignore_media(a.out)
        asyncio.run(Server(a).serve())
        return
    req = {"cmd": a.cmd}
    if a.cmd == "shot":
        req["name"] = a.name
    elif a.cmd == "tap":
        req.update(x=a.x, y=a.y)
    elif a.cmd == "swipe":
        req.update(x1=a.x1, y1=a.y1, x2=a.x2, y2=a.y2, ms=a.ms)
    elif a.cmd == "key":
        req["key"] = a.key
    elif a.cmd == "wait":
        req["ms"] = a.ms
    elif a.cmd == "rec":
        if a.action == "start" and not a.name:
            p.error("rec start needs a NAME")
        req.update(action=a.action, name=a.name)
    elif a.cmd == "mark":
        req["label"] = a.label
    elif a.cmd == "play":
        req.update(script=str(Path(a.script).resolve()), reload=a.reload,
                   take=a.take or Path(a.script).stem + time.strftime("-%H%M%S"))
    send(a.out, req)


if __name__ == "__main__":
    main()
