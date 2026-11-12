#!/usr/bin/env python3
"""Steps pane: an episode's steps in a herdr pane to the right of the agent, so the human sees
at a glance which step the work is at.

  steps_pane.py open EPISODE     split the agent's pane to the right and watch EPISODE there
  steps_pane.py watch EPISODE    the loop that runs inside that pane
  steps_pane.py once EPISODE     print the block once, plain text (no herdr: paste it in the chat)
  steps_pane.py close EPISODE    close EPISODE's steps pane in this tab

EPISODE is an episode folder (it holds words.txt and one folder per level). The agent's own steps
(words, dialogues, keywords, metadata) are read from the files that exist; the pipeline steps of
each level come from <LEVEL>/state.json, which run.py updates as it works. `open` exits 69 when
herdr is not available, after printing the block. Modelled on
remix-chart-to-video/scripts/steps_pane.py. Standard library only: run it with plain python3.
"""
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

PANE_TITLE = 'vocab-steps'
RULE_WIDTH = 36
LEVEL_DIR = re.compile(r'^[ABC][12]$')
# What the pane shows for a level; run.py reports render and check together, one format at a time.
PIPELINE = [('validate', 'Kiểm tra hội thoại'), ('tts', 'Giọng nói'), ('build', 'Ghép âm thanh'),
            ('publish', 'Trường đăng bài'), ('thumbnail', 'Thumbnail, bìa'), ('render', 'Render, kiểm tra video')]
STYLES = {'done': '32', 'current': '1;33', 'todo': '2', 'title': '1', 'bad': '1;31', 'head': '1;36'}
MARKS = {'done': ('✓', 'done'), 'running': ('▶', 'current'), 'failed': ('✗', 'bad'), 'todo': ('·', 'todo')}


def cell_width(text):
    return sum(0 if unicodedata.combining(ch) else 2 if unicodedata.east_asian_width(ch) in 'WF' else 1 for ch in text)


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


def ms(seconds):
    s = int(max(0, seconds))
    return f'{s // 60}:{s % 60:02d}'


def read_json(path):
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):       # missing, or caught halfway through a write
        return None


def alive(pid):
    try:
        os.kill(int(pid), 0)
    except (OSError, TypeError, ValueError):
        return False
    return True


def levels(episode):
    try:
        return sorted(n for n in os.listdir(episode) if LEVEL_DIR.match(n) and os.path.isdir(os.path.join(episode, n)))
    except OSError:
        return []


def level_steps(folder, now):
    """[(label, status, detail)] for one level's pipeline, plus its headline and a failure text."""
    state = read_json(os.path.join(folder, 'state.json')) or {}
    prog = state.get('progress')
    rows, error, running = [], None, None
    if prog is None:                    # a run from before run.py reported progress
        done = set(state.get('steps') or {})
        if 'check' in done:
            done.add('render')
        return [(label, 'done' if key in done else 'todo', '') for key, label in PIPELINE], None, None, state
    dead = prog.get('status') == 'running' and not alive(prog.get('pid'))
    for key, label in PIPELINE:
        if key in (prog.get('done') or []):
            rows.append((label, 'done', ''))
        elif key == prog.get('current'):
            detail = prog.get('detail') or ''
            if prog.get('status') == 'running' and not dead:
                clock = ms(now - (prog.get('step_started_at') or now))
                rows.append((label, 'running', f'{detail} {clock}'.strip()))
                running = f'{label}{" · " + detail if detail else ""}'
            else:
                rows.append((label, 'failed', detail))
                error = prog.get('error') or ('tiến trình đã dừng giữa chừng' if dead else 'bước này lỗi')
        else:
            rows.append((label, 'todo', ''))
    return rows, error, running, state


