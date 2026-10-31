#!/usr/bin/env python3
"""Keep a game's name the same everywhere: folder, GitHub repo, site repo, Pages listing, app, docs.

  scripts/name_sync.py names "Moss Lantern"                    # every form the name takes
  scripts/name_sync.py rename PATH --old OLD --new NEW         # dry run: every hit in PATH's files
  scripts/name_sync.py rename PATH --old OLD --new NEW --apply # rewrite them (and paths that hold it)
  scripts/name_sync.py check REPO [--old OLD]... [--online]    # PASS/FAIL per place; exit 1 on a FAIL

A name has seven forms: Title (`Moss Lantern`), kebab (`moss-lantern`: folder, repo, URLs), snake
(`moss_lantern`: Dart package, Android ids), compact (`mosslantern`: iOS bundle id suffix), camel,
Pascal and UPPER. `rename` rewrites each form of OLD into the same form of NEW in a checkout's
git-tracked and untracked-unignored text files, skipping `.clone/` (the gate log keeps the history),
`.reports/` (audit snapshots), CHANGELOG files and binaries. When OLD is one word several forms are the same string; the context
picks the form (`package:` → snake, a reverse-DNS id → compact, or snake under android/, a URL or
`-site` → kebab, before a capital → camel). `--keep-ids` leaves bundle ids, product ids and Android
ids alone: once App Store Connect has them they never change.

`check` reads the name from REPO/.clone/status.md (`# Clone status: <Game> (clone of …)`). Before G1
is approved it only checks that the folder and GitHub repo agree on the working slug. From G1 on it
checks every place below that exists yet: folder, origin, status.md Repo/Landing, DESIGN.md, pubspec,
iOS display name and bundle id, Android label and applicationId, web title, site repo, stale Pages
URLs, the root Pages repo's robots.txt and llms.txt, linked worktrees, the Telegram registry and, with
--old, every leftover of the old name. --online adds `gh repo view` and HTTP 200 on the Pages URLs.
Standard library only (plus `git`, and `gh` for --online).
"""
import argparse
import fnmatch
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request

FORMS = ('title', 'kebab', 'snake', 'compact', 'camel', 'pascal', 'upper')
CODE_EXT = {'.dart', '.kt', '.kts', '.gradle', '.swift', '.m', '.h', '.yaml', '.yml', '.json', '.plist',
            '.pbxproj', '.xcconfig', '.xcscheme', '.sh', '.py', '.arb', '.properties', '.cmake'}
SKIP_ALWAYS = ('.clone/*', '.reports/*', '.claude/*', 'CHANGELOG*', '*/CHANGELOG*')  # history, audits, worktrees
MAX_BYTES = 2_000_000
CONFIG_HOME = os.environ.get('XDG_CONFIG_HOME') or os.path.expanduser('~/.config')
TELEGRAM_DIR = os.path.join(CONFIG_HOME, 'game-clone-pipeline')
APPROVED = re.compile(r'^(approv|duyệt|chấp nhận|ok\b|yes\b|đồng ý)', re.IGNORECASE)


# Forms of a name

def words_of(name):
    """'Moss Lantern', 'moss-lantern', 'moss_lantern' or 'MossLantern' → ['Moss', 'Lantern']."""
    parts = re.split(r'[\s_\-]+', name.strip())
    out = []
    for part in parts:
        out += re.findall(r'[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+|\d+', part) or [part]
    return [w for w in out if w]


def forms(name):
    words = words_of(name)
    if not words:
        raise SystemExit(f'name_sync: no letters in name {name!r}')
    lower = [w.lower() for w in words]
    has_case = any(c.isupper() for c in name) and ' ' in name.strip()
    title = name.strip() if has_case else ' '.join(w[:1].upper() + w[1:] for w in lower)
    return {
        'title': title,
        'kebab': '-'.join(lower),
        'snake': '_'.join(lower),
        'compact': ''.join(lower),
        'camel': lower[0] + ''.join(w[:1].upper() + w[1:] for w in lower[1:]),
        'pascal': ''.join(w[:1].upper() + w[1:] for w in lower),
        'upper': ' '.join(w.upper() for w in lower),
    }


