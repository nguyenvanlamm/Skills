#!/usr/bin/env python3
"""Steps pane: the pipeline's stages S0–S9 in a herdr pane to the right of the agent, redrawn
whenever .clone/status.md changes, so the human sees which stage the run is at.

  scripts/steps_pane.py open REPO    # split the agent's pane to the right and watch REPO there
  scripts/steps_pane.py watch REPO   # the loop that runs inside that pane
  scripts/steps_pane.py once REPO    # print the steps once, plain text (no herdr: paste in chat)
  scripts/steps_pane.py close REPO   # close REPO's steps pane in this tab

Reads the newest .clone/status.md of REPO and its worktrees (.claude/worktrees/*/, where a
background session works each stage): the `- [x] S<n> …` stage lines with their `**G…**` gate,
the Gate log table (a gate is passed once it has a row whose Decision does not start with reject,
revise or no), and the `Now:` / `Waiting on:` lines. The current stage is the one a
`Now: S<n> · …` line names, else the first unchecked one. `open` exits 69 when herdr is not
available, after printing the steps. Standard library only.
"""
import glob
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import textwrap
import time
import unicodedata

PANE_TITLE = 'clone-steps'
LABELS = {
    'S0': 'Chọn game',
    'S1': 'SPEC',
    'S2': 'DESIGN',
    'S3': 'Core Flutter',
    'S4': 'Giao diện',
    'S5': 'IAP + chơi thử',
    'S6': 'Soát code',
    'S7': 'Landing',
    'S8': 'iOS + nộp',
    'S9': 'Hoàn thiện',
}
LABEL_WIDTH = max(len(label) for label in LABELS.values())
RULE_WIDTH = 32
EMPTY = {'', '—', '–', '-', 'none'}
NOT_PASSED = re.compile(r'^(reject|revise|no\b|từ chối|làm lại)', re.IGNORECASE)

STYLES = {'done': '32', 'current': '1;33', 'todo': '2', 'wait': '35', 'title': '1'}


def mtime(path):
    try:
        return os.path.getmtime(path)
    except OSError:
        return None


def status_path(repo):
    """REPO's newest status.md: a background session updates its worktree's copy, and `main` only
    catches up when the stage is merged. `main`'s copy wins a tie."""
    best = os.path.join(repo, '.clone', 'status.md')
    best_time = mtime(best)
    for path in glob.glob(os.path.join(glob.escape(repo), '.claude', 'worktrees', '*', '.clone', 'status.md')):
        if (stamp := mtime(path)) is not None and (best_time is None or stamp > best_time):
            best, best_time = path, stamp
    return best


def worktree_of(repo, path):
    """The worktree folder name when PATH is a worktree's copy, else None."""
    parts = os.path.relpath(path, repo).split(os.sep)
    return parts[2] if parts[:2] == ['.claude', 'worktrees'] and len(parts) > 2 else None


def value(text):
    text = text.strip()
    return None if text.lower() in EMPTY else text


def parse(text):
    """status.md → {'title', 'name', 'stages': [{'id', 'done', 'label', 'gate'}], 'passed', 'now', 'waiting'}."""
    state = {'title': None, 'name': None, 'stages': [], 'passed': set(), 'now': None, 'waiting': None}
    in_gate_log = False
    for line in text.splitlines():
        if line.startswith('## '):
            in_gate_log = line[3:].strip().lower() == 'gate log'
            continue
        if m := re.match(r'#\s*Clone status:\s*(.+?)\s*\(clone of\s*(.+?)\)\s*$', line):
            name, refs = (part if '{{' not in part else None for part in m.groups())
            if name:
                state['name'] = name
                state['title'] = f'{name} ← {refs}' if refs else name
        elif m := re.match(r'Now:\s*(.*)$', line, re.IGNORECASE):
            state['now'] = value(m.group(1))
        elif m := re.match(r'Waiting on:\s*(.*)$', line, re.IGNORECASE):
            state['waiting'] = value(m.group(1))
        elif m := re.match(r'- \[([ xX])\] (S\d+)\b\s*(.*)$', line):
            stage_id, rest = m.group(2), m.group(3)
            gate = re.search(r'\*\*(G\d+b?)\*\*', rest)
            label = LABELS.get(stage_id) or rest.split(':')[0].strip('` ')[:LABEL_WIDTH]
            state['stages'].append({'id': stage_id, 'done': m.group(1) != ' ', 'label': label,
                                    'gate': gate.group(1) if gate else None})
        elif in_gate_log and line.startswith('|'):
            cells = [cell.strip() for cell in line.strip('|').split('|')]
            if re.fullmatch(r'G\d+b?', cells[0]) and not NOT_PASSED.match(cells[2] if len(cells) > 2 else ''):
                state['passed'].add(cells[0])
    return state


def current_stage(state):
    """The stage `Now: S<n> · …` names, else the first unchecked one. A free-form `Now:` that only mentions
    stages (`S8 done: …`, `S0–S7 and S9 done`) names none."""
    named = re.match(r'(S\d+)\s*·', state['now'] or '')
    ids = [stage['id'] for stage in state['stages']]
    if named and named.group(1) in ids:
        return named.group(1)
    return next((stage['id'] for stage in state['stages'] if not stage['done']), None)


def cell_width(text):
    return sum(0 if unicodedata.combining(ch) else 2 if unicodedata.east_asian_width(ch) in 'WF' else 1
               for ch in text)


def pad(text, width):
    return text + ' ' * max(0, width - cell_width(text))


