#!/usr/bin/env python3
"""Telegram remote: decide gates, send commands and files, and open Claude sessions from the phone while
away from the computer. At the computer nothing changes and the chat stays the place to decide; Telegram
only speaks up in away mode (`/away` on the phone, or `mode away` from the chat) and keeps the machine
awake then.

  scripts/telegram_bridge.py setup                          # pair the bot with your chat, once
  scripts/telegram_bridge.py install-service                # run `serve` as a systemd user service, once
  scripts/telegram_bridge.py uninstall-service
  scripts/telegram_bridge.py serve                          # the daemon: the only Telegram reader, all games
  scripts/telegram_bridge.py watch REPO                     # register REPO, then serve (no service installed)
  scripts/telegram_bridge.py register REPO                  # make REPO a game the phone can reach
  scripts/telegram_bridge.py ask REPO GATE QUESTION [--option TEXT]...  # wait for a decision
  scripts/telegram_bridge.py close REPO --answered-here ANSWER          # decided at the computer
  scripts/telegram_bridge.py answers REPO                   # decisions that arrived while no session waited
  scripts/telegram_bridge.py inbox REPO                     # unread commands, texts and files, as JSON lines
  scripts/telegram_bridge.py mode here|away                 # switch from the chat
  scripts/telegram_bridge.py send REPO [TEXT] [--file PATH [--caption TEXT]]...  # files go in order
  scripts/telegram_bridge.py hook                          # Claude Code Notification hook (stdin JSON)

Config lives outside every repo: ~/.config/game-clone-pipeline/telegram.env (chmod 600) with
TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID (the only chat that counts as the human) and GAMES_DIR (default
~/Documents/projects); environment variables override it. Games are GAMES_DIR/*/.clone/status.md plus
registered repos. Per-game state lives in REPO/.clone/telegram/ (git-ignored); the mode, the current game
and the update offset in ~/.local/state/game-clone-pipeline/telegram/.

From the phone, `/open <game>` and `/new <idea>` start `claude --bg` sessions (permission mode auto);
`claude attach <session id>` takes one over at the computer (a `/new` session is named after the idea,
not the game). A Telegram answer for a game with no live session opens one, which reads it with
`answers`. A session belongs to a game when it runs in the repo or one of its worktrees, carries the
game's name, or ran a subcommand on the repo. Phone-started sessions carry `hook`: it reports a
permission prompt to the phone and refuses `EnterWorktree` with `path:` (SKILL.md rule 5). In away mode
`serve` warns the phone once when no question is pending and either a busy session has written nothing
for STALL_MINUTES (most likely waiting on a prompt only the computer can answer) or the game's sessions
have all stopped with stages left and nothing in `Waiting on:` (it quit without asking anything) or
with an answer of yours unread (it died before reading it, e.g. on an expired login).

`ask` prints one JSON line and exits 0: {"event": "answer", "answer", "by": "telegram"|"computer", ...}
or {"event": "inbox", "unread": n} when a command arrived first (read `inbox`, then ask again: the
same question is reused, not resent). GATE `S8-apple` (SKILL.md rule 13) takes only `--option "Để sau"`
and settles only on that deferral or on a reply with the VALID build number and the app's Apple ID, which
its answer carries as "build" and "apple_id"; any other reply keeps the question open and goes to the
inbox marked "held", and `close` refuses it. Exit codes: 64 usage, 66 no such repo, 69 Telegram not set
up or `serve` not running, 70 Telegram API or systemctl error. Standard library only.
"""
import argparse
import contextlib
import fcntl
import getpass
import glob
import html
import json
import mimetypes
import os
import re
import shlex
import shutil
import signal
import subprocess
import sys
import threading
import time
import unicodedata
import urllib.error
import urllib.request
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import steps_pane  # noqa: E402

SCRIPT = os.path.abspath(__file__)
CONFIG_HOME = os.environ.get('XDG_CONFIG_HOME') or os.path.expanduser('~/.config')
STATE_HOME = os.environ.get('XDG_STATE_HOME') or os.path.expanduser('~/.local/state')
CONFIG_DIR = os.path.join(CONFIG_HOME, 'game-clone-pipeline')
CONFIG = os.path.join(CONFIG_DIR, 'telegram.env')
REPOS = os.path.join(CONFIG_DIR, 'repos.json')
STATE = os.path.join(STATE_HOME, 'game-clone-pipeline', 'telegram')
UNIT_NAME = 'game-clone-telegram.service'
UNIT = os.path.join(CONFIG_HOME, 'systemd', 'user', UNIT_NAME)
API_BASE = 'https://api.telegram.org'
DEFAULT_GAMES_DIR = '~/Documents/projects'
WHO = 'game-clone-pipeline'
POLL_SECONDS = 10
SLEEP_GAP = 60
STALL_MINUTES = 30
STALL_CHECK_SECONDS = 300
ENDED_MINUTES = 10
ENDED_HOURS = 24
DOWNLOAD_LIMIT = 20 * 1024 * 1024
UPLOAD_LIMIT = 50 * 1024 * 1024
PHOTO_LIMIT = 10 * 1024 * 1024
VIDEO_EXT = {'.mp4', '.mov', '.m4v', '.webm', '.mkv', '.avi', '.3gp'}
PHOTO_EXT = {'.png', '.jpg', '.jpeg', '.webp'}
APK_EXT = {'.apk', '.xapk', '.apks', '.aab'}
INBOX_COMMANDS = {'pause', 'resume', 'skip', 'redo', 'note'}
NEEDS_ARGS = {'skip', 'redo', 'note', 'new', 'use', 'hide', 'unhide'}
MODE_LABEL = {'here': 'ở máy', 'away': 'vắng mặt'}
SESSION_LABEL = {'idle': 'đang mở, không làm gì', 'waiting': 'chờ xác nhận trên máy'}
ANSI = re.compile(r'\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b\][^\x07]*\x07|\x1b[()][0-9A-Za-z]')
BACKGROUNDED = re.compile(r'backgrounded\s*·\s*(\S+)')
RESUME_PROMPT = ('/game-clone-pipeline Resume the game in {repo} (work in that folder). Started from Telegram: '
                 'the human is away. Follow the "Telegram remote" section: run `answers` and `inbox` first, ask '
                 'every decision with `ask`.')
NEW_PROMPT = ('/game-clone-pipeline Start a new game: {idea}\n\nStarted from Telegram: the human is away. Create '
              'the repo under {games_dir} with a working slug, run `register` on it, and ask everything else '
              'with `ask` as the "Telegram remote" section says.')
HELP = '\n'.join([
    '<b>📖 Lệnh</b>',
    '',
    '<b>Ra ngoài, về máy</b>',
    '/away · hỏi quyết định ở đây, giữ máy thức',
    '/back · về máy, Telegram im lặng',
    '',
    '<b>Game</b>',
    '/games · danh sách game, bước, phiên Claude',
    '/status [game] · đang ở bước nào',
    '/use &lt;game&gt; · chọn game để nói chuyện',
    '/hide &lt;game&gt;, /unhide &lt;game&gt; · ẩn, hiện trong /games',
    '',
    '<b>Phiên Claude</b>',
    '/open [game] · mở phiên chạy tiếp game',
    '/new &lt;ý tưởng hoặc link store&gt; · làm game mới',
    '/log [game] · phiên đang làm gì',
    '/stop [game] · dừng phiên mở từ điện thoại',
    '',
    '<b>Nhắn agent</b>',
    '/pause, /resume · dừng sau bước đang làm, chạy tiếp',
    '/skip &lt;bước&gt; · bỏ qua một bước',
    '/redo &lt;S…&gt; · làm lại một stage',
    '/note &lt;chữ&gt; · ghi chú cho agent',
    'Gửi video, APK, file data: lưu vào .clone/ của game đang chọn (tối đa 20 MB).',
    '',
    '👉 Có câu hỏi thì bấm nút hoặc gõ câu trả lời.',
])
HELP_WORDS = {'help', 'trợ giúp', 'tro giup', 'lệnh', 'menu'}
NO_GAME = '<b>❔ Chưa chọn game</b>\n\n👉 Xem /games, rồi chọn bằng /use &lt;game&gt;'
APPLE_GATE = 'S8-apple'
APPLE_LATER = 'Để sau'
APPLE_HINT = (f'Bấm {APPLE_LATER}. Khi build đã VALID trên TestFlight thì gõ số build và Apple ID của app '
              '(App Information → Apple ID), ví dụ: <code>build 1, Apple ID 1234567890</code>')
GATE_LABELS = {'G0': 'Chọn game (G0)', 'G0b': 'Duyệt SPEC (G0b)', 'G1': 'Duyệt thiết kế + tên (G1)',
               'G2': 'Chọn giao diện (G2)', 'G3': 'Duyệt IAP + giá (G3)', 'G4': 'Duyệt gói App Store (G4)',
               APPLE_GATE: 'Build trên Mac'}
