#!/usr/bin/env python3
"""Fail a pipeline game that would ship silent.

  scripts/sound_check.py REPO          # PASS/WARN/FAIL per check; exit 1 on a FAIL, 2 when REPO is no Flutter app

Run at S4 Verify, before G4 at S8, and at every Final report from S4 on. 18 of the first 25 pipeline games shipped
without a single sound because nothing checked; `templates/sound/` is the starting point that passes.

Checks (Flutter's asset rules: a directory entry in pubspec.yaml is not recursive):
  dependency   an audio plugin in pubspec.yaml (audioplayers, just_audio, flame_audio, soundpool)
  files        declared asset entries hold at least MIN_SOUNDS sound files; none is OGG/Opus/WebM (iOS AVPlayer
               cannot play them); no sound file under assets/ is left undeclared
  wiring       every id in a `static const ids = [...]` list, every value of an `enum Sound…` (its first string
               argument when it has one) and every quoted sound path in lib/ has its file
  ambient      lib/ sets AVAudioSessionCategory.ambient, or AudioContextConfig(respectSilence: true) which builds it
               (the silent switch mutes the game; the player's music keeps playing)
  switch       lib/ has a player-facing Sound switch ('Sound…', 'Mute…' or 'SFX…' text)
  credits      assets/CREDITS.md (or CREDITS.md) has a row for the sounds
  test         a test under test/ checks the sound files (mentions the audio folder or Sfx.ids)
Standard library only.
"""
import argparse
import os
import re
import sys

MIN_SOUNDS = 4
PLAYABLE = {'.m4a', '.wav', '.caf', '.mp3', '.aac', '.aif', '.aiff'}
UNPLAYABLE = {'.ogg', '.oga', '.opus', '.webm'}
PLUGINS = ('audioplayers', 'just_audio', 'flame_audio', 'soundpool')


class Report:
    def __init__(self):
        self.rows = []

    def add(self, status, place, detail):
        self.rows.append((status, place, detail))

    def ok(self, cond, place, good, bad, fail='FAIL'):
        self.add('PASS' if cond else fail, place, good if cond else bad)

    def print(self):
        width = max(len(p) for _, p, _ in self.rows)
        for status, place, detail in self.rows:
            print(f'{status:<5} {place:<{width}}  {detail}')
        count = {s: sum(1 for r in self.rows if r[0] == s) for s in ('FAIL', 'PASS', 'WARN')}
        print(f'sound_check: {count["FAIL"]} FAIL, {count["PASS"]} PASS, {count["WARN"]} WARN')
        return 1 if count['FAIL'] else 0


def read(path):
    try:
        with open(path, encoding='utf-8') as f:
            return f.read()
    except (OSError, UnicodeDecodeError):
        return ''


def dart_files(root):
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        for name in files:
            if name.endswith('.dart'):
                yield os.path.join(base, name)


def declared_assets(pubspec):
    """Entries under flutter: → assets: (strings only; the `- path: …` map form is read too)."""
    entries = []
    in_assets = False
    indent = None
    for line in pubspec.splitlines():
        if re.match(r'^\s*#', line) or not line.strip():
            continue
        m = re.match(r'^(\s*)assets:\s*$', line)
        if m and len(m.group(1)) == 2:
            in_assets, indent = True, None
            continue
        if in_assets:
            m = re.match(r'^(\s*)-\s*(?:path:\s*)?["\']?([^"\'#]+?)["\']?\s*(?:#.*)?$', line)
            lead = len(line) - len(line.lstrip())
            if m and (indent is None or lead == indent):
                indent = lead
                entries.append(m.group(2).strip())
            elif indent is not None and lead <= 2:
                in_assets = False
    return entries


def enum_sounds(code):
    """Values of `enum Sound…` declarations: the first string argument of an enhanced value, else its name."""
    names = []
    for m in re.finditer(r'\benum\s+Sound\w*\s*\{', code):
        body, depth, i = [], 0, m.end()
        while i < len(code):
            c = code[i]
            if c in '([{':
                depth += 1
            elif c in ')]}':
                if depth == 0:
                    break
                depth -= 1
            elif c == ';' and depth == 0:
                break
            body.append(c)
            i += 1
        text = re.sub(r'//[^\n]*', '', ''.join(body))
        entries, depth, cur = [], 0, ''
        for c in text:
            depth += c in '(['
            depth -= c in ')]'
            if c == ',' and depth == 0:
                entries.append(cur)
                cur = ''
            else:
                cur += c
        entries.append(cur)
        for e in entries:
            e = e.strip()
            v = re.match(r'(\w+)\s*(?:\(\s*[\'"]([\w-]+)[\'"])?', e)
            if v:
                names.append(v.group(2) or v.group(1))
    return names


