"""The storyboard: check it, fill it in when it is missing, and turn it into timed shots.

A storyboard is the `scenes` list of dialogue.json: each scene covers a run of lines and says
where it happens, who is in it and what they do on which word. `resolve_shots` gives every scene
its place on the audio timeline; `mouth_track` reads the voice track for the lip movement.
"""
from __future__ import annotations

import array
import math
import unicodedata
import wave
from pathlib import Path

from common import VIDEO, letters, read_json, tokens, word_variants

RIG = read_json(VIDEO / "src" / "toon" / "rig.json")  # the same lists the video code draws from
CHAR_KEYS = ("id", "x", "y", "s", "face", "pose", "emotion", "enter", "exit", "walk")
SHOT_KEYS = ("set", "time", "wall", "shop", "tag", "side", "zoom")
LONG_SHOT_MS = 17_000
SHORT_SHOT_MS = 1_200


def default_cast(cfg: dict, dialogue: dict) -> dict:
    """Every speaker's look from the config, overridden by the dialogue's own `cast`."""
    cast = {sid: dict(s.get("look") or {}) for sid, s in cfg["speakers"].items()}
    for cid, look in (dialogue.get("cast") or {}).items():
        cast[cid] = {**cast.get(cid, {}), **(look or {})}
    return cast


def auto_scenes(dialogue: dict, cfg: dict) -> list[dict]:
    """A plain storyboard for a dialogue that has none: wide shots broken up by close-ups."""
    order = sorted(cfg["speakers"], key=lambda sid: cfg["speakers"][sid].get("side") != "left")
    used = {l["speaker"] for l in dialogue["lines"]}
    chars = [{"id": sid} for sid in order if sid in used]
    lines, scenes, i, k = dialogue["lines"], [], 1, 0
    while i <= len(lines):
        end = min(len(lines), i + (1 if k % 2 == 0 else 2))
        scenes.append({"kind": "wide", "lines": [i, end], "set": "home", "time": "day",
                       "chars": [dict(c) for c in chars]})
        i, k = end + 1, k + 1
        if i <= len(lines):
            scenes.append({"kind": "closeup", "lines": [i, i], "set": "home", "time": "day",
                           "chars": [{"id": lines[i - 1]["speaker"]}]})
            i += 1
    return scenes


def _fold(word: str) -> str:
    """Letters without accents, so a cue typed `ecole` or `coeur` still finds the word."""
    w = word.replace("œ", "oe").replace("æ", "ae")
    return "".join(c for c in unicodedata.normalize("NFD", w) if unicodedata.category(c) != "Mn")


def find_all(at: str, texts: list[str]) -> list[tuple[int, int]]:
    """Every place the cue `at` (one word or a few) is said: (text number, token number).

    Three tries, the first that finds anything wins: the words as written (an elided article is
    ignored, so `école` finds `l'école` and `un an` finds `d'un an`), then without accents, then
    another form of a long word (`déménager` finds `déménagé`). A word inside another word
    (`loyer` in `employer`) never matches.
    """
    want = [letters(w) for w in str(at).split()]
    want = [w for w in want if w]
    if not want:
        return []
    keys = [[{letters(v) for v in word_variants(t)} for t in tokens(text)] for text in texts]

    def match(have: set[str], need: str, level: int) -> bool:
        if level == 0:
            return need in have
        if level == 1:
            return _fold(need) in {_fold(h) for h in have}
        stem = _fold(need)[:-2]
        return len(need) >= 7 and any(_fold(h).startswith(stem) and len(h) <= len(need) + 3 for h in have)

    for level in (0, 1, 2):
        hits = [(n, i) for n, toks in enumerate(keys) for i in range(len(toks) - len(want) + 1)
                if all(match(toks[i + k], w, level) for k, w in enumerate(want))]
        if hits:
            return hits
    return []


def find_word(at: str, texts: list[str]) -> tuple[int, int] | None:
    """The first place the cue is said, or None."""
    hits = find_all(at, texts)
    return hits[0] if hits else None


def pick_hit(at: str, lines: list[dict], who: str | None) -> tuple[tuple[int, int] | None, int]:
    """(where the cue lands, how many places it could land). A beat for `who` prefers the
    lines `who` says: a reaction named for a character goes on that character's own word."""
    hits = find_all(at, [l.get("text") or "" for l in lines])
    own = [h for h in hits if who and lines[h[0]].get("speaker") == who]
    hits = own or hits
    return (hits[0] if hits else None), len(hits)