APPLE_ID = re.compile(r'(?<!\d)\d{9,10}(?!\d)')
APPLE_BUILD = (re.compile(r'\(\s*(\d{1,6})\s*\)'),
               re.compile(r'build\D{0,12}?(?<![\d.])(\d{1,6})(?![\d.])', re.IGNORECASE),
               re.compile(r'(?<![\d.])(\d{1,6})(?![\d.])'))


class BotError(Exception):
    pass


class Parser(argparse.ArgumentParser):
    def error(self, message):
        self.print_usage(sys.stderr)
        print(f'{self.prog}: {message}', file=sys.stderr)
        sys.exit(64)


class Attach(argparse.Action):
    """`send` files: every --file joins the list in order, and a --caption labels the --file right before it."""

    def __call__(self, parser, namespace, value, option_string=None):
        files = list(getattr(namespace, 'files', None) or [])
        if '--file' in self.option_strings:
            files.append((value, None))
        elif files and files[-1][1] is None:
            files[-1] = (files[-1][0], value)
        else:
            parser.error('each --caption goes right after its own --file')
        namespace.files = files


def warn(text):
    print(f'telegram_bridge: {text}', file=sys.stderr, flush=True)


def now_iso():
    return time.strftime('%Y-%m-%dT%H:%M:%S%z')


# Config and the Bot API

def load_config():
    values = {}
    try:
        with open(CONFIG, encoding='utf-8') as f:
            for line in f:
                key, sep, val = line.strip().partition('=')
                if sep and not key.startswith('#'):
                    values[key.strip()] = val.strip().strip('"\'')
    except FileNotFoundError:
        pass
    games_dir = os.environ.get('GAMES_DIR') or values.get('GAMES_DIR') or DEFAULT_GAMES_DIR
    return {'token': os.environ.get('TELEGRAM_BOT_TOKEN') or values.get('TELEGRAM_BOT_TOKEN'),
            'chat': os.environ.get('TELEGRAM_CHAT_ID') or values.get('TELEGRAM_CHAT_ID'),
            'games_dir': os.path.abspath(os.path.expanduser(games_dir)),
            'base': (os.environ.get('TELEGRAM_API_BASE') or API_BASE).rstrip('/')}


def require_config():
    cfg = load_config()
    if not (cfg['token'] and cfg['chat']):
        warn(f'Telegram is not set up ({CONFIG}); run `telegram_bridge.py setup` once')
        sys.exit(69)
    return cfg


def multipart(fields, field, path):
    boundary = uuid.uuid4().hex
    name = os.path.basename(path)
    ctype = mimetypes.guess_type(name)[0] or 'application/octet-stream'
    parts = [f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode()
             for key, value in fields.items()]
    parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{field}"; filename="{name}"\r\n'
                 f'Content-Type: {ctype}\r\n\r\n'.encode())
    with open(path, 'rb') as f:
        parts.append(f.read())
    parts.append(f'\r\n--{boundary}--\r\n'.encode())
    return b''.join(parts), f'multipart/form-data; boundary={boundary}'


def api(cfg, method, params=None, file=None, timeout=30):
    """Call the Bot API; errors never carry the token."""
    url = f"{cfg['base']}/bot{cfg['token']}/{method}"
    if file:
        body, ctype = multipart(params or {}, *file)
    else:
        body, ctype = json.dumps(params or {}).encode(), 'application/json'
    request = urllib.request.Request(url, body, {'Content-Type': ctype})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as error:
        try:
            payload = json.load(error)
        except ValueError:
            raise BotError(f'{method}: HTTP {error.code}') from None
    except (urllib.error.URLError, OSError, ValueError) as error:
        raise BotError(f'{method}: {getattr(error, "reason", error)}') from None
    if not payload.get('ok'):
        raise BotError(f"{method}: {payload.get('description', 'failed')}")
    return payload['result']


# Messages are phone-sized cards in Telegram HTML: a bold first line, short lines, a 👉 line for the action.

def esc(text):
    return html.escape(str(text), quote=False)


def code(text):
    """Monospace, which the phone copies on a tap."""
    return f'<code>{esc(text)}</code>'


def card(icon, title, *blocks, action=None):
    """A message: bold ICON and TITLE, then the non-empty BLOCKS (HTML) a blank line apart, then 👉 ACTION."""
    parts = [f'<b>{icon} {esc(title)}</b>', *(block for block in blocks if block)]
    if action:
        parts.append(f'👉 {action}')
    return '\n\n'.join(parts)


def markup(text, repo=None):
    """Agent-written TEXT as card HTML: escaped, `code` tap-to-copy, **bold** bold, '- ' and '* ' bullets '• '.
    A leading '<game> · ' goes, since the card's first line names the game already."""
    text = text.strip()
    if repo:
        names = '|'.join(re.escape(name) for name in {display_name(repo), game_name(repo)})
        text = re.sub(rf'^(?:{names})\s*[·:–-]\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'^(\s*)[-*] ', r'\1• ', esc(text), flags=re.MULTILINE)
    text = re.sub(r'`([^`\n]+)`', r'<code>\1</code>', text)
    text = re.sub(r'\*\*([^*\n]+)\*\*', r'<b>\1</b>', text)
    return re.sub(r'\n{3,}', '\n\n', text)


def plain(text):
    """Card HTML as plain text, for when Telegram rejects the markup."""
    return html.unescape(re.sub(r'</?(?:b|i|code|pre)>', '', text))


def send_text(cfg, text, **extra):
    """Send TEXT (card HTML); markup Telegram rejects, a cut tag say, goes again as plain text."""
    params = {'chat_id': cfg['chat'], 'text': text[:4000], 'parse_mode': 'HTML', **extra}
    try:
        return api(cfg, 'sendMessage', params)
    except BotError as error:
        if "can't parse entities" not in str(error):
            raise
    del params['parse_mode']
    return api(cfg, 'sendMessage', {**params, 'text': plain(text)[:4000]})


def send_pre(cfg, text):
    return send_text(cfg, '<pre>' + esc(text[-3800:]) + '</pre>')


def send_file(cfg, path, caption=None):
    ext, size = os.path.splitext(path)[1].lower(), os.path.getsize(path)
    if size > UPLOAD_LIMIT:
        raise BotError(f'{os.path.basename(path)} is {size // 2**20} MB; bots can upload 50 MB at most')
    if ext in VIDEO_EXT:
        method, field = 'sendVideo', 'video'
    elif ext in PHOTO_EXT and size <= PHOTO_LIMIT:
        method, field = 'sendPhoto', 'photo'
    elif ext == '.gif':
        method, field = 'sendAnimation', 'animation'
    else:
        method, field = 'sendDocument', 'document'
    params = {'chat_id': cfg['chat']}
    if caption:
        params['caption'] = caption[:1000]
    return api(cfg, method, params, file=(field, path), timeout=600)


def retire(cfg, message_id, text):
    """Replace a question's text (card HTML) and drop its buttons."""
    try:
        api(cfg, 'editMessageText', {'chat_id': cfg['chat'], 'message_id': message_id, 'text': text[:4000],
                                     'parse_mode': 'HTML'})
    except BotError as error:
        warn(str(error))


def download(cfg, file_id, dest):
    info = api(cfg, 'getFile', {'file_id': file_id})
    url = f"{cfg['base']}/file/bot{cfg['token']}/{info['file_path']}"
    try:
        with urllib.request.urlopen(url, timeout=300) as response, open(dest + '.part', 'wb') as out:
            shutil.copyfileobj(response, out)
    except (urllib.error.URLError, OSError) as error:
        raise BotError(f'download: {getattr(error, "reason", error)}') from None
    os.replace(dest + '.part', dest)


# State: per game in REPO/.clone/telegram/, global in STATE

def state_dir(repo):
    folder = os.path.join(repo, '.clone', 'telegram')
    os.makedirs(folder, exist_ok=True)
    return folder


def state_file(repo, name):
    return os.path.join(state_dir(repo), name)


def global_file(name):
    os.makedirs(STATE, exist_ok=True)
    return os.path.join(STATE, name)


def read_json(path):
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, ValueError):
        return None


def read_text(path):
    try:
        with open(path, encoding='utf-8') as f:
            return f.read().strip()
    except FileNotFoundError:
        return None


def write_text(path, text):
    tmp = f'{path}.{os.getpid()}.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        f.write(text)
    os.replace(tmp, path)


def write_json(path, data):
    write_text(path, json.dumps(data, ensure_ascii=False))


@contextlib.contextmanager
def locked(repo):
    with open(state_file(repo, 'lock'), 'w') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        yield


def get_mode():
    mode = read_text(global_file('mode'))
    return mode if mode in MODE_LABEL else 'here'


