"""Environment checks. Run before anything long, and again at the start of every run: the four
repos keep changing, so the flags and keys this skill relies on are re-read each time."""
from __future__ import annotations

import json
import os
import shutil
import socket
import sys
from pathlib import Path

from . import config as cfgmod
from .common import SKILL_DIR, check, read_json, run, sha256_file
from .stemforge import Api

FILTERS = ('acrossfade', 'ebur128', 'silencedetect', 'ssim', 'lowpass', 'aresample')
FLAGS = {
    'downloader': {('remix', '--help'): ('--top', '--no-download', '--html', '--chart'),
                   ('originals', '--help'): ('--limit', '--interval', '--run-id'),
                   ('report', '--help'): ('--json', '--run-id')},
    'mixcover': {('--help',): ('--all', '--crossfade', '--title', '--subtitle', '--seed', '--image', '--dry-run',
                               '--thumb-tracks', '--no-chapters', '--chapters', '--preset')},
    'visualizer': {('--help',): ('--bg', '--logo', '--preset', '--fps', '--size', '--start', '--duration', '--set',
                                 '--workers')},
}
ENTRY = {'downloader': 'run.py', 'mixcover': 'main.py', 'visualizer': 'main.py'}
STEMFORGE_TEXT = {
    'backend/api/auto_remix.py': ('@router.post("/upload")', '@router.post("/{job_id}/retry")',
                                  '@router.get("/{job_id}/download")', 'target_bpm', 'output_format'),
    'backend/main.py': ('STEMFORGE_REMIX_RETENTION_DAYS',),
}
PRESET_KEYS = ('background.dim', 'effects.shake.enabled', 'effects.bg_zoom.enabled', 'effects.bg_zoom.amount',
               'effects.circular_spectrum.enabled', 'effects.particles.enabled', 'effects.vignette.enabled',
               'effects.logo_pulse.enabled')
MIXCOVER_KEYS = ('layout.margin', 'fonts.track', 'fonts.number', 'colors.primary', 'colors.secondary', 'colors.accent',
                 'colors.panel', 'colors.background')


def port_open(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1.0)
        return s.connect_ex((host, int(port))) == 0


def mixcover_preset_check(cfg: dict) -> dict:
    """The side column of the video background is drawn with m10-mixcover's Pillow, in the fonts
    and colours of the preset the cover uses, inside its margin. Look those keys up, resolve the
    font files and import the modules the helper uses, so a change in that repo shows up here
    and not at the end of a long run."""
    mc = _repo(cfg, 'mixcover')
    code = ('import json, sys\nimport PIL\nfrom mixcover.fonts import resolve\nfrom mixcover.preset import Preset\n'
            'p = Preset.load(sys.argv[1])\n'
            'gone = [k for k in sys.argv[2:] if p.get(k, ...) is ...]\n'
            '[resolve(p.get(k)) for k in ("fonts.track", "fonts.number") if k not in gone]\n'
            'print(json.dumps(gone))')
    rc, out, err = run([mc / '.venv' / 'bin' / 'python', '-c', code, str(cfg['cover']['preset']), *MIXCOVER_KEYS],
                       cwd=str(mc), timeout=120)
    if rc != 0 or not out.strip():
        return check('mixcover_preset', 'FAIL', f'không nạp được preset {cfg["cover"]["preset"]}, font hoặc Pillow của m10-mixcover: '
                                                f'{err.strip()[-200:]}')
    gone = json.loads(out.strip().splitlines()[-1])
    if not gone:
        return check('mixcover_preset', 'PASS', 'preset có đủ font, màu và lề để vẽ cột chữ ở mép nền video')
    needed = cfg['video'].get('look') != 'cover'
    return check('mixcover_preset', 'FAIL' if needed else 'WARN',
                 f'preset của m10-mixcover không còn khoá {gone}: không vẽ được cột chữ ở mép nền video; '
                 'đặt video.tracklist thành none cho tới khi skill được sửa')


def _repo(cfg, name):
    path = cfg['repos'].get(name)
    return Path(path) if path else None