def emit(segments, columns, color):
    """Join (text, style) segments into one line cut to `columns` cells, styled when `color`."""
    out, used = [], 0
    for text, style in segments:
        room = columns - used
        if room <= 0:
            break
        if cell_width(text) > room:
            cut = ''
            for ch in text:
                if cell_width(cut + ch) > room - 1:
                    break
                cut += ch
            text = cut + '…'
        used += cell_width(text)
        out.append(f'\033[{STYLES[style]}m{text}\033[0m' if color and style else text)
    return ''.join(out) if color else ''.join(out).rstrip()


def render(repo, columns, color):
    """The pane's lines for REPO at `columns` cells wide."""
    path = status_path(repo)
    try:
        with open(path, encoding='utf-8') as f:
            state = parse(f.read())
        updated = time.strftime('%H:%M:%S', time.localtime(os.path.getmtime(path)))
    except FileNotFoundError:
        return [emit([('Chưa có .clone/status.md', 'todo')], columns, color),
                emit([(repo, 'todo')], columns, color)]

    current = current_stage(state)
    rule = '─' * min(columns, RULE_WIDTH)
    lines = [emit([(state['title'] or 'Clone status', 'title')], columns, color), rule]
    for stage in state['stages']:
        is_current = stage['id'] == current
        if is_current:
            mark, style = '▶', 'current'
        elif stage['done']:
            mark, style = '✓', 'done'
        else:
            mark, style = '·', 'todo'
        segments = [(f'{mark} {stage["id"]} {pad(stage["label"], LABEL_WIDTH)} ', style)]
        if stage['gate']:
            passed = stage['gate'] in state['passed']
            segments.append((pad(stage['gate'], 3), 'done' if passed else 'todo'))
            if passed:
                segments.append((' ✓', 'done'))
        if is_current and state['waiting']:
            segments.append((' ⏸', 'wait'))
        lines.append(emit(segments, columns, color))
    if not current and state['stages']:
        lines.append(emit([('Xong tất cả các bước', 'done')], columns, color))
    lines.append(rule)
    for label, text, style in (('Đang làm', state['now'], 'current'), ('Chờ bạn', state['waiting'], 'wait')):
        wrapped = textwrap.wrap(f'{label}: {text or "—"}', width=max(columns, 10), subsequent_indent='  ')
        lines.extend(emit([(part, style if text else 'todo')], columns, color) for part in wrapped)
    worktree = worktree_of(repo, path)
    lines.append(emit([(f'Cập nhật {updated}' + (f' · worktree {worktree}' if worktree else ''), 'todo')],
                      columns, color))
    return lines


def watch(repo):
    shown = None
    sys.stdout.write(f'\033]0;{PANE_TITLE}: {os.path.basename(repo)}\007\033[?25l')
    try:
        while True:
            path = status_path(repo)
            stamp = mtime(path)
            size = shutil.get_terminal_size()
            if (path, stamp, size) != shown:
                shown = (path, stamp, size)
                lines = render(repo, max(size.columns, 10), color=True)
                sys.stdout.write('\033[H\033[2J' + '\n'.join(lines[:size.lines]))
                sys.stdout.flush()
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        sys.stdout.write('\033[?25h\n')


def herdr(*args):
    done = subprocess.run(['herdr', *args], capture_output=True, text=True)
    if done.returncode != 0:
        print(f'herdr {" ".join(args)} failed: {(done.stderr or done.stdout).strip()}', file=sys.stderr)
        sys.exit(70)
    return done.stdout


def steps_panes(repo):
    """Ids of REPO's steps panes in the agent's tab."""
    me = json.loads(herdr('pane', 'get', os.environ['HERDR_PANE_ID']))['result']['pane']
    title = f'{PANE_TITLE}: {os.path.basename(repo)}'
    return [pane['pane_id'] for pane in json.loads(herdr('pane', 'list'))['result']['panes']
            if pane.get('tab_id') == me['tab_id']
            and (pane.get('terminal_title_stripped') or pane.get('terminal_title') or '').strip() == title]


def has_herdr():
    return bool(os.environ.get('HERDR_PANE_ID')) and shutil.which('herdr') is not None


def open_pane(repo):
    if not has_herdr():
        print('\n'.join(render(repo, 48, color=False)))
        print('herdr is not available: no steps pane; show these lines in the chat instead', file=sys.stderr)
        return 69
    if existing := steps_panes(repo):
        print(f'steps pane {existing[0]} is already open')
        return 0
    split = json.loads(herdr('pane', 'split', os.environ['HERDR_PANE_ID'], '--direction', 'right',
                             '--ratio', '0.7', '--no-focus', '--cwd', repo))['result']
    pane = (split.get('pane') or split)['pane_id']
    subprocess.run(['herdr', 'pane', 'rename', pane, PANE_TITLE], capture_output=True)
    herdr('pane', 'run', pane, shlex.join(['python3', os.path.abspath(__file__), 'watch', repo]))
    print(f'steps pane {pane} opened')
    return 0


def close_pane(repo):
    if not has_herdr():
        return 0
    panes = steps_panes(repo)
    for pane in panes:
        herdr('pane', 'close', pane)
    print(f'closed {len(panes)} steps pane(s)')
    return 0


def main(argv):
    if len(argv) != 3 or argv[1] not in ('open', 'watch', 'once', 'close'):
        print(__doc__.split('\n\n')[1], file=sys.stderr)
        return 64
    repo = os.path.abspath(argv[2])
    if not os.path.isdir(repo):
        print(f'no such directory: {repo}', file=sys.stderr)
        return 66
    if argv[1] == 'once':
        print('\n'.join(render(repo, 48, color=False)))
    elif argv[1] == 'watch':
        watch(repo)
    elif argv[1] == 'open':
        return open_pane(repo)
    else:
        return close_pane(repo)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