def form_pattern(text):
    """Regex for one form with word edges that still let it sit inside an identifier (`mossLanternTheme`,
    `MossLanternApp`, `moss_lantern_test`), but not inside a longer word (`mosslanterns`)."""
    body = re.escape(text)
    if text[:1].isupper():
        before = r'(?<![A-Z0-9])' if not text.isupper() else r'(?<![A-Za-z0-9])'
    else:
        before = r'(?<![A-Za-z0-9])'
    after = r'(?![A-Za-z0-9])' if text.isupper() else r'(?![a-z0-9])'
    return before + body + after


class Mapper:
    """Maps every form of OLD to the same form of NEW, picking the form from context when OLD's forms
    coincide (a one-word OLD is the same string as kebab, snake, compact and camel)."""

    def __init__(self, old, new, keep_ids=False):
        self.old, self.new, self.keep_ids = forms(old), forms(new), keep_ids
        by_text = {}
        for form in FORMS:
            by_text.setdefault(self.old[form], []).append(form)
        self.by_text = by_text
        alternation = '|'.join(form_pattern(t) for t in sorted(by_text, key=len, reverse=True))
        self.regex = re.compile(alternation)

    def pick(self, candidates, text, start, end, relpath):
        if len(candidates) == 1:
            return candidates[0]
        before, after = text[max(0, start - 80):start], text[end:end + 40]
        ext = os.path.splitext(relpath)[1].lower()
        android = relpath.startswith('android/') or ext in {'.kt', '.kts', '.gradle'}
        ios = relpath.startswith(('ios/', 'macos/')) or ext in {'.pbxproj', '.plist', '.xcconfig', '.swift'}
        lowered = [c for c in candidates if c not in ('title', 'pascal', 'upper')]
        capital = [c for c in candidates if c in ('title', 'pascal')]
        if capital and not lowered:
            code_name = ext in CODE_EXT and (re.match(r'\s*(\(|\.\w|<(?!/))', after) or re.search(
                r'\b(class|extends|with|implements|new|enum|mixin|const)\s+$', before))
            if re.match(r'[A-Z]', after) or re.search(r'[a-z0-9]$', before) or code_name:
                return 'pascal' if 'pascal' in capital else capital[0]
            return 'title' if 'title' in capital else capital[0]
        if re.match(r'[A-Z]', after) and 'camel' in candidates:
            return 'camel'
        if before.endswith('package:') or (relpath.endswith('pubspec.yaml') and re.search(r'(^|\n)name:\s*$', before)):
            return 'snake'
        if re.search(r'[A-Za-z0-9_]+\.[A-Za-z0-9_]+\.$', before):  # reverse-DNS id: com.org.<name>
            if android and 'snake' in candidates:
                return 'snake'
            return 'compact' if 'compact' in candidates else candidates[0]
        if after.startswith('-site') or re.search(r'(github\.(com|io)/[^\s/]*/?|://[^\s]*/)$', before):
            return 'kebab'
        if ios and 'compact' in candidates and 'PRODUCT_BUNDLE_IDENTIFIER' in before:
            return 'compact'
        if (ext in CODE_EXT or android) and 'snake' in candidates:
            return 'snake'
        return 'kebab' if 'kebab' in candidates else candidates[0]

    def is_id(self, text, start, end):
        """True inside a reverse-DNS id such as com.org.mosslantern or com.org.mosslantern.full_game."""
        before = text[max(0, start - 80):start]
        return bool(re.search(r'[A-Za-z0-9_]+\.[A-Za-z0-9_]+\.$', before)) or bool(
            re.search(r'(PRODUCT_BUNDLE_IDENTIFIER|applicationId|namespace|^package)\s*[=:]?\s*["\']?[\w.]*$',
                      before, re.MULTILINE))

    def sub(self, text, relpath):
        """(new text, [(line number, old, new)])."""
        changes = []

        def replace(m):
            old = m.group(0)
            if self.keep_ids and self.is_id(text, m.start(), m.end()):
                return old
            form = self.pick(self.by_text[old], text, m.start(), m.end(), relpath)
            new = self.new[form]
            if new != old:
                changes.append((text.count('\n', 0, m.start()) + 1, old, new))
            return new

        return self.regex.sub(replace, text), changes