def serve_pid():
    try:
        pid = int(read_text(global_file('serve.pid')) or '')
        os.kill(pid, 0)
    except (ValueError, ProcessLookupError):
        return None
    except PermissionError:
        pass
    return pid


def inbox_lines(repo):
    try:
        with open(state_file(repo, 'inbox.jsonl'), encoding='utf-8') as f:
            return f.read().splitlines()
    except FileNotFoundError:
        return []


def inbox_cursor(repo):
    try:
        return int(read_text(state_file(repo, 'inbox.cursor')) or 0)
    except ValueError:
        return 0


def to_inbox(repo, entry):
    with open(state_file(repo, 'inbox.jsonl'), 'a', encoding='utf-8') as f:
        f.write(json.dumps({'at': now_iso(), **entry}, ensure_ascii=False) + '\n')


# Games

def register(repo):
    repos = read_json(REPOS) or []
    if repo not in repos:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        write_json(REPOS, repos + [repo])
    set_current(repo)


def games(cfg):
    """{name: repo} for registered repos and GAMES_DIR/*/.clone/status.md."""
    found = {}
    candidates = list(read_json(REPOS) or [])
    with contextlib.suppress(FileNotFoundError, NotADirectoryError):
        candidates += sorted(os.path.join(cfg['games_dir'], name) for name in os.listdir(cfg['games_dir'])
                             if os.path.isfile(os.path.join(cfg['games_dir'], name, '.clone', 'status.md')))
    for repo in candidates:
        if os.path.isdir(repo):
            found.setdefault(os.path.basename(repo), repo)
    return found


def get_current(cfg):
    repo = read_text(global_file('current'))
    return repo if repo and os.path.isdir(repo) else None


def set_current(repo):
    write_text(global_file('current'), repo)


def hidden():
    """Repos `/hide` took off the /games list; everything else still sees them."""
    return read_json(global_file('hidden.json')) or []


def set_hidden(repo, on):
    real, rest = os.path.realpath(repo), [path for path in hidden() if path != os.path.realpath(repo)]
    write_json(global_file('hidden.json'), rest + [real] if on else rest)


def resolve_game(cfg, name):
    """The repo `name` points at (exact, then unique partial match), else the current game, else the only one."""
    found = games(cfg)
    if name:
        if name in found:
            return found[name]
        partial = [repo for game, repo in found.items() if name.lower() in game.lower()]
        return partial[0] if len(partial) == 1 else None
    current = get_current(cfg)
    if current:
        return current
    return next(iter(found.values())) if len(found) == 1 else None


def game_name(repo):
    return os.path.basename(repo)


def display_name(repo):
    """The game's name as status.md spells it (Moss Lantern); the folder name until it has one."""
    return (read_state(repo) or {}).get('name') or game_name(repo)


# Claude Code sessions

def claude(*args, cwd=None, timeout=60):
    binary = shutil.which('claude')
    if not binary:
        raise BotError('không tìm thấy lệnh claude trên máy (PATH)')
    done = subprocess.run([binary, *args], cwd=cwd, capture_output=True, text=True, timeout=timeout,
                          stdin=subprocess.DEVNULL)
    if done.returncode != 0:
        raise BotError(f'claude {args[0]}: {(done.stderr or done.stdout).strip()[:300]}')
    return done.stdout


def agents(include_done=False):
    return json.loads(claude('agents', '--json', *(['--all'] if include_done else [])) or '[]')


def link_session(repo):
    """Remember the Claude session running this subcommand as REPO's. A `/new` session runs from GAMES_DIR
    under the idea's name, so neither its folder nor its name tells which game it builds."""
    sid = os.environ.get('CLAUDE_CODE_SESSION_ID')
    if not sid:
        return
    linked = read_json(state_file(repo, 'sessions.json')) or []
    if sid not in linked:
        write_json(state_file(repo, 'sessions.json'), (linked + [sid])[-20:])


def belongs(session, repo):
    """A session is REPO's when it runs in REPO or one of its worktrees, carries the game's name, or ran a
    subcommand on REPO (`link_session`)."""
    real, cwd = os.path.realpath(repo), session.get('cwd')
    if cwd and (os.path.realpath(cwd) + os.sep).startswith(real + os.sep):
        return True
    return (session.get('name') == game_name(repo)
            or session.get('sessionId') in (read_json(state_file(repo, 'sessions.json')) or []))


def sessions_for(repo, include_done=False, listing=None):
    """REPO's Claude Code sessions, newest first; LISTING is a fetched `agents` list to reuse."""
    mine = [s for s in (agents(include_done) if listing is None else listing) if belongs(s, repo)]
    return sorted(mine, key=lambda s: s.get('startedAt') or 0, reverse=True)


def session_repo(cfg, sid, cwd):
    """The game a session works on, from its id and folder, or None."""
    session = {'sessionId': sid, 'cwd': cwd}
    return next((repo for repo in games(cfg).values() if belongs(session, repo)), None)


def session_ref(session):
    return session.get('id') or session.get('name') or session.get('sessionId')


def attach_command(ref):
    """`claude attach REF` as typed in a terminal at the computer. Sessions live per config folder: one
    under another CLAUDE_CONFIG_DIR (an mcc profile) is invisible to a plain `claude attach`."""
    config = os.environ.get('CLAUDE_CONFIG_DIR')
    if config and os.path.realpath(config) != os.path.realpath(os.path.expanduser('~/.claude')):
        return f'CLAUDE_CONFIG_DIR={shlex.quote(config)} claude attach {ref}'
    return f'claude attach {ref}'


def session_state(session):
    return ' · '.join(str(session[key]) for key in ('status', 'state') if session.get(key)) or '?'


def transcript(session):
    """Path of a session's transcript (the newest, when a worktree move left several), or None."""
    config_dir = os.environ.get('CLAUDE_CONFIG_DIR') or os.path.expanduser('~/.claude')
    sid = session.get('sessionId')
    matches = glob.glob(os.path.join(glob.escape(config_dir), 'projects', '*', f'{sid}.jsonl')) if sid else []
    return max(matches, key=os.path.getmtime) if matches else None


def transcript_items(lines):
    """Prompts, replies and tool calls of transcript lines, as short phone-readable strings."""
    items = []
    for line in lines:
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        content = (entry.get('message') or {}).get('content')
        if entry.get('type') == 'user' and isinstance(content, str):
            items.append('👤 ' + content.strip())
        elif entry.get('type') == 'assistant' and isinstance(content, list):
            for block in content:
                if block.get('type') == 'text' and block.get('text', '').strip():
                    items.append('🤖 ' + block['text'].strip())
                elif block.get('type') == 'tool_use':
                    args = block.get('input') or {}
                    detail = next((str(args[key]) for key in ('description', 'command', 'file_path', 'skill', 'pattern', 'path', 'name')
                                   if args.get(key)), '')
                    items.append(f"🔧 {block.get('name')}" + (f': {detail}' if detail else ''))
    return items


def recent_activity(session, limit=12):
    """The last prompts, replies and tool calls of a session, from its transcript; None if not found."""
    path = transcript(session)
    if not path:
        return None
    with open(path, encoding='utf-8') as f:
        items = transcript_items(f)
    return '\n\n'.join(item if len(item) <= 500 else item[:500] + '…' for item in items[-limit:]) or '(chưa có gì)'


def tail_items(path, tail=512 * 1024):
    """Transcript items read from the end of PATH (transcripts grow to tens of MB)."""
    start = max(0, os.path.getsize(path) - tail)
    with open(path, 'rb') as f:
        f.seek(start)
        lines = f.read().decode('utf-8', 'replace').splitlines()[1 if start else 0:]
    return transcript_items(lines)


def last_tool(path):
    """The last tool call in a transcript."""
    calls = [item for item in tail_items(path) if item.startswith('🔧')]
    return calls[-1][2:].strip()[:300] if calls else None


def last_reply(path):
    """The end of the last reply in a transcript, where a run says how it ended."""
    replies = [item[2:].strip() for item in tail_items(path) if item.startswith('🤖')]
    if not replies:
        return None
    return replies[-1] if len(replies[-1]) <= 300 else '…' + replies[-1][-300:]


