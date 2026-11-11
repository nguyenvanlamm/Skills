#!/usr/bin/env python3
"""Steps pane: the run's stages in a herdr pane to the right of the agent, redrawn from
state.json, so the human sees at a glance which step the run is at.

  steps_pane.py open RUN     split the agent's pane to the right and watch RUN there
  steps_pane.py watch RUN    the loop that runs inside that pane
  steps_pane.py once RUN     print the block once, plain text (no herdr: paste it in the chat)
  steps_pane.py close RUN    close RUN's steps pane in this tab

RUN is a run folder (it holds state.json). `open` exits 69 when herdr is not available, after
printing the block. The pane warns when a stage is running but the state has not moved for
`panel.stall_warn_s` seconds (default 300), so a dead process does not look like a slow one.
Modelled on game-clone-pipeline/scripts/steps_pane.py. Standard library only.
"""
import json
import os
import shlex
import shutil
import subprocess
import sys
import textwrap
import time
import unicodedata

PANE_TITLE = 'remix-steps'
RULE_WIDTH = 34
STYLES = {'done': '32', 'current': '1;33', 'todo': '2', 'wait': '35', 'title': '1', 'bad': '1;31', 'warn': '33'}
MARKS = {'done': ('✓', 'done'), 'running': ('▶', 'current'), 'waiting': ('⏸', 'wait'), 'failed': ('✗', 'bad'),
         'interrupted': ('✗', 'bad'), 'todo': ('·', 'todo')}


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


def hms(seconds):
    s = int(max(0, seconds))
    return f'{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}'


def load(run):
    with open(os.path.join(run, 'state.json'), encoding='utf-8') as f:
        return json.load(f)


def stall_limit(state):
    try:
        with open(state['run'].get('config_path') or '', encoding='utf-8') as f:
            return float(json.load(f).get('panel', {}).get('stall_warn_s', 300))
    except (OSError, ValueError):
        return 300.0


def render(run, columns, color, now=None):
    """The pane's lines for RUN at `columns` cells wide."""
    now = now or time.time()
    try:
        state = load(run)
    except (OSError, ValueError):
        return [emit([('Chưa có state.json', 'todo')], columns, color), emit([(run, 'todo')], columns, color)]
    stages = state['stages']
    width = max(cell_width(s['label']) for s in stages)
    rule = '─' * min(columns, RULE_WIDTH)
    lines = [emit([(state['run'].get('title') or state['run'].get('name') or 'Remix run', 'title')], columns, color), rule]
    elapsed, running = 0.0, None
    for n, st in enumerate(stages):
        status = st['status']
        mark, style = MARKS.get(status, MARKS['todo'])
        if status == 'running':
            running = st
            elapsed += (st.get('elapsed_s_prev') or 0) + now - (st.get('started_at') or now)
        else:
            elapsed += st.get('elapsed_s') or 0
        worst = max((c['status'] for c in st.get('checks') or []), key=['SKIP', 'PASS', 'WARN', 'FAIL'].index, default='PASS')
        segments = [(f'{mark} S{n} {pad(st["label"], width)} ', style)]
        prog = st.get('progress') or {}
        if prog.get('total') and status in ('running', 'done', 'waiting', 'failed', 'interrupted'):
            segments.append((f'{prog.get("done", 0)}/{prog["total"]}', style))
        elif status == 'running' and prog.get('percent') is not None:
            segments.append((f'{prog["percent"]:.0f}%', style))
        if status == 'done' and worst == 'WARN':
            segments.append((' !', 'warn'))
        lines.append(emit(segments, columns, color))
    finished = all(st['status'] == 'done' for st in stages)
    lines.append(rule)
    if finished:
        lines.append(emit([('Xong tất cả các bước', 'done')], columns, color))
        for label, key in (('Video', 'video'), ('Thumbnail', 'thumbnail'), ('YouTube', 'youtube_md'), ('Báo cáo', 'report')):
            value = (state.get('result') or {}).get(key)
            if value:
                for part in textwrap.wrap(f'{label}: {value}', width=max(columns, 10), subsequent_indent='  ',
                                          break_long_words=True, break_on_hyphens=False):
                    lines.append(emit([(part, 'done')], columns, color))
    else:
        failed = next((st for st in stages if st['status'] in ('failed', 'interrupted')), None)
        for label, text, style in (('Đang làm', state.get('now') if running else None, 'current'),
                                   ('Chờ bạn', state.get('waiting'), 'wait'),
                                   ('Lỗi', failed and (failed.get('error') or failed['status']), 'bad')):
            if label == 'Lỗi' and not text:
                continue
            first = (text or '—').splitlines()[0]
            wrapped = textwrap.wrap(f'{label}: {first}', width=max(columns, 10), subsequent_indent='  ')
            lines.extend(emit([(part, style if text else 'todo')], columns, color) for part in wrapped[:4])
        age = now - (state.get('heartbeat') or now)
        if running and age > stall_limit(state):
            lines.append(emit([(f'⚠ Không có cập nhật từ {time.strftime("%H:%M:%S", time.localtime(state["heartbeat"]))} '
                                f'({int(age // 60)} phút): tiến trình có thể đã chết', 'bad')], columns, color))
    stamp = time.strftime('%H:%M:%S', time.localtime(state.get('heartbeat') or now))
    lines.append(emit([(f'Đã chạy {hms(elapsed)} · cập nhật {stamp}', 'todo')], columns, color))
    return lines