# Files

def git(repo, *args, check=True):
    proc = subprocess.run(['git', '-C', repo, *args], capture_output=True, text=True)
    if check and proc.returncode != 0:
        raise SystemExit(f'name_sync: git {" ".join(args)} in {repo} failed: {proc.stderr.strip()}')
    return proc


def listed_files(repo, skips=()):
    out = git(repo, 'ls-files', '-z', '--cached', '--others', '--exclude-standard').stdout
    seen = []
    for rel in sorted(set(filter(None, out.split('\0')))):
        if any(fnmatch.fnmatch(rel, pat) for pat in SKIP_ALWAYS + tuple(skips)):
            continue
        if os.path.isfile(os.path.join(repo, rel)):
            seen.append(rel)
    return seen


def read_text_file(path):
    try:
        if os.path.getsize(path) > MAX_BYTES:
            return None
        with open(path, 'rb') as f:
            raw = f.read()
    except OSError:
        return None
    if b'\0' in raw[:8192]:
        return None
    try:
        return raw.decode('utf-8')
    except UnicodeDecodeError:
        return None


def cmd_rename(args):
    repo = os.path.abspath(args.path)
    mapper = Mapper(args.old, args.new, args.keep_ids)
    files = listed_files(repo, args.skip)
    edits, moves, total = [], [], 0
    for rel in files:
        text = read_text_file(os.path.join(repo, rel))
        if text is None:
            continue
        new_text, changes = mapper.sub(text, rel)
        if changes:
            edits.append((rel, new_text, changes))
            total += len(changes)
        # The Kotlin/Java source folder spells the Android package: it moves with the ids, or not at all.
        if args.keep_ids and rel.startswith('android/') and ('/kotlin/' in rel or '/java/' in rel):
            continue
        new_rel = '/'.join(mapper.sub(part, rel)[0] for part in rel.split('/'))
        if new_rel != rel:
            moves.append((rel, new_rel))
    for rel, _, changes in edits:
        for line, old, new in changes[:args.show]:
            print(f'{rel}:{line}: {old} → {new}')
        if len(changes) > args.show:
            print(f'{rel}: … {len(changes) - args.show} more')
    for rel, new_rel in moves:
        print(f'move {rel} → {new_rel}')
    clash = [new for _, new in moves if os.path.exists(os.path.join(repo, new))]
    if clash:
        print('name_sync: target paths already exist: ' + ', '.join(clash), file=sys.stderr)
        return 1
    verb = 'rewrote' if args.apply else 'would rewrite'
    print(f'name_sync: {verb} {total} occurrence(s) in {len(edits)} file(s), '
          f'{"moved" if args.apply else "would move"} {len(moves)} path(s) in {repo}')
    if not args.apply:
        print('name_sync: dry run; read the list, then run again with --apply '
              '(--skip GLOB for a file whose old name is history, --keep-ids once App Store Connect has the ids)')
        return 0
    for rel, new_text, _ in edits:
        path = os.path.join(repo, rel)
        mode = os.stat(path).st_mode
        tmp = f'{path}.name_sync.tmp'
        with open(tmp, 'w', encoding='utf-8', newline='') as f:
            f.write(new_text)
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    for rel, new_rel in moves:
        src, dst = os.path.join(repo, rel), os.path.join(repo, new_rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        os.replace(src, dst)
        prune_empty(repo, os.path.dirname(src))
    return 0


def prune_empty(repo, folder):
    while os.path.abspath(folder) != repo and os.path.isdir(folder) and not os.listdir(folder):
        os.rmdir(folder)
        folder = os.path.dirname(folder)


# Check

class Report:
    def __init__(self):
        self.rows = []

    def add(self, status, place, detail=''):
        self.rows.append((status, place, detail))

    def ok(self, cond, place, good, bad):
        self.add('PASS' if cond else 'FAIL', place, good if cond else bad)

    def print(self):
        width = max((len(p) for _, p, _ in self.rows), default=0)
        for status, place, detail in self.rows:
            print(f'{status:<5} {place:<{width}}  {detail}')
        fails = sum(1 for s, _, _ in self.rows if s == 'FAIL')
        print(f'name_sync: {fails} FAIL, {sum(1 for s, _, _ in self.rows if s == "PASS")} PASS, '
              f'{sum(1 for s, _, _ in self.rows if s == "SKIP")} SKIP')
        return 1 if fails else 0


def read(path):
    try:
        with open(path, encoding='utf-8') as f:
            return f.read()
    except (OSError, UnicodeDecodeError):
        return None


def parse_status(text):
    state = {'name': None, 'header': '', 'done': set(), 'g1': False, 'kept': set()}
    in_log = False
    for line in text.splitlines():
        if line.startswith('## '):
            in_log = line[3:].strip().lower() == 'gate log'
            continue
        if m := re.match(r'#\s*Clone status:\s*(.+?)\s*\(clone of', line):
            name = re.sub(r'\s*\(.*$', '', m.group(1)).strip()
            state['name'] = None if '{{' in name else name
        elif line.startswith('Reference:'):
            state['header'] = line
        elif m := re.match(r'Kept ids:\s*(.*)$', line):
            # bundle / Android ids App Store Connect already holds, kept through a rename (`rename --keep-ids`)
            state['kept'] = set(re.findall(r'[A-Za-z][\w]*(?:\.[\w]+)+', m.group(1)))
        elif m := re.match(r'- \[[xX]\] (S\d+)\b', line):
            state['done'].add(m.group(1))
        elif in_log and line.startswith('|'):
            cells = [c.strip() for c in line.strip('|').split('|')]
            if cells and cells[0] == 'G1' and len(cells) > 2 and APPROVED.match(cells[2].strip('*"“ ')):
                state['g1'] = True
    return state


def header_field(header, key):
    m = re.search(rf'{key}:\s*(.*?)(?:\s+·\s+[A-Z][a-z]+:|$)', header)
    return m.group(1).strip() if m else ''


def repo_name_of(url):
    m = re.search(r'github\.com[:/]([^/]+)/([^/\s]+?)(?:\.git)?/?$', url or '')
    return (m.group(1), m.group(2)) if m else (None, None)


def main_checkout(path):
    """The main checkout of PATH's repository (PATH itself unless it is a linked worktree)."""
    proc = git(path, 'rev-parse', '--path-format=absolute', '--git-common-dir', check=False)
    common = proc.stdout.strip()
    if proc.returncode != 0 or not common:
        return path
    return os.path.dirname(common) if os.path.basename(common) == '.git' else path


def origin(repo):
    proc = git(repo, 'remote', 'get-url', 'origin', check=False)
    return proc.stdout.strip() if proc.returncode == 0 else ''


def plist_value(text, key):
    m = re.search(rf'<key>{re.escape(key)}</key>\s*<string>([^<]*)</string>', text or '')
    return m.group(1) if m else None


def grep_files(repo, regex, skips=()):
    hits = []
    if not os.path.isdir(os.path.join(repo, '.git')) and not os.path.isfile(os.path.join(repo, '.git')):
        return hits
    for rel in listed_files(repo, skips):
        text = read_text_file(os.path.join(repo, rel))
        if text is None:
            continue
        for m in regex.finditer(text):
            hits.append(f'{rel}:{text.count(chr(10), 0, m.start()) + 1}: {m.group(0)}')
    return hits


def grep_old(repo, mapper, skips=(), keep_ids=False, only=None):
    """Leftovers of the old name; with kept ids, a match inside a reverse-DNS id is not one."""
    hits = []
    for rel in listed_files(repo, skips):
        if only and rel not in only:
            continue
        text = read_text_file(os.path.join(repo, rel))
        if text is None:
            continue
        for m in mapper.regex.finditer(text):
            if keep_ids and mapper.is_id(text, m.start(), m.end()):
                continue
            hits.append(f'{rel}:{text.count(chr(10), 0, m.start()) + 1}: {m.group(0)}')
    return hits


def summary(hits, limit=6):
    shown = '; '.join(hits[:limit])
    return shown + (f'; … {len(hits) - limit} more' if len(hits) > limit else '')


def http_status(url):
    req = urllib.request.Request(url, method='HEAD', headers={'User-Agent': 'name_sync'})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status
    except urllib.error.HTTPError as err:
        return err.code
    except (urllib.error.URLError, TimeoutError, OSError):
        return None


def cmd_check(args):
    repo = os.path.abspath(args.repo).rstrip('/')
    report = Report()
    # A stage worktree is checked as its content plus the main checkout's folder, site and registry.
    checkout, repo = repo, main_checkout(repo)
    status_text = read(os.path.join(checkout, '.clone', 'status.md'))
    if status_text is None:
        print(f'name_sync: no .clone/status.md in {checkout}', file=sys.stderr)
        return 66
    state = parse_status(status_text)
    url = origin(repo)
    owner, remote_name = repo_name_of(url)
    folder = os.path.basename(repo)
    parent = os.path.dirname(repo)

    if not (state['g1'] or 'S2' in state['done']) and not args.name:
        report.ok(remote_name == folder, 'folder = GitHub repo', f'working slug {folder} (before G1)',
                  f'folder {folder} but origin is {url or "missing"}')
        report.ok(not folder.endswith('-clone'), 'no -clone suffix', folder, f'{folder} ends in -clone')
        return report.print()

    name = args.name or state['name']
    if not name:
        print('name_sync: status.md has no game name in its title; pass --name', file=sys.stderr)
        return 66
    f = forms(name)
    slug, site_slug = f['kebab'], f['kebab'] + '-site'

    # Game repo
    report.ok(folder == slug, 'folder', f'{folder}', f'{folder}, expected {slug} (mv {repo} {parent}/{slug})')
    report.ok(remote_name == slug, 'origin', url, f'{url or "missing"}, expected …/{owner or "<owner>"}/{slug}.git')
    repo_field = header_field(state['header'], 'Repo')
    report.ok(bool(re.search(rf'github\.com/[^/\s]+/{re.escape(slug)}(?![\w-])', repo_field)), 'status.md Repo:',
              repo_field, f'"{repo_field}", expected github.com/{owner or "<owner>"}/{slug}')
    design = read(os.path.join(checkout, 'DESIGN.md'))
    if design is None:
        report.add('SKIP', 'DESIGN.md', 'not written yet')
    else:
        report.ok(name in design, 'DESIGN.md', f'names {name}', f'never names "{name}"')

    pubspec = read(os.path.join(checkout, 'pubspec.yaml'))
    if pubspec is None:
        report.add('SKIP', 'pubspec name', 'no Flutter project yet (S3)')
    else:
        m = re.search(r'^name:\s*(\S+)', pubspec, re.MULTILINE)
        got = m.group(1) if m else None
        report.ok(got == f['snake'], 'pubspec name', got, f'{got}, expected {f["snake"]}')

    plist = read(os.path.join(checkout, 'ios', 'Runner', 'Info.plist'))
    if plist is None:
        report.add('SKIP', 'iOS display name', 'no ios/ yet')
    else:
        got = plist_value(plist, 'CFBundleDisplayName')
        report.ok(got == name, 'iOS display name', got, f'{got}, expected {name}')
    pbx = read(os.path.join(checkout, 'ios', 'Runner.xcodeproj', 'project.pbxproj'))
    if pbx is not None:
        ids = sorted(set(re.findall(r'PRODUCT_BUNDLE_IDENTIFIER = "?([^";]+)"?;', pbx)))
        app_ids = [i for i in ids if not i.endswith('.RunnerTests')]
        tests_ok = all(i in app_ids or any(i == a + '.RunnerTests' for a in app_ids) for i in ids)
        kept = len(app_ids) == 1 and app_ids[0] in state['kept']
        good = len(app_ids) == 1 and tests_ok and (kept or app_ids[0].rsplit('.', 1)[-1].lower() == f['compact'])
        report.ok(good, 'iOS bundle id', app_ids[0] + (' (Kept ids: App Store Connect holds it)' if kept else '')
                  if app_ids else '-',
                  f'{", ".join(ids) or "none"}, expected one <org>.{f["compact"]} (+ .RunnerTests), '
                  'or list it under "Kept ids:" in status.md once App Store Connect holds it')

    manifest = read(os.path.join(checkout, 'android', 'app', 'src', 'main', 'AndroidManifest.xml'))
    if manifest is None:
        report.add('SKIP', 'Android label', 'no android/ yet')
    else:
        m = re.search(r'android:label="([^"]*)"', manifest)
        got = m.group(1) if m else None
        report.ok(got == name, 'Android label', got, f'{got}, expected {name}')
        gradle = read(os.path.join(checkout, 'android', 'app', 'build.gradle.kts')) or read(
            os.path.join(checkout, 'android', 'app', 'build.gradle')) or ''
        m = re.search(r'applicationId\s*=?\s*"([^"]+)"', gradle)
        got = m.group(1) if m else None
        last = (got or '').rsplit('.', 1)[-1].lower()
        kept_tails = {k.rsplit('.', 1)[-1].lower().replace('_', '') for k in state['kept']}
        kept = bool(got) and (got in state['kept'] or last.replace('_', '') in kept_tails)
        report.ok(last in (f['snake'], f['compact']) or kept, 'Android applicationId',
                  f'{got}' + (' (Kept ids)' if kept else ''), f'{got}, expected <org>.{f["snake"]}')

    web = read(os.path.join(checkout, 'web', 'index.html'))
    if web is None:
        report.add('SKIP', 'web title', 'no web/ yet')
    else:
        m = re.search(r'<title>([^<]*)</title>', web)
        got = m.group(1).strip() if m else None
        webmanifest = read(os.path.join(checkout, 'web', 'manifest.json')) or '{}'
        try:
            wm = json.loads(webmanifest)
        except ValueError:
            wm = {}
        good = got == name and wm.get('name', name) == name
        report.ok(good, 'web title', got, f'<title>{got}</title>, manifest name {wm.get("name")!r}, expected {name}')

    stale = re.compile(rf'[\w-]+\.github\.io/(?!{re.escape(site_slug)}(?![\w-]))[\w-]+-site\b')
    hits = grep_files(checkout, stale, args.skip)
    report.ok(not hits, 'site URLs in game repo', f'only {site_slug}', 'other sites: ' + summary(hits))

    worktrees = git(repo, 'worktree', 'list', '--porcelain', check=False).stdout
    broken = [line[9:] for line in worktrees.splitlines()
              if line.startswith('worktree ') and not os.path.isdir(line[9:])]
    fixes = []
    for path in broken:  # a moved repo leaves its worktrees pointing at the old path
        moved = repo + path[path.index('/.claude/worktrees/'):] if '/.claude/worktrees/' in path else None
        fixes.append(f'git -C {repo} worktree repair {moved}' if moved and os.path.isdir(moved)
                     else f'git -C {repo} worktree prune')
    report.ok(not broken, 'worktrees', 'all paths exist',
              f'missing {", ".join(broken)} ({"; ".join(sorted(set(fixes)))})')

    # Site repo
    site = os.path.join(parent, site_slug)
    landing = header_field(state['header'], 'Landing')
    site_due = 'S7' in state['done']
    if not os.path.isdir(site):
        others = [d for d in os.listdir(parent) if d.endswith('-site') and d != site_slug and
                  d.startswith(tuple(forms(o)['kebab'] for o in args.old))] if args.old else []
        if site_due or others:
            report.add('FAIL', 'site folder', f'{site} missing' + (f'; found {", ".join(others)}' if others else ''))
        else:
            report.add('SKIP', 'site folder', 'no site repo yet (S7)')
    else:
        s_url = origin(site)
        if not s_url and not site_due:
            report.add('SKIP', 'site origin', 'not pushed yet (S7 open)')
        else:
            report.ok(repo_name_of(s_url)[1] == site_slug, 'site origin', s_url,
                      f'{s_url or "missing"}, expected …/{site_slug}.git')
        report.ok(site_slug in landing, 'status.md Landing:', landing,
                  f'"{landing or "—"}", expected the {site_slug} repo and Pages URL')
        index = read(os.path.join(site, 'index.html'))
        report.ok(index is not None and name in index, 'site index.html', f'names {name}',
                  'missing' if index is None else f'never names "{name}"')
        hits = grep_files(site, stale, args.skip)
        report.ok(not hits, 'site URLs in site repo', f'only {site_slug}', 'other sites: ' + summary(hits))

    # Root Pages repo
    root = os.path.join(parent, f'{owner}.github.io') if owner else None
    if root and os.path.isdir(root):
        robots, llms = read(os.path.join(root, 'robots.txt')) or '', read(os.path.join(root, 'llms.txt')) or ''
        listed = f'{site_slug}/' in robots or f'{site_slug}/' in llms
        if 'S9' in state['done'] or listed:
            good_r = f'{owner}.github.io/{site_slug}/sitemap.xml' in robots
            line = next((ln for ln in llms.splitlines() if f'{site_slug}/' in ln), '')
            good_l = f'[{name}]' in line
            report.ok(good_r, 'root robots.txt', f'Sitemap …/{site_slug}/sitemap.xml',
                      f'no Sitemap line for {site_slug}')
            report.ok(good_l, 'root llms.txt', line.strip()[:80], f'no "- [{name}](…/{site_slug}/llms.txt)" line'
                      + (f' (found: {line.strip()[:60]})' if line else ''))
        else:
            report.add('SKIP', 'root Pages listing', 'not listed yet (S9)')
    else:
        report.add('SKIP', 'root Pages listing', f'no {owner}.github.io checkout in {parent}')

    # Telegram registry
    repos_json = os.path.join(TELEGRAM_DIR, 'repos.json')
    if os.path.isfile(os.path.join(TELEGRAM_DIR, 'telegram.env')):
        try:
            registered = json.loads(read(repos_json) or '[]')
        except ValueError:
            registered = []
        old_paths = [os.path.join(parent, forms(o)['kebab']) for o in args.old]
        stale_paths = [p for p in registered if p in old_paths]
        good = repo in registered and not stale_paths
        report.ok(good, 'Telegram registry', 'registered',
                  ('not registered' if repo not in registered else '') +
                  (f' still lists {", ".join(stale_paths)}' if stale_paths else '') +
                  f' (telegram_bridge.py register {repo}' + (f' --was {stale_paths[0]})' if stale_paths else ')'))
    else:
        report.add('SKIP', 'Telegram registry', 'Telegram not set up')

    # Leftovers of the old name
    for old in args.old:
        o = forms(old)
        if o['kebab'] == slug:
            continue
        leftover = Mapper(old, name)
        keep = bool(state['kept'])
        for where in (checkout, site):
            if not os.path.isdir(where):
                continue
            hits = grep_old(where, leftover, args.skip, keep)
            report.ok(not hits, f'old "{o["title"]}" in {os.path.basename(where)}', 'none',
                      summary(hits) + f' (name_sync.py rename {where} --old "{old}" --new "{name}"'
                      + (' --keep-ids)' if keep else ')'))
        if root and os.path.isdir(root):
            hits = grep_old(root, leftover, only={'robots.txt', 'llms.txt'})
            report.ok(not hits, f'old "{o["title"]}" in root Pages', 'none', summary(hits))
        gone = [p for p in (os.path.join(parent, o['kebab']), os.path.join(parent, o['kebab'] + '-site'))
                if os.path.exists(p)]
        report.ok(not gone, f'old "{o["title"]}" folders', 'none left', 'still there: ' + ', '.join(gone))

    if args.online:
        online(report, owner, slug, site_slug, os.path.isdir(site), [forms(o)['kebab'] for o in args.old])
    return report.print()


def online(report, owner, slug, site_slug, has_site, old_slugs):
    if not owner:
        report.add('FAIL', 'GitHub', 'no GitHub origin to check')
        return
    for repo_name in [slug] + ([site_slug] if has_site else []):
        proc = subprocess.run(['gh', 'repo', 'view', f'{owner}/{repo_name}', '--json', 'name', '--jq', '.name'],
                              capture_output=True, text=True)
        got = proc.stdout.strip()
        report.ok(proc.returncode == 0 and got == repo_name, f'GitHub {repo_name}', 'exists under that name',
                  got and f'resolves to {got} (gh repo rename {repo_name} -R {owner}/{got} --yes)'
                  or proc.stderr.strip()[:120])
    if has_site:
        base = f'https://{owner}.github.io/{site_slug}/'
        for page in ('', 'privacy.html', 'support.html'):
            code = http_status(base + page)
            report.ok(code == 200, f'Pages /{page or ""}', f'{base + page} 200',
                      f'{base + page} {code} (after a rename: gh api -X POST repos/{owner}/{site_slug}/pages/builds)')
        for old in old_slugs:
            if old != slug:
                code = http_status(f'https://{owner}.github.io/{old}-site/')
                report.add('INFO', 'old Pages URL', f'https://{owner}.github.io/{old}-site/ {code} '
                           '(GitHub does not redirect a renamed Pages site; update every link that used it)')


def cmd_names(args):
    f = forms(args.name)
    for form in FORMS:
        print(f'{form:<8} {f[form]}')
    print(f'{"site":<8} {f["kebab"]}-site')
    print(f'{"bundle":<8} <org>.{f["compact"]}')
    return 0


def main(argv):
    parser = argparse.ArgumentParser(prog='name_sync.py', description=__doc__.split('\n\n')[0])
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('names')
    p.add_argument('name')
    p = sub.add_parser('rename')
    p.add_argument('path')
    p.add_argument('--old', required=True)
    p.add_argument('--new', required=True)
    p.add_argument('--apply', action='store_true')
    p.add_argument('--keep-ids', action='store_true')
    p.add_argument('--skip', action='append', default=[], metavar='GLOB')
    p.add_argument('--show', type=int, default=5, help='hits shown per file (default 5)')
    p = sub.add_parser('check')
    p.add_argument('repo')
    p.add_argument('--name', help='the game name, when status.md does not carry it yet')
    p.add_argument('--old', action='append', default=[], metavar='NAME')
    p.add_argument('--skip', action='append', default=[], metavar='GLOB')
    p.add_argument('--online', action='store_true')
    args = parser.parse_args(argv[1:])
    return {'names': cmd_names, 'rename': cmd_rename, 'check': cmd_check}[args.command](args)


if __name__ == '__main__':
    sys.exit(main(sys.argv))