def minutes_since(path):
    return int((time.time() - os.path.getmtime(path)) // 60)


def hook_settings():
    hook = [{'type': 'command', 'command': shlex.join([sys.executable, SCRIPT, 'hook'])}]
    return json.dumps({'hooks': {'Notification': [{'hooks': hook}],
                                 'PreToolUse': [{'matcher': 'EnterWorktree', 'hooks': hook}]}})


def launch(cfg, cwd, name, prompt):
    """Start `claude --bg` in CWD; the phone is where the human is, so switch to away."""
    out = claude('--bg', '-n', name, '--permission-mode', 'auto', '--settings', hook_settings(), prompt, cwd=cwd)
    if get_mode() != 'away':
        set_mode(cfg, 'away', quiet=True)
    found = BACKGROUNDED.search(out)
    return found.group(1) if found else name


def resume(cfg, repo):
    """Open a session that resumes REPO. Claude may never have been opened in a repo the pipeline created,
    and `--bg` refuses an untrusted folder: then start from its parent (GAMES_DIR, where `/new` runs)."""
    prompt = RESUME_PROMPT.format(repo=repo)
    try:
        return launch(cfg, repo, game_name(repo), prompt)
    except BotError as error:
        if 'not trusted' not in str(error):
            raise
    parent = os.path.dirname(repo)
    ref = launch(cfg, parent, game_name(repo), prompt)
    with contextlib.suppress(BotError):
        send_text(cfg, card('ℹ️', display_name(repo),
                            f'Claude chưa được tin cậy (trust) trong thư mục game, nên phiên chạy từ {code(parent)}.',
                            action=f'Sửa hẳn: ở máy chạy {code("claude")} một lần trong {code(repo)} và chấp nhận.'),
                  disable_notification=True)
    return ref


def ensure_session(cfg, repo):
    """After a phone answer: open a session to act on it when none is running for REPO."""
    try:
        if sessions_for(repo):
            return
        ref = resume(cfg, repo)
        send_text(cfg, card('▶', display_name(repo), 'Không có phiên Claude nào đang chạy, đã mở phiên mới để chạy tiếp.',
                            action=f'Ở máy: {code(attach_command(ref))}'))
    except (BotError, subprocess.TimeoutExpired, ValueError) as error:
        warn(str(error))
        with contextlib.suppress(BotError):
            send_text(cfg, card('⚠️', display_name(repo), 'Đã ghi câu trả lời nhưng không mở được phiên Claude.',
                                esc(error), action=f'Thử lại: /open {game_name(repo)}'))


# Questions and answers

def gate_label(gate):
    """What a question is about in the human's words: the gate's name, else its stage's (S8-submit → iOS + nộp)."""
    stage = re.match(r'S\d+', gate)
    return GATE_LABELS.get(gate) or (stage and steps_pane.LABELS.get(stage.group())) or gate


def question_text(repo, pending):
    if pending['gate'] == APPLE_GATE:
        action = APPLE_HINT
    else:
        action = 'Bấm một nút, hoặc gõ câu trả lời.' if pending['options'] else 'Gõ câu trả lời.'
    return card('❓', f"{display_name(repo)} · {gate_label(pending['gate'])}", markup(pending['question'], repo),
                action=action)


def settled_text(repo, gate, answer, by='telegram'):
    """What a question becomes once decided: its subject and the decision."""
    who = 'Bạn chọn' if by == 'telegram' else 'Đã quyết trên máy tính'
    return card('✓', f'{display_name(repo)} · {gate_label(gate)}', f'{who}: <b>{esc(answer)}</b>',
                'Agent đang chạy tiếp.' if by == 'telegram' else '')


def deliver_pending(repo, cfg):
    """Send REPO's pending question with its buttons unless Telegram has it already. Hold the lock."""
    path = state_file(repo, 'pending.json')
    pending = read_json(path)
    if not pending or pending.get('message_id'):
        return
    extra = {}
    if pending['options']:
        extra['reply_markup'] = {'inline_keyboard': [[{'text': option[:60], 'callback_data': f"a|{pending['id']}|{i}"}]
                                                     for i, option in enumerate(pending['options'])]}
    pending['message_id'] = send_text(cfg, question_text(repo, pending), **extra)['message_id']
    write_json(path, pending)
    set_current(repo)


def fold(text):
    """TEXT in lower case without Vietnamese diacritics, for matching typed words."""
    text = unicodedata.normalize('NFD', text.lower().replace('đ', 'd'))
    return ''.join(c for c in text if not unicodedata.combining(c)).strip(' .!')


def apple_answer(text):
    """What a reply to the `S8-apple` question settles it with: the deferral, or the reply plus the build number
    and the app's Apple ID typed off App Store Connect (SKILL.md rule 13). None for anything else, so "Build
    VALID" or "xong" never confirms a build."""
    if fold(text) in ('de sau', 'later'):
        return APPLE_LATER, {}
    if not (apple_id := APPLE_ID.search(text)):
        return None
    rest = f'{text[:apple_id.start()]} {text[apple_id.end():]}'
    build = next((match.group(1) for pattern in APPLE_BUILD if (match := pattern.search(rest))), None)
    return (text, {'build': build, 'apple_id': apple_id.group()}) if build else None


def record_answer(repo, answer, by, **fields):
    """Settle REPO's pending question; returns it, or None when nothing was pending. Hold the lock."""
    path = state_file(repo, 'pending.json')
    pending = read_json(path)
    if not pending:
        return None
    write_json(state_file(repo, f"answer-{pending['id']}.json"),
               {'id': pending['id'], 'gate': pending['gate'], 'question': pending['question'],
                'answer': answer, 'by': by, 'at': now_iso(), **fields})
    os.remove(path)
    return pending


def set_mode(cfg, mode, quiet=False):
    before = get_mode()
    write_text(global_file('mode'), mode)
    if mode == before:
        return
    try:
        if mode == 'away':
            if not quiet:
                send_text(cfg, card('🛫', 'Chế độ vắng mặt', 'Quyết định sẽ được hỏi ở đây.\nMáy được giữ thức.',
                                    action='Về máy thì gõ /back'))
            for repo in games(cfg).values():
                with locked(repo):
                    deliver_pending(repo, cfg)
        else:
            send_text(cfg, card('🏠', 'Đã về máy', 'Telegram im lặng, quyết định trong chat trên máy tính.',
                                action='Ra ngoài thì gõ /away'), disable_notification=True)
    except BotError as error:
        warn(str(error))


def status_text(repo):
    lines = steps_pane.render(repo, 40, color=False)
    lines.append(f'Chế độ: {MODE_LABEL[get_mode()]}')
    pending = read_json(state_file(repo, 'pending.json'))
    if pending:
        lines.append(f"Đang hỏi: {pending['gate']}")
    return '\n'.join(lines)


def read_state(repo):
    """REPO's parsed `.clone/status.md`, or None before it exists."""
    try:
        with open(steps_pane.status_path(repo), encoding='utf-8') as f:
            return steps_pane.parse(f.read())
    except FileNotFoundError:
        return None


def status_snapshot(repo):
    state = read_state(repo)
    return (state['now'], state['waiting']) if state else (None, None)


def brief(repo):
    """REPO's step, what it waits on, and its Claude session with the minutes since it last wrote, as card HTML."""
    now, waiting = status_snapshot(repo)
    lines = [f"▶ Đang làm: {esc(now or 'chưa có status.md')}"] + ([f'⏸ Chờ bạn: {esc(waiting)}'] if waiting else [])
    try:
        live = sessions_for(repo)
    except (BotError, subprocess.TimeoutExpired, ValueError):
        return '\n'.join(lines)
    if not live:
        lines.append(f'💤 Claude không chạy · /open {game_name(repo)} để chạy tiếp')
    else:
        path = transcript(live[0])
        lines.append(f'🤖 Claude: {esc(session_state(live[0]))}'
                     + (f', ghi lần cuối {minutes_since(path)} phút trước' if path else ''))
    return '\n'.join(lines)


# Sleep: a sleeping machine runs nothing and Telegram cannot wake it

def hold_inhibitor(what, mode, why):
    """Start a child that holds a logind inhibitor until it is released or this process dies."""
    keepalive = f'while kill -0 {os.getpid()} 2>/dev/null; do sleep 5; done'
    if shutil.which('systemd-inhibit'):
        command = ['systemd-inhibit', f'--what={what}', f'--who={WHO}', f'--why={why}', f'--mode={mode}',
                   'sh', '-c', keepalive]
    elif shutil.which('caffeinate') and mode == 'block':
        command = ['caffeinate', '-i', '-w', str(os.getpid())]
    else:
        return None
    child = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, start_new_session=True)
    try:
        time.sleep(0.3)
    except BaseException:
        release(child)
        raise
    return child if child.poll() is None else None


def release(child):
    if child is None or child.poll() is not None:
        return
    with contextlib.suppress(ProcessLookupError):
        os.killpg(child.pid, signal.SIGTERM)
    try:
        child.wait(timeout=5)
    except subprocess.TimeoutExpired:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(child.pid, signal.SIGKILL)


def slept_for(wall0, mono0, wall1, mono1):
    """Seconds the machine was asleep between two readings: the monotonic clock stops in suspend."""
    return max(0.0, (wall1 - wall0) - (mono1 - mono0))