def run_preflight(cfg: dict, run_dir=None, count: int | None = None, deep: bool = False, need_server: bool = True) -> list[dict]:
    checks = []
    count = count or cfg['selection']['count']

    # tools
    missing = [t for t in ('ffmpeg', 'ffprobe') if not shutil.which(t)]
    if missing:
        checks.append(check('tools', 'FAIL', f'thiếu {", ".join(missing)}'))
    else:
        rc, out, _ = run(['ffmpeg', '-hide_banner', '-filters'], timeout=60)
        absent = [f for f in FILTERS if f' {f} ' not in out]
        checks.append(check('tools', 'FAIL' if absent else 'PASS',
                            f'ffmpeg thiếu filter {absent}' if absent else 'ffmpeg, ffprobe và các filter cần dùng'))
    checks.append(check('python', 'PASS' if sys.version_info >= (3, 10) else 'FAIL',
                        f'Python {sys.version_info.major}.{sys.version_info.minor}'))

    # repos and their interpreters
    ok_repos = {}
    for name in cfgmod.REPOS:
        repo = _repo(cfg, name)
        python = repo / '.venv' / 'bin' / 'python' if repo else None
        ok = bool(repo and repo.is_dir() and python.is_file())
        ok_repos[name] = ok
        checks.append(check(f'repo_{name}', 'PASS' if ok else 'FAIL',
                            str(repo) if ok else f'thiếu repo hoặc .venv/bin/python: {repo}'))

    # the flags this skill passes must still exist
    for name, calls in FLAGS.items():
        if not ok_repos[name]:
            continue
        repo = _repo(cfg, name)
        gone = []
        for args, flags in calls.items():
            rc, out, err = run([repo / '.venv' / 'bin' / 'python', repo / ENTRY[name], *args], cwd=str(repo), timeout=120)
            text = out + err
            gone += [f'{" ".join(args[:-1]) or ENTRY[name]} {f}' for f in flags if f not in text]
        checks.append(check(f'flags_{name}', 'FAIL' if gone else 'PASS',
                            f'không còn thấy: {gone}' if gone else 'các flag skill dùng đều còn'))

    if ok_repos['stemforge']:
        sf = _repo(cfg, 'stemforge')
        gone = []
        for rel, needles in STEMFORGE_TEXT.items():
            text = (sf / rel).read_text(encoding='utf-8', errors='replace') if (sf / rel).is_file() else ''
            gone += [f'{rel}: {n}' for n in needles if n not in text]
        preset = sf / 'presets' / 'remix' / f'{cfgmod.GENRE}.json'
        if not preset.is_file():
            gone.append(f'preset {preset.name}')
        checks.append(check('flags_stemforge', 'FAIL' if gone else 'PASS',
                            f'không còn thấy: {gone}' if gone else f'API Auto Remix và preset {cfgmod.GENRE}'))

        # editable installs must point at this checkout (they break when the repo is moved)
        stale = []
        for pth in (sf / '.venv' / 'lib').glob('python*/site-packages/_editable_impl_*.pth'):
            stale += [f'{pth.name} -> {line}' for line in set(pth.read_text().split()) if not Path(line).exists()]
        rc, _, _ = run([sf / '.venv' / 'bin' / 'python', '-c',
                        'import importlib.util as u, sys; sys.exit(0 if u.find_spec("acestep") else 1)'], cwd=str(sf), timeout=120)
        bad = bool(stale) or rc != 0
        checks.append(check('stemforge_env', 'FAIL' if bad else 'PASS',
                            ('venv trỏ về đường dẫn cũ, chạy `uv sync --locked` trong repo StemForge: ' + '; '.join(stale[:2]))
                            if bad else 'venv khớp vị trí repo, import được acestep'))
        checks.append(_models(sf, deep))

    if ok_repos['visualizer']:
        vz = _repo(cfg, 'visualizer')
        preset = vz / 'presets' / f'{cfg["video"]["preset"]}.yaml'
        code = ('import json, sys, yaml\n'
                'from visualizer.preset import load_preset\n'
                'print(json.dumps(load_preset(sys.argv[1], [])))')
        rc, out, err = run([vz / '.venv' / 'bin' / 'python', '-c', code, cfg['video']['preset']], cwd=str(vz), timeout=120)
        if rc != 0:
            checks.append(check('visualizer_preset', 'FAIL', f'không nạp được preset {preset.name}: {err.strip()[-200:]}'))
        else:
            data = json.loads(out)
            gone = []
            for key in PRESET_KEYS:
                node = data
                for part in key.split('.'):
                    node = node.get(part) if isinstance(node, dict) else None
                    if node is None:
                        gone.append(key)
                        break
            checks.append(check('visualizer_preset', 'FAIL' if gone else 'PASS',
                                f'preset thiếu khoá: {gone}' if gone else f'preset {cfg["video"]["preset"]} có đủ khoá lớp phủ'))

    if ok_repos['mixcover']:
        mc = _repo(cfg, 'mixcover')
        rc, out, err = run([mc / '.venv' / 'bin' / 'python', mc / 'main.py', '--check'], cwd=str(mc), timeout=120)
        checks.append(check('mixcover_env', 'PASS' if rc == 0 else 'FAIL',
                            'main.py --check đạt' if rc == 0 else (out + err).strip()[-200:]))
        if cfg['video'].get('tracklist', 'side') == 'side':
            checks.append(mixcover_preset_check(cfg))
        if not cfg['cover'].get('dry_run') and not cfg['cover'].get('image'):
            env = (mc / '.env').read_text(encoding='utf-8', errors='replace') if (mc / '.env').is_file() else ''
            have = [n for n in ('CLOUDFLARE_API_TOKEN', 'CLOUDFLARE_ACCOUNT_ID')
                    if any(line.startswith(n + '=') and len(line) > len(n) + 1 for line in env.splitlines())]
            checks.append(check('image_provider_keys', 'PASS' if len(have) == 2 else 'WARN',
                                'có CLOUDFLARE_API_TOKEN và CLOUDFLARE_ACCOUNT_ID trong .env' if len(have) == 2 else
                                'thiếu biến Cloudflare trong .env của m10-mixcover; dùng cover.image hoặc cover.dry_run'))

    # disk, GPU, ports
    target = Path(run_dir) if run_dir else Path(cfg['_workspace'])
    target.mkdir(parents=True, exist_ok=True)
    need_gb = count * 2.5 + 8
    free_gb = min(shutil.disk_usage(target).free, shutil.disk_usage(Path.home()).free) / 1e9
    checks.append(check('disk', 'PASS' if free_gb >= need_gb else 'WARN' if free_gb >= count * 2.5 else 'FAIL',
                        f'trống {free_gb:.0f} GB, cần khoảng {need_gb:.0f} GB cho {count} bài'))
    rc, out, _ = run(['nvidia-smi', '--query-gpu=name,memory.total,memory.used', '--format=csv,noheader,nounits'], timeout=30)
    if rc == 0 and out.strip():
        name, total, used = [x.strip() for x in out.strip().splitlines()[0].split(',')]
        free = int(total) - int(used)
        checks.append(check('gpu', 'PASS' if free >= 10000 else 'WARN',
                            f'{name}: trống {free} MB / {total} MB' + ('' if free >= 10000 else '; chặng phối cần khoảng 10 GB')))
    else:
        checks.append(check('gpu', 'WARN', 'không gọi được nvidia-smi'))
    rm = cfg['remix']
    busy = [p for p in (rm['port'], rm['acestep_port']) if port_open(rm['host'], p)]
    if not need_server:                             # every remix of this run is done: StemForge will not be started
        checks.append(check('ports', 'SKIP', 'chặng phối đã xong: lượt này không cần server StemForge nữa'))
    elif Api(rm['host'], rm['port']).health():
        checks.append(check('ports', 'WARN', f'đã có server StemForge ở cổng {rm["port"]}; skill sẽ dùng lại nó và không dừng nó'))
    elif busy:
        key = 'remix.port' if rm['port'] in busy else 'remix.acestep_port'
        checks.append(check('ports', 'FAIL', f'cổng {busy} đang do một chương trình khác dùng (không phải StemForge). '
                                             f'Đổi cổng cho skill bằng `pipeline.py set {key} <cổng trống>`, hoặc đóng chương trình đó; '
                                             'skill không dừng tiến trình nó không khởi động'))
    else:
        checks.append(check('ports', 'PASS', f'cổng {rm["port"]} và {rm["acestep_port"]} đang trống'))

    # NCT, pane, YouTube limits
    live = cfg['nct'].get('live_access')
    checks.append(check('nct_access', 'PASS',
                        'đã bật trong config' if live is True else 'đang tắt: chế độ offline' if live is False
                        else 'chưa hỏi (câu hỏi lần đầu)'))
    herdr = bool(os.environ.get('HERDR_PANE_ID')) and shutil.which('herdr') is not None
    checks.append(check('pane', 'PASS' if herdr else 'SKIP',
                        'herdr có sẵn: panel tiến độ mở được' if herdr else 'không có herdr: in khối trạng thái vào chat'))
    limits = read_json(SKILL_DIR / 'references' / 'youtube_limits.json') or {}
    items = limits.get('limits') or {}
    unverified = [k for k, v in items.items() if not v.get('verified')]
    checks.append(check('youtube_limits', 'WARN' if unverified or not items else 'PASS',
                        f'chưa xác minh: {unverified}' if unverified else
                        f'{len(items)} giới hạn đã xác minh ({limits.get("checked_on")})' if items else 'thiếu youtube_limits.json'))
    return checks