def _is_number(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def _seconds(at: str) -> float | None:
    """The value of a "+seconds" cue, or None when it is not a plain number from 0 up."""
    try:
        v = float(at[1:])
    except ValueError:
        return None
    return v if math.isfinite(v) and v >= 0 else None


def _check_at(at, lines: list[dict], who: str | None, warn) -> str | None:
    if _is_number(at):
        return None if 0 <= at <= 1 else "a number must be a fraction of the scene between 0 and 1"
    if isinstance(at, str) and at.startswith("+"):
        return None if _seconds(at) is not None else f"{at!r} is not '+seconds' (a number from 0 up)"
    if isinstance(at, str) and at.strip():
        hit, count = pick_hit(at, lines, who)
        if not hit:
            return f"{at!r} is not said in this scene's lines"
        if count > 1:
            warn(f"{at!r} is said {count} times in this scene; the cue lands on the first. "
                 "Use more words in `at` to pick another")
        return None
    return "`at` is missing: a word of the scene, '+seconds', or a fraction"


def validate_scenes(dialogue: dict, cfg: dict) -> tuple[list[str], list[str]]:
    """Errors and warnings for `cast` and `scenes`. No `scenes` at all is allowed (see auto_scenes)."""
    errors: list[str] = []
    warnings: list[str] = []
    lines = [l if isinstance(l, dict) else {} for l in dialogue.get("lines") or []]
    if not isinstance(dialogue.get("cast") or {}, dict):
        return ["`cast` must be an object: {\"name\": {look}}"], warnings
    cast = default_cast(cfg, dialogue)
    for cid, look in cast.items():
        if not isinstance(look, dict):
            errors.append(f"cast {cid}: the look must be an object")
            cast[cid] = {}
            continue
        for key, allowed in (("outfit", "outfits"), ("hair", "hairs"), ("hat", "hats"), ("skin", "skins")):
            v = look.get(key)
            if v is not None and v is not True and v is not False and v not in RIG[allowed]:
                errors.append(f"cast {cid}: {key} {v!r} is not one of {sorted(RIG[allowed])}")
    scenes = dialogue.get("scenes")
    if scenes is None:
        warnings.append("no `scenes`: a plain storyboard will be generated (see references/scene-rules.md)")
        return errors, warnings
    if not isinstance(scenes, list) or not scenes:
        return errors + ["`scenes` must be a non-empty list"], warnings

    expect = 1
    kinds: list[str] = []
    hook_speaker = (dialogue.get("hook") or {}).get("speaker") if isinstance(dialogue.get("hook"), dict) else None
    for n, sc in enumerate(scenes, 1):
        where = f"scene {n}"
        if not isinstance(sc, dict):
            errors.append(f"{where}: must be an object")
            continue
        kind = sc.get("kind")
        kinds.append(kind)
        if kind not in RIG["kinds"]:
            errors.append(f"{where}: kind {kind!r} is not one of {RIG['kinds']}")
        rng = sc.get("lines")
        if not (isinstance(rng, list) and len(rng) == 2 and all(type(v) is int for v in rng)
                and 1 <= rng[0] <= rng[1] <= len(lines)):
            errors.append(f"{where}: `lines` must be [from, to] with 1 <= from <= to <= {len(lines)}")
            continue
        if rng[0] != expect:
            errors.append(f"{where}: starts at line {rng[0]}, but line {expect} is the next one not yet covered; "
                          "scenes must cover every line once, in order")
        expect = rng[1] + 1
        if rng[1] - rng[0] + 1 > 3:
            warnings.append(f"{where}: covers {rng[1] - rng[0] + 1} lines; one picture for that long feels static")
        for key, allowed in (("set", "sets"), ("time", "times"), ("wall", "walls")):
            if sc.get(key) is not None and sc[key] not in RIG[allowed]:
                errors.append(f"{where}: {key} {sc[key]!r} is not one of {RIG[allowed]}")
        if sc.get("side") not in (None, "left", "right"):
            errors.append(f"{where}: side must be 'left' or 'right'")
        for key in ("shop", "tag"):
            if sc.get(key) is not None and not isinstance(sc[key], str):
                errors.append(f"{where}: {key} must be text")
        zoom = sc.get("zoom")
        if zoom is not None and not (isinstance(zoom, list) and len(zoom) == 2
                                     and all(_is_number(v) and 0.5 <= v <= 2 for v in zoom)):
            errors.append(f"{where}: zoom must be [from, to], each between 0.5 and 2 (1 = the whole set)")

        chars = sc.get("chars")
        if not isinstance(chars, list) or not chars or not all(isinstance(c, dict) for c in chars):
            errors.append(f"{where}: `chars` must list at least one character, each as {{\"id\": ...}}")
            continue
        ids = [c.get("id") for c in chars]
        if len(set(map(str, ids))) != len(ids):
            errors.append(f"{where}: a character is listed twice in `chars`")
        for c in chars:
            if c.get("id") not in cast:
                errors.append(f"{where}: unknown character {c.get('id')!r} (cast is {sorted(cast)})")
            if c.get("pose") is not None and c["pose"] not in RIG["poses"]:
                errors.append(f"{where}: pose {c['pose']!r} is not one of {sorted(RIG['poses'])}")
            if c.get("emotion") is not None and c["emotion"] not in RIG["emotions"]:
                errors.append(f"{where}: emotion {c['emotion']!r} is not one of {sorted(RIG['emotions'])}")
            for key in ("enter", "exit"):
                if c.get(key) not in (None, "left", "right"):
                    errors.append(f"{where}: {key} must be 'left' or 'right'")
            for key, lo, hi in (("x", -400, 2320), ("y", 0, 2400), ("s", 0.2, 4), ("face", -1, 1)):
                if c.get(key) is not None and not (_is_number(c[key]) and lo <= c[key] <= hi):
                    errors.append(f"{where}: {key} of {c.get('id')!r} must be a number from {lo} to {hi}")
            walk = c.get("walk")
            if walk is not None and not (isinstance(walk, list) and len(walk) == 2 and all(_is_number(v) for v in walk)):
                errors.append(f"{where}: walk must be [from_x, to_x]")
        if kind == "closeup" and len(chars) != 1:
            errors.append(f"{where}: a closeup shows exactly one character")
        mine = lines[rng[0] - 1:rng[1]]
        speakers = {l.get("speaker") for l in mine}
        if not speakers & set(ids):
            warnings.append(f"{where}: nobody in the picture speaks in lines {rng[0]}-{rng[1]}")
        if n == 1:
            late = next((c for c in chars if c.get("id") == hook_speaker and c.get("enter")), None)
            if late:
                warnings.append(f"{where}: {hook_speaker!r} says the hook but is still walking in; "
                                "the first frames show a bubble with nobody under it. Let the other character enter")

        def has_hat(cid) -> bool:
            return (cast.get(cid) or {}).get("hat") not in (None, False, "none")

        for c in chars:
            if c.get("pose") == "tiphat" and not has_hat(c.get("id")):
                warnings.append(f"{where}: {c.get('id')!r} has no hat to tip; give them one in `cast` or use another pose")

        beats = sc.get("beats") or []
        labels = sc.get("labels") or []
        if not isinstance(beats, list) or not all(isinstance(b, dict) for b in beats):
            errors.append(f"{where}: `beats` must be a list of objects")
            beats = []
        if not isinstance(labels, list) or not all(isinstance(b, dict) for b in labels):
            errors.append(f"{where}: `labels` must be a list of objects")
            labels = []
        for b in beats:
            who = b.get("who")
            problem = _check_at(b.get("at"), mine, who, lambda w: warnings.append(f"{where}: beat: {w}"))
            if problem:
                errors.append(f"{where}: beat: {problem}")
            if who is not None and who not in ids:
                errors.append(f"{where}: beat for {who!r}, who is not in this scene")
            if b.get("pose") is not None and b["pose"] not in RIG["poses"]:
                errors.append(f"{where}: beat pose {b['pose']!r} is not one of {sorted(RIG['poses'])}")
            if b.get("emotion") is not None and b["emotion"] not in RIG["emotions"]:
                errors.append(f"{where}: beat emotion {b['emotion']!r} is not one of {sorted(RIG['emotions'])}")
            if b.get("face") is not None and not (_is_number(b["face"]) and -1 <= b["face"] <= 1):
                errors.append(f"{where}: beat face must be a number from -1 to 1")
            if not any(k in b for k in ("pose", "emotion", "face")):
                errors.append(f"{where}: a beat must change pose, emotion or face")
            if b.get("pose") == "tiphat" and not has_hat(who or ids[0]):
                warnings.append(f"{where}: beat pose 'tiphat' on a character with no hat")
            if who is None and not problem and isinstance(b.get("at"), str) and not b["at"].startswith("+"):
                hit, _ = pick_hit(b["at"], mine, None)
                said_by = mine[hit[0]].get("speaker") if hit else None
                if said_by not in ids:
                    warnings.append(f"{where}: beat at {b['at']!r} has no `who`, and {said_by!r}, who says it, "
                                    f"is not in the picture; it goes to {ids[0]!r}. Add `who` to make that clear")
        for lab in labels:
            if not isinstance(lab.get("text"), str) or not lab["text"].strip():
                errors.append(f"{where}: a label needs `text`")
            problem = _check_at(lab.get("at"), mine, None, lambda w: warnings.append(f"{where}: label: {w}"))
            if problem:
                errors.append(f"{where}: label: {problem}")
        if len(labels) > 1:
            warnings.append(f"{where}: {len(labels)} labels; they stack and crowd the picture, one per scene reads best")
    if expect != len(lines) + 1 and not any("must be [from, to]" in e or "must be an object" in e for e in errors):
        errors.append(f"scenes stop at line {expect - 1}; the dialogue has {len(lines)} lines")
    for i in range(2, len(kinds)):
        if kinds[i] == kinds[i - 1] == kinds[i - 2]:
            warnings.append(f"scenes {i - 1}-{i + 1} are all {kinds[i]!r}; vary the shots")
            break
    return errors, warnings


def _gesture(text: str, n: int, toward: str) -> dict:
    """What a speaker does when the storyboard gives them nothing: a small talking gesture."""
    stripped = text.rstrip()
    if stripped.endswith("?"):
        return {"pose": toward, "emotion": "smile"}
    if stripped.endswith("!"):
        return {"pose": "celebrate" if len(tokens(text)) <= 3 else "explain", "emotion": "smile"}
    return {"pose": ("explain", toward, "hips")[n % 3], "emotion": "neutral"}


def resolve_shots(dialogue: dict, cfg: dict, lines_out: list[dict], indices: list[int], duration_ms: int,
                  log=print) -> list[dict]:
    """Scenes -> shots with start and end times, for the lines that are in this timeline.

    `indices[i]` is the dialogue line number of `lines_out[i]` (0 = the opening hook, which joins
    the first shot). A scene none of whose lines are in the timeline (the short cut) is dropped.
    """
    scenes = dialogue.get("scenes") or auto_scenes(dialogue, cfg)
    sides = {sid: s.get("side", "left") for sid, s in cfg["speakers"].items()}
    picked = []
    for sc in scenes:
        a, b = sc["lines"]
        members = [j for j, idx in enumerate(indices) if a <= idx <= b]
        if members:
            picked.append((sc, members))
    if not picked:
        return []
    hook = [j for j, idx in enumerate(indices) if idx == 0]
    picked[0] = (picked[0][0], hook + picked[0][1])

    starts = []
    for n, (_, members) in enumerate(picked):
        first = members[0]
        if n == 0 or first == 0:
            starts.append(0)
            continue
        s0, e = lines_out[first]["startMs"], lines_out[first - 1]["endMs"]
        starts.append(round(s0 - 30 if s0 - e < 100 else max((e + s0) / 2, s0 - 350)))

    shots = []
    for n, (sc, members) in enumerate(picked):
        start = starts[n]
        end = starts[n + 1] if n + 1 < len(picked) else duration_ms
        mine = [lines_out[j] for j in members]
        ids = [c["id"] for c in sc["chars"]]
        # A cue is looked up in the whole scene, as the validator did, and only then placed on
        # the timeline: in the short cut a word of a line that was cut away is dropped, never
        # moved to a similar word of a line that stayed. Cues never land on the hook.
        first = sc["lines"][0]
        scene_lines = dialogue["lines"][first - 1:sc["lines"][1]]
        placed = {indices[j]: lines_out[j] for j in members if indices[j] != 0}

        def cue(at, who=None) -> tuple[int, str | None] | None:
            if _is_number(at):
                return round(start + at * (end - start)), None
            if isinstance(at, str) and at.startswith("+"):
                sec = _seconds(at)
                if sec is None:
                    return None
                if start + sec * 1000 >= end:
                    log(f"  WARN scene {scenes.index(sc) + 1}: cue {at!r} is after the end of its "
                        f"{(end - start) / 1000:.1f}s shot; moved to the end")
                return round(min(start + sec * 1000, max(start, end - 300))), None
            hit, _ = pick_hit(at, scene_lines, who) if isinstance(at, str) else (None, 0)
            line = placed.get(first + hit[0]) if hit else None
            if not line:
                return None  # the word belongs to a line that is not in this timeline
            return line["words"][hit[1]]["startMs"], line["speaker"]

        beats = []
        for b in sc.get("beats") or []:
            got = cue(b.get("at"), b.get("who"))
            if not got:
                continue
            who = b.get("who") or (got[1] if got[1] in ids else ids[0])
            beats.append({"atMs": got[0], "who": who, **{k: b[k] for k in ("pose", "emotion", "face") if k in b}})

        # Characters the storyboard leaves alone still gesture when they speak and rest when they listen.
        directed = {b["who"] for b in beats} | {c["id"] for c in sc["chars"] if "pose" in c or "emotion" in c}
        for j, line in zip(members, mine):
            for cid in ids:
                if cid in directed:
                    continue
                if cid == line["speaker"]:
                    toward = "present" if sides.get(cid, "left") == "left" else "present_left"
                    beats.append({"atMs": line["startMs"], "who": cid, **_gesture(line["text"], j, toward)})
                else:
                    beats.append({"atMs": line["startMs"], "who": cid, "pose": "idle", "emotion": "neutral"})

        labels = []
        for lab in sc.get("labels") or []:
            got = cue(lab.get("at"))
            if got:
                labels.append({"text": lab["text"], "atMs": got[0], **({"color": lab["color"]} if lab.get("color") else {})})

        shot = {"kind": sc["kind"], "startMs": start, "endMs": end,
                **{k: sc[k] for k in SHOT_KEYS if sc.get(k) is not None},
                "chars": [{k: c[k] for k in CHAR_KEYS if k in c} for c in sc["chars"]],
                "beats": sorted(beats, key=lambda b: b["atMs"]), "labels": labels}
        if end - start > LONG_SHOT_MS:
            log(f"  WARN shot {n + 1} ({sc['kind']}, lines {sc['lines'][0]}-{sc['lines'][1]}) lasts "
                f"{(end - start) / 1000:.1f}s; split the scene")
        if end - start < SHORT_SHOT_MS:
            log(f"  WARN shot {n + 1} ({sc['kind']}, lines {sc['lines'][0]}-{sc['lines'][1]}) lasts only "
                f"{(end - start) / 1000:.1f}s; join it with a neighbour")
        shots.append(shot)
    return shots


def mouth_track(wav: Path, fps: int, duration_ms: int, lines: list[dict] | None = None) -> str:
    """One character per video frame: 0 mouth closed, 1 half open, 2 open, from how loud the voice is.

    Loudness is judged against the line being spoken (`lines`, with startMs/endMs), not against
    the whole track: a quiet voice opens its mouth as wide as a loud one.
    """
    with wave.open(str(wav)) as w:
        rate, channels = w.getframerate(), w.getnchannels()
        if w.getsampwidth() != 2:
            raise RuntimeError(f"{wav}: expected 16-bit audio")
        pcm = array.array("h")
        pcm.frombytes(w.readframes(w.getnframes()))
    step = 4  # every fourth sample of the first channel is plenty for loudness
    mono = pcm[::channels * step]
    hop = rate / step / fps
    frames = max(1, math.ceil(duration_ms / 1000 * fps))
    rms = []
    for f in range(frames):
        chunk = mono[round(f * hop):round((f + 1) * hop)]
        rms.append(math.sqrt(sum(v * v for v in chunk) / len(chunk)) if chunk else 0.0)

    def peak(values: list[float]) -> float:
        loud = sorted(v for v in values if v > 0)
        return loud[min(len(loud) - 1, int(len(loud) * 0.97))] if loud else 0.0

    overall = peak(rms) or 1.0
    tops = [overall] * frames
    for line in lines or []:
        a = max(0, int(line["startMs"] / 1000 * fps))
        b = min(frames, math.ceil(line["endMs"] / 1000 * fps) + 1)
        top = peak(rms[a:b])
        if top > 0.1 * overall:  # a near-silent line keeps the track's scale, so noise opens no mouth
            tops[a:b] = [top] * (b - a)
    hold_min = max(1, round(fps / 10))  # a mouth shape lasts at least a tenth of a second
    out, cur, held = [], "0", hold_min
    for v, top in zip(rms, tops):
        target = "2" if v > 0.45 * top else "1" if v > 0.14 * top else "0"
        if target != cur and held >= hold_min:
            cur, held = target, 0
        held += 1
        out.append(cur)
    return "".join(out)