class SleepGuard:
    """Keeps the machine awake in away mode and warns the phone before a sleep it could not block."""

    def __init__(self, cfg):
        self.cfg = cfg
        self.block = self.delay = self.monitor = None
        self.told_no_tool = False

    def sync(self, away):
        if away and self.block is None:
            self.block = hold_inhibitor('sleep:idle', 'block', 'Telegram away mode: keep running for remote decisions')
            if self.block is None and not self.told_no_tool:
                self.told_no_tool = True
                with contextlib.suppress(BotError):
                    send_text(self.cfg, card('⚠️', 'Máy có thể ngủ', 'Không chặn được chế độ ngủ trên máy này.\n'
                                                                       'Nếu máy ngủ, lệnh gửi lúc đó sẽ chờ tới khi máy thức.'))
        elif not away and self.block is not None:
            release(self.block)
            self.block = None

    def start_monitor(self):
        if shutil.which('gdbus') and shutil.which('systemd-inhibit'):
            threading.Thread(target=self._monitor, daemon=True).start()

    def _monitor(self):
        self.delay = hold_inhibitor('sleep', 'delay', 'Telegram: tell the phone before sleeping')
        self.monitor = subprocess.Popen(
            ['gdbus', 'monitor', '--system', '--dest', 'org.freedesktop.login1',
             '--object-path', '/org/freedesktop/login1'],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
            start_new_session=True)
        for line in self.monitor.stdout:
            if 'PrepareForSleep' not in line:
                continue
            if '(true,)' in line:
                if get_mode() == 'away':
                    with contextlib.suppress(BotError):
                        send_text(self.cfg, card('😴', 'Máy sắp ngủ', 'Lệnh gửi lúc này sẽ chờ tới khi máy thức.\n'
                                                                      'Telegram giữ tin tối đa 24 giờ.'))
                release(self.delay)
                self.delay = None
            elif '(false,)' in line and self.delay is None:
                self.delay = hold_inhibitor('sleep', 'delay', 'Telegram: tell the phone before sleeping')

    def close(self):
        for child in (self.block, self.delay, self.monitor):
            release(child)


# The serve daemon

def media_of(message):
    """(telegram object, kind) of the file in a message, or (None, None)."""
    for key, kind in (('video', 'video'), ('video_note', 'video'), ('animation', 'video'), ('document', 'document')):
        if message.get(key):
            return message[key], kind
    if message.get('photo'):
        return message['photo'][-1], 'photo'
    return None, None


def save_file(repo, cfg, message):
    obj, kind = media_of(message)
    mime = obj.get('mime_type') or ''
    default_ext = {'video': '.mp4', 'photo': '.jpg'}.get(kind, mimetypes.guess_extension(mime) or '')
    name = os.path.basename(obj.get('file_name') or f"tg-{obj['file_unique_id']}{default_ext}")
    ext = os.path.splitext(name)[1].lower()
    size = obj.get('file_size') or 0
    if size > DOWNLOAD_LIMIT:
        to_inbox(repo, {'kind': 'file_too_big', 'name': name, 'size': size})
        send_text(cfg, card('⚠️', f'File quá lớn: {name}', f'Nặng {size // 2**20} MB, bot chỉ tải được tối đa 20 MB.',
                            action='Gửi link (Drive, Dropbox…) hoặc cắt clip ngắn hơn.'))
        return
    if ext in APK_EXT:
        folder = 'apk'
    elif kind in ('video', 'photo') or ext in VIDEO_EXT or ext in PHOTO_EXT or mime.startswith('video/'):
        folder = 'reference'
    else:
        folder = 'data'
    target_dir = os.path.join(repo, '.clone', folder)
    os.makedirs(target_dir, exist_ok=True)
    stem, suffix = os.path.splitext(name)
    dest, n = os.path.join(target_dir, name), 1
    while os.path.exists(dest):
        dest, n = os.path.join(target_dir, f'{stem}-{n}{suffix}'), n + 1
    download(cfg, obj['file_id'], dest)
    rel = os.path.relpath(dest, repo)
    to_inbox(repo, {'kind': 'file', 'path': rel, 'caption': message.get('caption')})
    send_text(cfg, f'📎 <b>{esc(display_name(repo))}</b>: đã lưu {code(rel)}', disable_notification=True)


def on_button(cfg, query):
    parts = (query.get('data') or '').split('|')
    message_id = query.get('message', {}).get('message_id')
    settled = answer = repo = None
    for candidate in games(cfg).values():
        pending = read_json(state_file(candidate, 'pending.json'))
        if len(parts) == 3 and pending and pending['id'] == parts[1]:
            repo = candidate
            break
    if repo:
        with locked(repo):
            pending = read_json(state_file(repo, 'pending.json'))
            if pending and pending['id'] == parts[1] and parts[2].isdigit() and int(parts[2]) < len(pending['options']):
                answer = pending['options'][int(parts[2])]
                settled = record_answer(repo, answer, 'telegram')
    if settled:
        api(cfg, 'answerCallbackQuery', {'callback_query_id': query['id'], 'text': 'Đã nhận'})
        retire(cfg, message_id, settled_text(repo, settled['gate'], answer))
        ensure_session(cfg, repo)
    else:
        api(cfg, 'answerCallbackQuery', {'callback_query_id': query['id'], 'text': 'Câu này đã được quyết rồi.'})
        with contextlib.suppress(BotError):
            api(cfg, 'editMessageReplyMarkup', {'chat_id': cfg['chat'], 'message_id': message_id,
                                                'reply_markup': {'inline_keyboard': []}})


def short(text, limit=80):
    """The first clause of a status.md line, without markdown or a leading `human —`, cut to LIMIT."""
    text = re.sub(r'^human\s*[—:-]\s*', '', text.replace('`', ''), flags=re.IGNORECASE)
    text = re.split(r' → |; |, xem ', text)[0].strip()
    return text if len(text) <= limit else text[:limit - 1].rstrip() + '…'


def game_card(name, repo, current, live):
    """One game for /games, as Telegram HTML: name and one state, then its stage and what it waits on."""
    state, pending = read_state(repo), read_json(state_file(repo, 'pending.json'))
    stage = steps_pane.current_stage(state) if state else None
    status = live[0].get('status') if live else None
    prompt = status == 'waiting'  # a permission prompt holds the run until someone clicks it at the computer
    if pending:
        badge = f"❓ đang hỏi bạn ({pending['gate']})"
    elif status == 'busy':
        badge = '🟢 đang chạy'
    elif state and state['waiting'] and not prompt:
        badge = '⏸ chờ bạn'
    elif live:
        badge = f"🟡 Claude {SESSION_LABEL.get(status, status or '?')}"
    elif not state:
        badge = '⚪ chưa bắt đầu'
    elif not stage:
        badge = '✅ xong'
    else:
        badge = f'💤 đã dừng · /open {name}'
    lines = [f"{'▶ ' if repo == current else ''}<b>{html.escape(name)}</b>  {html.escape(badge)}"]
    if stage:
        label = next(s['label'] for s in state['stages'] if s['id'] == stage)
        lines.append(f'{stage} · {html.escape(label)}')
    if prompt and not pending:
        lines.append(f'Ở máy: {html.escape(attach_command(session_ref(live[0])))}')
    elif state and state['waiting'] and not pending:
        lines.append(f"Chờ: {html.escape(short(state['waiting']))}")
    return '\n'.join(lines)


def games_text(cfg):
    found, current, skip = games(cfg), get_current(cfg), hidden()
    if not found:
        return html.escape(f"Chưa có game nào trong {cfg['games_dir']}. Dùng /new <ý tưởng> để bắt đầu.")
    shown = {name: repo for name, repo in found.items() if os.path.realpath(repo) not in skip}
    try:
        listing = agents() if shown else []
    except (BotError, subprocess.TimeoutExpired, ValueError):
        listing = []
    cards = [game_card(name, repo, current, sessions_for(repo, listing=listing)) for name, repo in shown.items()]
    if len(shown) < len(found):
        cards.append(f"Đang ẩn: {html.escape(', '.join(name for name in found if name not in shown))}"
                     ' · /unhide &lt;game&gt; để hiện lại')
    return '\n\n'.join(cards + ['Chi tiết: /status &lt;game&gt; · Chọn game: /use &lt;game&gt;'])