def watch(run):
    shown = None
    sys.stdout.write(f'\033]0;{PANE_TITLE}: {os.path.basename(run)}\007\033[?25l')
    try:
        while True:
            size = shutil.get_terminal_size()
            lines = render(run, max(size.columns, 10), color=True)
            frame = '\n'.join(lines[:size.lines])
            if frame != shown:                      # the clock and the stall warning change without a new state.json
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


def steps_panes(run):
    """Ids of RUN's steps panes in the agent's tab."""
    me = json.loads(herdr('pane', 'get', os.environ['HERDR_PANE_ID']))['result']['pane']
    title = f'{PANE_TITLE}: {os.path.basename(run)}'
    return [pane['pane_id'] for pane in json.loads(herdr('pane', 'list'))['result']['panes']
            if pane.get('tab_id') == me['tab_id']
            and (pane.get('terminal_title_stripped') or pane.get('terminal_title') or '').strip() == title]


def has_herdr():
    return bool(os.environ.get('HERDR_PANE_ID')) and shutil.which('herdr') is not None


def open_pane(run):
    if not has_herdr():
        print('\n'.join(render(run, 48, color=False)))
        print('herdr is not available: no steps pane; show these lines in the chat instead', file=sys.stderr)
        return 69
    if existing := steps_panes(run):
        print(f'steps pane {existing[0]} is already open')
        return 0
    split = json.loads(herdr('pane', 'split', os.environ['HERDR_PANE_ID'], '--direction', 'right',
                             '--ratio', '0.7', '--no-focus', '--cwd', run))['result']
    pane = (split.get('pane') or split)['pane_id']
    subprocess.run(['herdr', 'pane', 'rename', pane, PANE_TITLE], capture_output=True)
    herdr('pane', 'run', pane, shlex.join(['python3', os.path.abspath(__file__), 'watch', run]))
    print(f'steps pane {pane} opened')
    return 0


def close_pane(run):
    if not has_herdr():
        return 0
    panes = steps_panes(run)
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
    run = os.path.abspath(argv[2])
    if not os.path.isdir(run):
        print(f'no such directory: {run}', file=sys.stderr)
        return 66
    if argv[1] == 'once':
        print('\n'.join(render(run, 48, color=False)))
    elif argv[1] == 'watch':
        watch(run)
    elif argv[1] == 'open':
        return open_pane(run)
    else:
        return close_pane(run)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