def sound_ext(name):
    return os.path.splitext(name)[1].lower()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('repo')
    args = ap.parse_args()
    repo = os.path.abspath(args.repo)
    pubspec = read(os.path.join(repo, 'pubspec.yaml'))
    if 'flutter:' not in pubspec:
        print(f'sound_check: no Flutter pubspec.yaml in {repo}', file=sys.stderr)
        return 2
    r = Report()

    # dependency
    plugins = [p for p in PLUGINS if re.search(rf'^\s{{2}}{p}\s*:', pubspec, re.M)]
    r.ok(bool(plugins), 'dependency', ', '.join(plugins),
         'no audio plugin in pubspec.yaml (add `audioplayers: 6.8.1`, templates/sound/README.md)')

    # files
    entries = declared_assets(pubspec)
    declared, bad_format = [], []
    for e in entries:
        path = os.path.join(repo, e)
        if e.endswith('/') and os.path.isdir(path):
            names = [os.path.join(e, n) for n in sorted(os.listdir(path)) if os.path.isfile(os.path.join(path, n))]
        elif os.path.isfile(path):
            names = [e]
        else:
            names = []
        declared += [n for n in names if sound_ext(n) in PLAYABLE]
        bad_format += [n for n in names if sound_ext(n) in UNPLAYABLE]
    folders = sorted({os.path.dirname(n) for n in declared})
    r.ok(len(declared) >= MIN_SOUNDS, 'files',
         f'{len(declared)} sound file(s) in {", ".join(folders)}',
         f'{len(declared)} sound file(s) declared under flutter: assets: (need {MIN_SOUNDS}+; '
         'python3 tool/gen_sfx.py from templates/sound/)')
    if bad_format:
        r.add('FAIL', 'format', f'iOS cannot play {", ".join(bad_format[:4])}: re-encode as .m4a (AAC)')
    on_disk = []
    assets_dir = os.path.join(repo, 'assets')
    for base, _, files in os.walk(assets_dir):
        for name in files:
            if sound_ext(name) in PLAYABLE | UNPLAYABLE:
                on_disk.append(os.path.relpath(os.path.join(base, name), repo))
    undeclared = sorted(set(on_disk) - set(declared) - set(bad_format))
    if undeclared:
        r.add('FAIL', 'bundled', f'not declared in pubspec.yaml, so not in the app: {", ".join(undeclared[:4])}'
              + (f' … {len(undeclared) - 4} more' if len(undeclared) > 4 else ''))

    # wiring
    lib = os.path.join(repo, 'lib')
    sources = {p: read(p) for p in dart_files(lib)}
    code = '\n'.join(sources.values())
    stems = {os.path.splitext(os.path.basename(n))[0] for n in declared}
    ids = []
    for m in re.finditer(r'static\s+const\s+(?:List<String>\s+)?ids\s*=\s*(?:<String>)?\[([^\]]*)\]', code):
        ids += re.findall(r"['\"]([\w-]+)['\"]", m.group(1))
    ids += enum_sounds(code)
    paths = re.findall(r"['\"]((?:[\w-]+/)*[\w-]+\.(?:m4a|wav|caf|mp3|aac|aiff?|ogg|opus))['\"]", code)
    missing_ids = [i for i in ids if i not in stems]
    missing_paths = [p for p in paths
                     if not any(os.path.isfile(os.path.join(repo, base, p)) for base in ('assets', '', 'assets/audio'))]
    if ids or paths:
        missing = missing_ids + missing_paths
        r.ok(not missing, 'wiring', f'{len(ids)} sound id(s) and {len(paths)} path(s) in lib/ all have files',
             f'no file for {", ".join(missing[:6])}')
    else:
        r.add('WARN', 'wiring', 'no `static const ids = [...]` list, `enum Sound` or quoted sound path in lib/ to match '
              'against the files')

    # ambient
    ambient = 'AVAudioSessionCategory.ambient' in code or re.search(r'respectSilence:\s*true', code)
    r.ok(bool(ambient), 'ambient', 'iOS ambient category set',
         'lib/ never sets AVAudioSessionCategory.ambient (the silent switch would not mute the game; '
         'Sfx.audioContext in templates/sound/)')

    # switch
    switch = re.search(r"['\"](?:Sound|Sounds|Sound effects|SFX|Mute)\b[^'\"]*['\"]", code)
    r.ok(bool(switch), 'switch', f'player-facing switch {switch.group(0) if switch else ""}',
         'no Sound/Mute text in lib/: add a "Sound: On/Off" row in Settings, saved in progress')

    # credits
    credits = read(os.path.join(repo, 'assets', 'CREDITS.md')) or read(os.path.join(repo, 'CREDITS.md'))
    credit = next((l for l in credits.splitlines() if re.search(r'\b(sound|sounds|sfx|audio)\b', l, re.I)), None)
    r.ok(credit is not None, 'credits', 'CREDITS row for the sounds',
         'no sound row in assets/CREDITS.md (own synthesised sounds: name tool/gen_sfx.py)')

    # test
    marks = [f for f in folders] + ['assets/audio', 'Sfx.ids']
    tested = [os.path.relpath(p, repo) for p in dart_files(os.path.join(repo, 'test'))
              if any(m in read(p) for m in marks)]
    r.ok(bool(tested), 'test', ', '.join(tested[:3]),
         'no test checks the sound files (copy templates/sound/test/sfx_template_test.dart)')

    return r.print()


if __name__ == '__main__':
    sys.exit(main())