def on_session_command(cfg, command, rest):
    if command == 'games':
        send_text(cfg, games_text(cfg))
        return
    if command == 'new':
        if not os.path.isdir(cfg['games_dir']):
            send_text(cfg, card('⚠️', 'Không thấy thư mục game', f"{code(cfg['games_dir'])} (GAMES_DIR) không tồn tại."))
            return
        slug = '-'.join(re.findall(r'[a-z0-9]+', rest.lower())[:3]) or 'new-game'
        ref = launch(cfg, cfg['games_dir'], f'new-{slug}',
                     NEW_PROMPT.format(idea=rest, games_dir=cfg['games_dir']))
        send_text(cfg, card('🆕', 'Game mới', f'Đã mở phiên Claude (phiên {code(ref)}). Agent sẽ hỏi tiếp ở đây.',
                            action=f'Ở máy: {code(attach_command(ref))}'))
        return
    repo = resolve_game(cfg, rest or None)
    if not repo:
        send_text(cfg, card('❔', f"Không rõ game{': ' + rest if rest else ''}",
                            action='Xem /games, rồi chọn bằng /use &lt;game&gt;'))
        return
    name, shown = game_name(repo), esc(display_name(repo))
    if command == 'use':
        set_current(repo)
        send_text(cfg, f'✓ Đang nói chuyện với <b>{shown}</b>.')
    elif command == 'status':
        send_pre(cfg, status_text(repo))
    elif command == 'hide':
        set_hidden(repo, True)
        send_text(cfg, f'🙈 Đã ẩn <b>{shown}</b> khỏi /games.\nHiện lại: /unhide {name}')
    elif command == 'unhide':
        set_hidden(repo, False)
        send_text(cfg, f'✓ <b>{shown}</b> hiện lại trong /games.')
    elif command == 'open':
        set_current(repo)
        set_hidden(repo, False)
        if live := sessions_for(repo):
            send_text(cfg, card('▶', display_name(repo), f'Đã có phiên Claude đang chạy ({esc(session_state(live[0]))}).',
                                action=f'Xem nó làm gì: /log {name}'))
            return
        ref = resume(cfg, repo)
        send_text(cfg, card('▶', display_name(repo), f'Đã mở phiên Claude (phiên {code(ref)}).',
                            action=f'Ở máy: {code(attach_command(ref))}'))
    elif command == 'log':
        found = sessions_for(repo) or sessions_for(repo, include_done=True)
        if not found:
            send_text(cfg, f'<b>{shown}</b>: chưa có phiên Claude nào.')
            return
        activity = recent_activity(found[0])
        if activity is None:
            screen = ANSI.sub('', claude('logs', session_ref(found[0])))
            activity = re.sub(r'\s+', ' ', screen).strip()[-3000:] or '(trống)'
        send_text(cfg, card('🧾', f'{display_name(repo)} · {session_state(found[0])}', esc(activity[-3500:])))
    elif command == 'stop':
        background = [s for s in sessions_for(repo) if s.get('kind') != 'interactive']
        if not background:
            send_text(cfg, card('⏹', display_name(repo), 'Không có phiên chạy nền nào để dừng.\n'
                                                         'Phiên trên máy tính thì dừng ở máy.'))
            return
        claude('stop', session_ref(background[0]))
        write_text(state_file(repo, 'stopped'), background[0].get('sessionId') or '')
        send_text(cfg, card('⏹', display_name(repo), 'Đã dừng phiên Claude.', action=f'Mở lại: /open {name}'))


def on_command(cfg, text):
    head, _, rest = text.partition(' ')
    command, rest = head[1:].split('@')[0].lower(), rest.strip()
    if command in NEEDS_ARGS and not rest:
        send_text(cfg, f'Thiếu nội dung: /{command} &lt;…&gt;')
    elif command == 'away':
        set_mode(cfg, 'away')
    elif command == 'back':
        set_mode(cfg, 'here')
    elif command in ('games', 'use', 'status', 'open', 'new', 'log', 'stop', 'hide', 'unhide'):
        try:
            on_session_command(cfg, command, rest)
        except (BotError, subprocess.TimeoutExpired, ValueError) as error:
            send_text(cfg, card('⚠️', f'/{command} không chạy được', esc(error)))
    elif command in INBOX_COMMANDS:
        repo = resolve_game(cfg, None)
        if not repo:
            send_text(cfg, NO_GAME)
            return
        to_inbox(repo, {'kind': 'command', 'command': command, 'args': rest})
        send_text(cfg, card('📥', display_name(repo), esc(f'Đã ghi /{command} {rest}'.rstrip() + '.'),
                            'Agent đọc khi xong bước đang làm.'), disable_notification=True)
    else:
        send_text(cfg, HELP)


def on_text(cfg, text):
    current = get_current(cfg)
    asked = [repo for repo in games(cfg).values()
             if (read_json(state_file(repo, 'pending.json')) or {}).get('message_id')]
    target = current if current in asked else (asked[0] if len(asked) == 1 else None)
    settled = held = None
    fields = {}
    if target:
        with locked(target):
            pending = read_json(state_file(target, 'pending.json'))
            if pending and pending.get('message_id'):
                if pending['gate'] != APPLE_GATE:
                    settled = record_answer(target, text, 'telegram')
                elif reply := apple_answer(text):
                    fields = reply[1]
                    settled = record_answer(target, reply[0], 'telegram', **fields)
                else:
                    held = pending
    if settled:
        retire(cfg, settled['message_id'], settled_text(target, settled['gate'], text))
        ack = (f"✓ Đã nhận: build <b>{esc(fields['build'])}</b>, Apple ID <b>{esc(fields['apple_id'])}</b>."
               if fields else '✓ Đã nhận câu trả lời.')
        send_text(cfg, ack, disable_notification=True)
        ensure_session(cfg, target)
        return
    if held:
        # Rule 13: only the deferral or both values settle it; the agent still reads the text, as a note.
        to_inbox(target, {'kind': 'text', 'text': text,
                          'held': f'{APPLE_GATE}: no build number and Apple ID, so not an answer'})
        send_text(cfg, card('📥', f'{display_name(target)} · {gate_label(APPLE_GATE)}',
                            'Chưa tính là báo xong: câu hỏi vẫn mở.\nTin của bạn đã chuyển cho agent như một ghi chú.',
                            action=APPLE_HINT), disable_notification=True)
        return
    if text.lower().strip(' ?!.') in HELP_WORDS:
        send_text(cfg, HELP)
        return
    repo = resolve_game(cfg, None)
    if not repo:
        send_text(cfg, NO_GAME)
        return
    to_inbox(repo, {'kind': 'text', 'text': text})
    # A session stuck inside one step never reaches the boundary where it reads this: show the human where it is.
    send_text(cfg, card('📥', display_name(repo), 'Đã ghi cho agent. Agent đọc khi xong bước đang làm.', brief(repo)),
              disable_notification=True)


def handle(cfg, update):
    if query := update.get('callback_query'):
        chat = query.get('message', {}).get('chat', {}).get('id')
        if str(chat) == cfg['chat']:
            on_button(cfg, query)
        return
    message = update.get('message')
    if not message or str(message.get('chat', {}).get('id')) != cfg['chat']:
        warn(f"ignored update {update.get('update_id')} from a chat that is not the allowlisted one")
        return
    text = (message.get('text') or '').strip()
    if media_of(message)[0]:
        repo = resolve_game(cfg, None)
        if repo:
            save_file(repo, cfg, message)
        else:
            send_text(cfg, card('❔', 'Chưa chọn game để lưu file', action='Xem /games, rồi chọn bằng /use &lt;game&gt;'))
    elif text.startswith('/'):
        on_command(cfg, text)
    elif text:
        on_text(cfg, text)


def unread_answers(repo):
    """Decisions recorded for REPO that no session has read yet (`ask` and `answers` remove them)."""
    return [name for name in os.listdir(state_dir(repo)) if name.startswith('answer-') and name.endswith('.json')]


def check_ended(cfg, warned, repo, session):
    """Warn once when REPO's newest session, not busy, last wrote ENDED_MINUTES to ENDED_HOURS ago with stages
    left and either nothing in `Waiting on:` or an answer of yours unread: it stopped without asking anything
    (a sibling skill's final report taken for the end of the run) or died before reading your answer (an
    expired login), and nothing restarts it. A session `/stop`ped from the phone is left alone."""
    path = transcript(session)
    if not path or read_text(state_file(repo, 'stopped')) == session.get('sessionId'):
        return
    mtime, key = os.path.getmtime(path), ('ended', session.get('sessionId'))
    if not ENDED_MINUTES * 60 <= time.time() - mtime <= ENDED_HOURS * 3600 or warned.get(key) == mtime:
        return
    state, unread = read_state(repo), unread_answers(repo)
    if not state or (state['waiting'] and not unread) or all(stage['done'] for stage in state['stages']):
        return
    warned[key] = mtime
    name, reply = game_name(repo), last_reply(path)
    with contextlib.suppress(BotError):
        send_text(cfg, card('⚠️', f'{display_name(repo)} · phiên Claude đã dừng',
                            f'Dừng lúc {time.strftime("%H:%M", time.localtime(mtime))}, '
                            + ('trước khi đọc câu trả lời của bạn.' if unread else 'mà không hỏi gì.'),
                            f"▶ Đang làm: {esc(state['now'] or '?')}" + (f'\n💬 Câu cuối: {esc(reply)}' if reply else ''),
                            action=f'Chạy tiếp: /open {name} · Xem: /log {name}'))