def _models(sf: Path, deep: bool) -> dict:
    """StemForge's own `auto_remix_setup.py --verify` compares absolute paths recorded when the
    models were downloaded, so it reports every file missing once the repo has moved. This
    check maps those paths onto the current checkout and compares sizes (SHA-256 with --deep)."""
    manifest = read_json(Path('~/.cache/stemforge/auto_remix_manifest.json').expanduser())
    if not manifest:
        return check('stemforge_models', 'WARN', 'không có auto_remix_manifest.json; server sẽ tự báo nếu thiếu model')
    bad, total = [], 0
    for model in manifest.get('models', []):
        for entry in model.get('files', []):
            recorded = entry.get('file') or ''
            path = Path(recorded)
            if not path.is_file() and '/Ace-Step-Wrangler/' in recorded:
                path = sf / 'Ace-Step-Wrangler' / recorded.split('/Ace-Step-Wrangler/', 1)[1]
            total += 1
            if not path.is_file() or str(path.stat().st_size) != str(entry.get('size')):
                if model.get('required', True):
                    bad.append(f'{model.get("id")}: {path.name}')
            elif deep and entry.get('sha256') and sha256_file(path) != entry['sha256']:
                bad.append(f'{model.get("id")}: {path.name} (sai SHA-256)')
    return check('stemforge_models', 'FAIL' if bad else 'PASS',
                 f'thiếu hoặc sai kích thước: {bad[:4]}' if bad else
                 f'{total} file model đủ' + (' và đúng SHA-256' if deep else ' (so kích thước)'))