def render(episode, columns, color, now=None):
    """The pane's lines for EPISODE at `columns` cells wide."""
    now = now or time.time()
    rule = '─' * min(columns, RULE_WIDTH)
    lvls = levels(episode)
    lines = [emit([('vocab-to-video', 'title')], columns, color),
             emit([(os.path.basename(episode), 'todo')], columns, color), rule]

    def per_level(name):
        return [(lv, os.path.isfile(os.path.join(episode, lv, name))) for lv in lvls]

    try:
        with open(os.path.join(episode, 'words.txt'), encoding='utf-8') as f:
            words = sum(1 for line in f if line.strip())
    except OSError:
        words = 0
    dialogues, metadata = per_level('dialogue.json'), per_level('metadata.json')
    agent = [('Từ vựng', bool(words), f'{words} từ' if words else ''),
             ('Hội thoại', bool(dialogues) and all(ok for _, ok in dialogues),
              '  '.join(f'{lv} {"✓" if ok else "·"}' for lv, ok in dialogues)),
             ('Từ khóa tìm kiếm', os.path.isfile(os.path.join(episode, 'keywords.json')), ''),
             ('Metadata', bool(metadata) and all(ok for _, ok in metadata),
              '  '.join(f'{lv} {"✓" if ok else "·"}' for lv, ok in metadata))]

    blocks, running, errors, results = [], [], [], []
    for lv in lvls:
        folder = os.path.join(episode, lv)
        rows, error, run, state = level_steps(folder, now)
        title = (read_json(os.path.join(folder, 'dialogue.json')) or {}).get('title') or ''
        blocks.append((lv, title, rows))
        if run:
            running.append(f'{lv} {run}')
        if error:
            errors.append(f'{lv}: {error}')
        checks = (state.get('steps') or {}).get('check') or {}
        if rows and all(status == 'done' for _, status, _ in rows) and checks:
            bad = sum(1 for c in checks.values() if c.get('problems'))
            results.append(f'{lv} {"FAIL" if bad else "PASS"} ({len(checks)} video)')

    # The first open agent step is the one being worked on, unless a pipeline is already running.
    first_open = next((i for i, (_, ok, _) in enumerate(agent) if not ok), None)
    width = max(cell_width(label) for label, _, _ in agent)
    for i, (label, ok, detail) in enumerate(agent):
        status = 'done' if ok else 'running' if i == first_open and not running else 'todo'
        mark, style = MARKS[status]
        lines.append(emit([(f'{mark} {pad(label, width)}  ', style), (detail, style)], columns, color))

    width = max(cell_width(label) for _, label in PIPELINE)
    for lv, title, rows in blocks:
        lines.append(rule)
        lines.append(emit([(lv, 'head'), (f' · {title}' if title else '', 'title')], columns, color))
        for label, status, detail in rows:
            mark, style = MARKS[status]
            lines.append(emit([(f' {mark} {pad(label, width)}  ', style), (detail, style)], columns, color))

    lines.append(rule)
    wrap = max(columns, 10)
    for text in errors:
        lines.extend(emit([(part, 'bad')], columns, color)
                     for part in textwrap.wrap(f'Lỗi {text}', width=wrap, subsequent_indent='  ')[:4])
    if running:
        for text in running:
            lines.extend(emit([(part, 'current')], columns, color)
                         for part in textwrap.wrap(f'Đang làm: {text}', width=wrap, subsequent_indent='  ')[:3])
    elif lvls and len(results) == len(lvls):
        lines.append(emit([('Xong: ' + ' · '.join(results), 'done')], columns, color))
    elif not errors:
        todo = agent[first_open][0] if first_open is not None else 'chạy pipeline'
        lines.append(emit([(f'Đang làm: {todo}', 'current')], columns, color))
    lines.append(emit([(f'cập nhật {time.strftime("%H:%M:%S", time.localtime(now))}', 'todo')], columns, color))
    return lines


def watch(episode):
    shown = None
    sys.stdout.write(f'\033]0;{PANE_TITLE}: {os.path.basename(episode)}\007\033[?25l')
    try:
        while True:
            size = shutil.get_terminal_size()
            lines = render(episode, max(size.columns, 10), color=True)
            frame = '\n'.join(lines[:size.lines])
            if frame != shown:
                shown = frame
                sys.stdout.write('\033[H\033[2J' + frame)
                sys.stdout.flush()
            time.sleep(1.0)
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


def steps_panes(episode):
    """Ids of EPISODE's steps panes in the agent's tab."""
    me = json.loads(herdr('pane', 'get', os.environ['HERDR_PANE_ID']))['result']['pane']
    title = f'{PANE_TITLE}: {os.path.basename(episode)}'
    return [pane['pane_id'] for pane in json.loads(herdr('pane', 'list'))['result']['panes']
            if pane.get('tab_id') == me['tab_id']
            and (pane.get('terminal_title_stripped') or pane.get('terminal_title') or '').strip() == title]


def has_herdr():
    return bool(os.environ.get('HERDR_PANE_ID')) and shutil.which('herdr') is not None


def open_pane(episode):
    if not has_herdr():
        print('\n'.join(render(episode, 48, color=False)))
        print('herdr is not available: no steps pane; show these lines in the chat instead', file=sys.stderr)
        return 69
    if existing := steps_panes(episode):
        print(f'steps pane {existing[0]} is already open')
        return 0
    split = json.loads(herdr('pane', 'split', os.environ['HERDR_PANE_ID'], '--direction', 'right',
                             '--ratio', '0.7', '--no-focus', '--cwd', episode))['result']
    pane = (split.get('pane') or split)['pane_id']
    subprocess.run(['herdr', 'pane', 'rename', pane, PANE_TITLE], capture_output=True)
    herdr('pane', 'run', pane, shlex.join(['python3', os.path.abspath(__file__), 'watch', episode]))
    for _ in range(25):                 # the pane is found by its title, which the watch loop sets
        if steps_panes(episode):
            break
        time.sleep(0.2)
    print(f'steps pane {pane} opened')
    return 0


def close_pane(episode):
    if not has_herdr():
        return 0
    panes = steps_panes(episode)
    for pane in panes:
        herdr('pane', 'close', pane)
    print(f'closed {len(panes)} steps pane(s)')
    return 0


def main(argv):
    if len(argv) == 2 and argv[1] in ('-h', '--help'):
        print(__doc__)
        return 0
    if len(argv) != 3 or argv[1] not in ('open', 'watch', 'once', 'close'):
        print(__doc__.split('\n\n')[1], file=sys.stderr)
        return 64
    episode = os.path.abspath(argv[2])
    if not os.path.isdir(episode):
        print(f'no such directory: {episode}', file=sys.stderr)
        return 66
    if argv[1] == 'once':
        print('\n'.join(render(episode, 48, color=False)))
    elif argv[1] == 'watch':
        watch(episode)
    elif argv[1] == 'open':
        return open_pane(episode)
    else:
        return close_pane(episode)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