def check_stalls(cfg, warned):
    """Warn the phone once per stall while no question is pending: a busy session that wrote nothing for
    STALL_MINUTES is most likely held by a prompt only the computer can answer, and a game with no busy
    session may have stopped without asking (`check_ended`). WARNED: (kind, sessionId) → reported mtime."""
    try:
        listing = agents(include_done=True)
    except (BotError, subprocess.TimeoutExpired, ValueError) as error:
        warn(str(error))
        return
    for repo in games(cfg).values():
        if read_json(state_file(repo, 'pending.json')):
            continue
        mine = sessions_for(repo, listing=listing)
        busy = [session for session in mine if session.get('status') == 'busy']
        if mine and not busy:
            check_ended(cfg, warned, repo, mine[0])
        for session in busy:
            path = transcript(session)
            if not path:
                continue
            mtime, key = os.path.getmtime(path), ('stall', session.get('sessionId'))
            if time.time() - mtime < STALL_MINUTES * 60 or warned.get(key) == mtime:
                continue
            warned[key] = mtime
            name, tool = game_name(repo), last_tool(path)
            with contextlib.suppress(BotError):
                send_text(cfg, card('⚠️', f'{display_name(repo)} · phiên Claude đứng im',
                                    f'Không ghi gì {minutes_since(path)} phút.'
                                    + (f'\nLệnh cuối: {esc(tool)}' if tool else '')
                                    + '\nCó thể đang chờ một xác nhận chỉ bấm được trên máy.',
                                    f'Xem: /log {name}\nMở lại: /stop {name} rồi /open {name}',
                                    action=f'Ở máy: {code(attach_command(session_ref(session)))}'))


def cmd_serve():
    cfg = require_config()
    if pid := serve_pid():
        print(f'serve is already running (pid {pid})')
        return 0
    pid_path, offset_path = global_file('serve.pid'), global_file('offset')
    write_text(pid_path, str(os.getpid()))
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    guard = SleepGuard(cfg)
    guard.start_monitor()
    try:
        offset = int(read_text(offset_path) or '')
    except ValueError:
        offset = None
    seen = {repo: status_snapshot(repo) for repo in games(cfg).values()}
    wall, mono = time.time(), time.monotonic()
    woke, failures = 0.0, 0
    stall_checked, stalled = mono, {}
    print(f'serving Telegram for the games in {cfg["games_dir"]} and registered repos (pid {os.getpid()})', flush=True)
    try:
        while True:
            away = get_mode() == 'away'
            guard.sync(away)
            now_wall, now_mono = time.time(), time.monotonic()
            gap = slept_for(wall, mono, now_wall, now_mono)
            wall, mono = now_wall, now_mono
            if gap >= SLEEP_GAP:
                woke = gap
                stall_checked = now_mono  # sessions were frozen too: give them time to write again
            if away and now_mono - stall_checked >= STALL_CHECK_SECONDS:
                stall_checked = now_mono
                check_stalls(cfg, stalled)
            for repo in games(cfg).values():
                snapshot = status_snapshot(repo)
                if snapshot != seen.get(repo):
                    first = repo not in seen
                    seen[repo] = snapshot
                    if away and not first and any(snapshot):
                        now, waiting = snapshot
                        with contextlib.suppress(BotError):
                            send_text(cfg, card('▶', display_name(repo), esc(now or ''),
                                                f'⏸ Chờ bạn: {esc(waiting)}' if waiting else ''))
            params = {'timeout': POLL_SECONDS, 'allowed_updates': ['message', 'callback_query']}
            if offset is not None:
                params['offset'] = offset
            try:
                updates = api(cfg, 'getUpdates', params, timeout=POLL_SECONDS + 20)
                failures = 0
            except BotError as error:
                failures += 1
                warn(str(error) + (' (another program polls this bot: give the pipeline its own bot token)'
                                   if 'Conflict' in str(error) else ''))
                time.sleep(min(60, 2 ** failures))
                continue
            if woke:
                if away:
                    with contextlib.suppress(BotError):
                        send_text(cfg, card('☀️', 'Máy vừa thức', f'Ngủ {round(woke / 60)} phút, '
                                                                    f'đang xử lý {len(updates)} tin chờ.'))
                woke = 0.0
            for update in updates:
                offset = update['update_id'] + 1
                try:
                    handle(cfg, update)
                except BotError as error:
                    warn(str(error))
                write_text(offset_path, str(offset))
    except KeyboardInterrupt:
        pass
    finally:
        guard.close()
        if serve_pid() == os.getpid():
            os.remove(pid_path)
    return 0


# The other subcommands

def cmd_ask(repo, gate, question, options):
    if gate == APPLE_GATE and options != [APPLE_LATER]:
        warn(f'{APPLE_GATE} takes one button, --option "{APPLE_LATER}": the human types the VALID build number and '
             "the app's Apple ID instead (SKILL.md rule 13)")
        return 64
    cfg = require_config()
    if not serve_pid():
        warn('serve is not running: install the service (`install-service`) or start `watch REPO` in the background')
        return 69
    register(repo)
    for name in sorted(os.listdir(state_dir(repo))):
        answer = read_json(state_file(repo, name)) if name.startswith('answer-') else None
        if answer and (answer['gate'], answer['question']) == (gate, question):
            os.remove(state_file(repo, name))
            print(json.dumps({'event': 'answer', **answer}, ensure_ascii=False))
            return 0
    with locked(repo):
        path = state_file(repo, 'pending.json')
        pending = read_json(path)
        if not pending or (pending['gate'], pending['question'], pending['options']) != (gate, question, options):
            if pending and pending.get('message_id'):
                retire(cfg, pending['message_id'], '↪ Câu hỏi này đã được thay bằng câu mới.')
            pending = {'id': uuid.uuid4().hex[:8], 'gate': gate, 'question': question, 'options': options,
                       'asked': now_iso()}
            write_json(path, pending)
        if get_mode() == 'away':
            try:
                deliver_pending(repo, cfg)
            except BotError as error:
                warn(str(error))
    answer_path = state_file(repo, f"answer-{pending['id']}.json")
    baseline = len(inbox_lines(repo))
    while True:
        if answer := read_json(answer_path):
            os.remove(answer_path)
            print(json.dumps({'event': 'answer', **answer}, ensure_ascii=False))
            return 0
        if (count := len(inbox_lines(repo))) > baseline:
            print(json.dumps({'event': 'inbox', 'id': pending['id'], 'gate': gate,
                              'unread': count - inbox_cursor(repo)}, ensure_ascii=False))
            return 0
        time.sleep(1)


def cmd_answers(repo):
    for name in sorted(os.listdir(state_dir(repo))):
        if name.startswith('answer-') and name.endswith('.json'):
            if answer := read_json(state_file(repo, name)):
                print(json.dumps({'event': 'answer', **answer}, ensure_ascii=False))
            os.remove(state_file(repo, name))
    return 0


def cmd_close(repo, answer):
    cfg = require_config()
    with locked(repo):
        pending = read_json(state_file(repo, 'pending.json'))
        fields = {}
        if pending and pending['gate'] == APPLE_GATE:
            if not (reply := apple_answer(answer)):
                warn(f'{APPLE_GATE} settles only on "{APPLE_LATER}" or the build number and the Apple ID, not '
                     f'{answer!r}: ask the human for both (SKILL.md rule 13)')
                return 64
            answer, fields = reply
        settled = record_answer(repo, answer, 'computer', **fields)
    if settled and settled.get('message_id'):
        retire(cfg, settled['message_id'], settled_text(repo, settled['gate'], answer, by='computer'))
    set_mode(cfg, 'here')
    print(f"closed {settled['gate']}" if settled else 'no pending question')
    return 0


def cmd_mode(mode):
    cfg = require_config()
    if mode == 'away' and not serve_pid():
        warn('serve is not running: the phone gets the question but nothing keeps the machine awake or reads replies')
    set_mode(cfg, mode)
    print(f'mode {mode}')
    return 0


def cmd_send(repo, text, files):
    """TEXT as a card, then each (path, caption) of FILES in order, one message each; a failure skips only itself."""
    cfg = require_config()
    sent, failed = [], []
    if text:
        try:
            send_text(cfg, card('💬', display_name(repo), markup(text, repo)))
            sent.append('text')
        except BotError as error:
            warn(str(error))
            failed.append('text')
    for path, caption in files:
        try:
            send_file(cfg, path, caption)
            sent.append(os.path.basename(path))
        except BotError as error:
            warn(str(error))
            failed.append(os.path.basename(path))
    print('sent: ' + (', '.join(sent) or 'nothing') + (f'; not sent: {", ".join(failed)}' if failed else ''))
    return 70 if failed else 0


def cmd_inbox(repo):
    lines, cursor = inbox_lines(repo), inbox_cursor(repo)
    for line in lines[cursor:]:
        print(line)
    write_text(state_file(repo, 'inbox.cursor'), str(len(lines)))
    return 0


def guard_worktree(event):
    """PreToolUse hook: refuse `EnterWorktree` with `path:` (SKILL.md rule 5). From another repo it raises a
    permission prompt only the computer can answer, and the background session waits on it. Exit 2 hands
    the reason to the agent instead."""
    if event.get('tool_name') != 'EnterWorktree' or not (event.get('tool_input') or {}).get('path'):
        return 0
    print('game-clone-pipeline rule 5: do not re-enter a worktree with `path:`. From another repo that raises '
          'a permission prompt only the computer can answer, and this session would wait on it. Go to the game '
          'repo root (cd, then check pwd), merge the worktree branch there with git ("Closing a branch"), and '
          'start any further work in a new worktree with `name:`.', file=sys.stderr)
    return 2


def cmd_hook():
    """Hook of phone-started sessions: a permission prompt nobody can click goes to the phone (Notification),
    and `EnterWorktree` with `path:` is refused before it can raise one (PreToolUse)."""
    try:
        event = json.load(sys.stdin)
    except ValueError:
        return 0
    if event.get('hook_event_name') == 'PreToolUse':
        return guard_worktree(event)
    cfg = load_config()
    message = event.get('message') or ''
    if not (cfg['token'] and cfg['chat']) or event.get('notification_type', '') != 'permission_prompt' \
            and 'permission' not in message.lower():
        return 0
    # The session's folder is no handle for it: a /new session is named after the idea, and it may sit in a
    # worktree or in the site repo. Attach by session id, and name the game it works on.
    cwd, sid = event.get('cwd') or os.getcwd(), event.get('session_id') or os.environ.get('CLAUDE_CODE_SESSION_ID')
    repo = session_repo(cfg, sid, cwd) or cwd
    with contextlib.suppress(BotError):
        send_text(cfg, card('⚠️', f'{display_name(repo)} · cần cấp quyền ở máy',
                            esc(message or 'Claude đang chờ cấp quyền.'),
                            'Phiên đứng chờ tới khi có người cho phép; từ điện thoại không bấm được.',
                            action=f'Ở máy: {code(attach_command(sid[:8] if sid else game_name(repo)))}'))
    return 0


def systemctl(*args):
    done = subprocess.run(['systemctl', '--user', *args], capture_output=True, text=True)
    if done.returncode != 0:
        warn(f'systemctl --user {" ".join(args)}: {(done.stderr or done.stdout).strip()}')
        sys.exit(70)


def cmd_install_service():
    require_config()
    local_bin = os.path.expanduser('~/.local/bin')
    path = os.environ.get('PATH', '/usr/local/bin:/usr/bin:/bin')
    if local_bin not in path.split(':'):
        path = f'{local_bin}:{path}'
    env = {'PATH': path, 'HOME': os.path.expanduser('~')}
    for key in ('CLAUDE_CONFIG_DIR', 'XDG_CONFIG_HOME', 'XDG_STATE_HOME'):
        if os.environ.get(key):
            env[key] = os.environ[key]
    unit = '\n'.join([
        '[Unit]',
        'Description=game-clone-pipeline Telegram remote',
        'After=network-online.target',
        'Wants=network-online.target',
        '',
        '[Service]',
        'Type=simple',
        f'ExecStart={shlex.join([sys.executable, SCRIPT, "serve"])}',
        *(f'Environment="{key}={value}"' for key, value in env.items()),
        'Restart=always',
        'RestartSec=15',
        '# Claude sessions started from the phone must outlive a restart of this service.',
        'KillMode=process',
        '',
        '[Install]',
        'WantedBy=default.target',
        '',
    ])
    os.makedirs(os.path.dirname(UNIT), exist_ok=True)
    write_text(UNIT, unit)
    systemctl('daemon-reload')
    systemctl('enable', '--now', UNIT_NAME)
    print(f'installed and started {UNIT}')
    return 0


def cmd_uninstall_service():
    if os.path.exists(UNIT):
        systemctl('disable', '--now', UNIT_NAME)
        os.remove(UNIT)
        systemctl('daemon-reload')
    print(f'removed {UNIT}')
    return 0


def cmd_setup():
    cfg = load_config()
    if not cfg['token'] and sys.stdin.isatty():
        cfg['token'] = getpass.getpass('Bot token from @BotFather (hidden): ').strip()
    if not cfg['token']:
        warn('no token: run this in a terminal, or set TELEGRAM_BOT_TOKEN')
        return 64
    try:
        bot = api(cfg, 'getMe')
        print(f"Bot @{bot['username']} works. On the phone open https://t.me/{bot['username']} "
              'and press Start (or send /start) within 5 minutes.', flush=True)
        chat, offset, deadline = None, None, time.time() + 300
        while chat is None and time.time() < deadline:
            params = {'timeout': 25} if offset is None else {'timeout': 25, 'offset': offset}
            for update in api(cfg, 'getUpdates', params, timeout=45):
                offset = update['update_id'] + 1
                message = update.get('message') or {}
                if (message.get('text') or '').startswith('/start') and message.get('chat', {}).get('type') == 'private':
                    chat = str(message['chat']['id'])
        if chat is None:
            warn('no /start arrived in 5 minutes')
            return 69
        api(cfg, 'getUpdates', {'offset': offset, 'timeout': 0})
        os.makedirs(CONFIG_DIR, mode=0o700, exist_ok=True)
        fd = os.open(CONFIG, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(f"TELEGRAM_BOT_TOKEN={cfg['token']}\nTELEGRAM_CHAT_ID={chat}\n"
                    f"GAMES_DIR={cfg['games_dir']}\n")
        os.chmod(CONFIG, 0o600)
        cfg['chat'] = chat
        send_text(cfg, card('✅', 'Đã kết nối với game-clone-pipeline',
                            'Ở máy thì quyết trong chat; ra ngoài thì gõ /away.') + '\n\n' + HELP)
    except BotError as error:
        warn(str(error) + (' (another program polls this bot: create a separate bot for the pipeline)'
                           if 'Conflict' in str(error) else ''))
        return 70
    print(f'Paired with chat {chat}; config written to {CONFIG} (chmod 600). Games folder: {cfg["games_dir"]} '
          '(edit GAMES_DIR there to change it).\n'
          f'Next, so the phone works even with Claude closed: python3 {SCRIPT} install-service')
    return 0


def main(argv):
    parser = Parser(prog='telegram_bridge.py', description=__doc__.split('\n\n')[0])
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('setup', 'serve', 'hook', 'install-service', 'uninstall-service'):
        sub.add_parser(name)
    for name in ('watch', 'register', 'inbox', 'answers'):
        sub.add_parser(name).add_argument('repo')
    ask = sub.add_parser('ask')
    ask.add_argument('repo')
    ask.add_argument('gate')
    ask.add_argument('question')
    ask.add_argument('--option', action='append', default=[])
    close = sub.add_parser('close')
    close.add_argument('repo')
    close.add_argument('--answered-here', required=True, metavar='ANSWER')
    sub.add_parser('mode').add_argument('mode', choices=sorted(MODE_LABEL))
    send = sub.add_parser('send')
    send.add_argument('repo')
    send.add_argument('text', nargs='?')
    send.add_argument('--file', dest='files', action=Attach, default=[], metavar='PATH',
                      help='a file to send; repeat for more, they go in order, one message each')
    send.add_argument('--caption', dest='files', action=Attach, metavar='TEXT',
                      help='caption of the --file right before it')
    args = parser.parse_args(argv[1:])

    simple = {'setup': cmd_setup, 'serve': cmd_serve, 'hook': cmd_hook,
              'install-service': cmd_install_service, 'uninstall-service': cmd_uninstall_service}
    if args.command in simple:
        return simple[args.command]()
    if args.command == 'mode':
        return cmd_mode(args.mode)
    repo = os.path.abspath(args.repo)
    if not os.path.isdir(repo):
        warn(f'no such directory: {repo}')
        return 66
    if args.command != 'watch':
        link_session(repo)
    if args.command == 'watch':
        register(repo)
        return cmd_serve()
    if args.command == 'register':
        register(repo)
        print(f'registered {repo}')
        return 0
    if args.command == 'ask':
        return cmd_ask(repo, args.gate, args.question, args.option)
    if args.command == 'close':
        return cmd_close(repo, args.answered_here)
    if args.command == 'answers':
        return cmd_answers(repo)
    if args.command == 'send':
        if not (args.text or args.files):
            parser.error('send needs TEXT or --file')
        missing = [path for path, _ in args.files if not os.path.isfile(path)]
        if missing:
            warn('no such file: ' + ', '.join(missing))
            return 66
        return cmd_send(repo, args.text, args.files)
    return cmd_inbox(repo)


if __name__ == '__main__':
    sys.exit(main(sys.argv))
