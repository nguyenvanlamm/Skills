"""Assemble and check the upload fields for YouTube, YouTube Shorts and TikTok.

Input:  <LEVEL>/metadata.json (written by the agent, see the skill's references/publish-rules.md)
Output: <LEVEL>/out/publish.json (every field, machine-readable) and out/publish.md (copy-paste).

Chapters, the vocabulary list and the transcript are generated from the episode timeline, so they
always match the video. Nothing is uploaded.

Usage: uv run python publish.py <episodes/NAME/LEVEL>
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from common import load_config, read_json, tokens, vocab_hits, write_json

HASHTAG = re.compile(r"^#[0-9A-Za-zÀ-ÖØ-öø-ÿ_]+$")
LIMITS = {"yt_title": 100, "yt_title_ideal": 70, "yt_description": 5000, "yt_tags": 500,
          "tiktok_caption": 2200, "cover_text": 40, "thumbnail_text": 32}


def fold(text: str) -> str:
    """Lowercase and strip accents, so "Français A2" matches the suggestion "francais a2"."""
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", text.lower()) if unicodedata.category(c) != "Mn").strip()


def stamp(ms: float) -> str:
    s = int(ms // 1000)
    return f"{s // 60}:{s % 60:02d}"


def first_uses(dialogue: dict, episode: dict) -> dict[str, int]:
    """Vocabulary word -> time (ms) of its first use in the video."""
    out: dict[str, int] = {}
    for v in dialogue["vocab"]:
        for line in episode["lines"]:
            if line.get("kind") == "hook":
                continue
            marks, _ = vocab_hits(tokens(line["text"]), [v])
            if any(marks):
                out[v["word"]] = line["words"][marks.index(True)]["startMs"]
                break
    return out


def chapters(uses: dict[str, int], label: str) -> list[tuple[int, str]]:
    """YouTube chapters: start at 0:00 and stay at least 10 s apart, or YouTube ignores them."""
    out = [(0, label)]
    for word, ms in sorted(uses.items(), key=lambda kv: kv[1]):
        if ms - out[-1][0] >= 10_000:
            out.append((ms, word))
    return out


def tags_length(tags: list[str]) -> int:
    """How YouTube counts the 500-character tag budget: commas, and quotes around multi-word tags."""
    return sum(len(t) + (2 if " " in t else 0) for t in tags) + max(0, len(tags) - 1)


def check_hashtags(tags: list[str], lo: int, hi: int, where: str, problems: list[str]) -> None:
    if not lo <= len(tags) <= hi:
        problems.append(f"{where}: {len(tags)} hashtags, need {lo}-{hi}")
    for h in tags:
        if not HASHTAG.match(h):
            problems.append(f"{where}: bad hashtag {h!r} (one word, starts with #, no spaces or hyphens)")
    if len({h.lower() for h in tags}) != len(tags):
        problems.append(f"{where}: duplicate hashtags")


def build_publish(level_dir: Path, dialogue: dict, episode: dict, cfg: dict) -> tuple[list[str], list[str]]:
    problems: list[str] = []
    warnings: list[str] = []
    pcfg = cfg["publish"]
    meta_path = level_dir / "metadata.json"
    if not meta_path.is_file():
        return [f"missing {meta_path}; write it following references/publish-rules.md"], []
    meta = read_json(meta_path)
    level = dialogue["level"]
    try:
        yt, shorts, tk = meta["youtube"], meta["shorts"], meta["tiktok"]
        notes = {n["word"]: n["note"].strip() for n in meta["vocab_notes"]}
        yt_title, intro, tags, yt_hash = yt["title"].strip(), yt["intro"].strip(), yt["tags"], yt["hashtags"]
        sh_title, sh_desc, sh_hash = shorts["title"].strip(), shorts["description"].strip(), shorts["hashtags"]
        tk_caption, tk_hash, cover = tk["caption"].strip(), tk["hashtags"], tk["cover_text"].strip()
        thumb = meta["thumbnail_text"].strip()
    except (KeyError, TypeError, AttributeError) as exc:
        return [f"metadata.json: missing or malformed field {exc}"], []

    keywords = [k.lower() for k in pcfg["keywords"]]

    def has_keyword(text: str) -> bool:
        return any(k in text.lower() for k in keywords)

    # --- titles
    for name, title in (("youtube.title", yt_title), ("shorts.title", sh_title)):
        if not title:
            problems.append(f"{name} is empty")
        if len(title) > LIMITS["yt_title"]:
            problems.append(f"{name}: {len(title)} characters, limit is {LIMITS['yt_title']}")
        elif len(title) > LIMITS["yt_title_ideal"]:
            warnings.append(f"{name}: {len(title)} characters; over {LIMITS['yt_title_ideal']} is cut in search results")
        if level not in title:
            problems.append(f"{name} must contain the level {level}")
        if not has_keyword(title):
            problems.append(f"{name} must contain one of {pcfg['keywords']}")
    if yt_title.lower() == sh_title.lower():
        warnings.append("youtube.title and shorts.title are identical; give the Short its own hook")

    # --- YouTube description
    lead = intro[:150]
    if level not in lead or not has_keyword(lead):
        problems.append("youtube.intro: the first 150 characters must contain the level and a main keyword "
                        "(they are what shows in search results)")
    if len(intro) < 200:
        warnings.append(f"youtube.intro is {len(intro)} characters; aim for 250-600")
    missing = [v["word"] for v in dialogue["vocab"] if not notes.get(v["word"])]
    if missing:
        problems.append(f"vocab_notes is missing: {missing}")

    uses = first_uses(dialogue, episode)
    chaps = chapters(uses, pcfg["chapter_start_label"])
    names = {s["id"]: s["name"] for s in episode["speakers"]}
    parts = [intro, ""]
    if len(chaps) >= 3:
        parts += [pcfg["headings"]["chapters"], *[f"{stamp(ms)} {label}" for ms, label in chaps], ""]
    else:
        warnings.append("fewer than 3 chapters fit (10 s apart); the chapter block was left out")
    parts += [pcfg["headings"]["vocab"].format(level=level),
              *[f"• {v['word']} : {notes.get(v['word'], '')}" for v in dialogue["vocab"]], "",
              pcfg["headings"]["transcript"],
              *[f"{names[l['speaker']]} : {l['text']}" for l in episode["lines"] if l.get("kind") != "hook"], "",
              pcfg["footer"], "", " ".join(yt_hash)]
    description = "\n".join(parts).strip()
    if len(description) > LIMITS["yt_description"]:
        problems.append(f"YouTube description is {len(description)} characters, limit is {LIMITS['yt_description']}")

    # --- tags and hashtags
    if not 8 <= len(tags) <= 25:
        problems.append(f"youtube.tags: {len(tags)} tags, need 8-25")
    if tags_length(tags) > LIMITS["yt_tags"]:
        problems.append(f"youtube.tags use {tags_length(tags)} characters, limit is {LIMITS['yt_tags']}")
    if len({t.lower() for t in tags}) != len(tags):
        problems.append("youtube.tags contains duplicates")
    if any("," in t or "#" in t for t in tags):
        problems.append("youtube.tags: no commas or # inside a tag")
    check_hashtags(yt_hash, 3, 5, "youtube.hashtags", problems)
    check_hashtags(sh_hash, 3, 5, "shorts.hashtags", problems)
    check_hashtags(tk_hash, 3, 5, "tiktok.hashtags", problems)
    for where, hs in (("shorts", sh_hash), ("tiktok", tk_hash)):
        if any(h.lower() in ("#fyp", "#foryou", "#pourtoi", "#viral") for h in hs):
            problems.append(f"{where}.hashtags: drop #fyp-style tags; they carry no search value")

    # --- real search phrases (pipeline/keywords.py)
    kw_path = level_dir.parent / "keywords.json"
    if not kw_path.is_file():
        problems.append(f"missing {kw_path}; run keywords.py on the episode folder before writing metadata")
    else:
        known = {fold(s) for s in read_json(kw_path)["all"]}
        hits = [t for t in tags if fold(t) in known]
        if len(hits) < 5:
            problems.append(f"youtube.tags: only {len(hits)} tag(s) are real YouTube search suggestions from "
                            f"keywords.json ({hits}); use at least 5, copied as suggested")
        if not any(k in fold(yt_title) for k in known if len(k.split()) >= 3):
            warnings.append("youtube.title contains no search suggestion of 3+ words from keywords.json")

    # --- Shorts and TikTok
    shorts_description = f"{sh_desc}\n\n{' '.join(sh_hash)}"
    tiktok_caption = f"{tk_caption} {' '.join(tk_hash)}"
    if len(tiktok_caption) > LIMITS["tiktok_caption"]:
        problems.append(f"TikTok caption is {len(tiktok_caption)} characters, limit is {LIMITS['tiktok_caption']}")
    if not has_keyword(tk_caption[:100]) or level not in tk_caption[:100]:
        problems.append("tiktok.caption: the first 100 characters must contain the level and a main keyword")
    if len(cover) > LIMITS["cover_text"]:
        problems.append(f"tiktok.cover_text: {len(cover)} characters, limit is {LIMITS['cover_text']}")
    if len(thumb) > LIMITS["thumbnail_text"]:
        problems.append(f"thumbnail_text: {len(thumb)} characters, limit is {LIMITS['thumbnail_text']}")
    if level in thumb.split():
        problems.append("thumbnail_text must not contain the level; the image already has a level badge")
    for name, text in (("youtube", yt_title + description), ("shorts", sh_title + shorts_description),
                       ("tiktok", tiktok_caption)):
        if "<" in text or ">" in text:
            problems.append(f"{name}: the characters < and > are rejected by the platforms")

    if problems:
        return problems, warnings

    base = f"{level_dir.parent.name}_{level}"
    common_fields = {"language": pcfg["language"], "made_for_kids": False,
                     "category": pcfg["category"], "category_id": pcfg["category_id"]}
    result = {
        "youtube": {
            "file": f"{base}_16x9.mp4", "title": yt_title, "description": description, "tags": tags,
            "hashtags": yt_hash, "playlist": pcfg["playlist"].format(level=level),
            "thumbnail_file": f"{base}_thumbnail.jpg",
            "thumbnail_text": thumb, "chapters": [{"time": stamp(ms), "label": lb} for ms, lb in chaps],
            "audio_language": pcfg["language"], "license": "Standard YouTube License",
            "visibility": "private (set by hand when uploading)", **common_fields,
        },
        "youtube_shorts": {
            "file": f"{base}_short_9x16.mp4", "full_length_file": f"{base}_9x16.mp4", "title": sh_title, "description": shorts_description,
            "hashtags": sh_hash, "related_video": yt_title, "cover_file": f"{base}_cover.jpg", **common_fields,
        },
        "tiktok": {
            "file": f"{base}_short_9x16.mp4", "full_length_file": f"{base}_9x16.mp4", "caption": tiktok_caption, "hashtags": tk_hash,
            "cover_file": f"{base}_cover.jpg", "cover_text": cover, 
            "language": pcfg["language"],
        },
    }
    out = level_dir / "out"
    out.mkdir(exist_ok=True)
    write_json(out / "publish.json", result)
    (out / "publish.md").write_text(render_markdown(result, tags), encoding="utf-8")
    return problems, warnings


def block(text: str) -> str:
    return f"```\n{text}\n```\n"


def render_markdown(r: dict, tags: list[str]) -> str:
    y, s, t = r["youtube"], r["youtube_shorts"], r["tiktok"]
    return "\n".join([
        f"# Upload fields — {y['title']}", "",
        "## YouTube (16:9)", "",
        f"- File: `{y['file']}`",
        f"- Category: {y['category']} · Language: {y['language']} · Made for kids: no",
        f"- Playlist: {y['playlist']}",
        f"- Thumbnail: `{y['thumbnail_file']}` (1280×720)", "",
        f"**Title** ({len(y['title'])}/100)", "", block(y["title"]),
        f"**Description** ({len(y['description'])}/5000)", "", block(y["description"]),
        f"**Tags** ({tags_length(tags)}/500)", "", block(", ".join(tags)),
        "## YouTube Shorts (9:16)", "",
        f"- File: `{s['file']}` (short cut); full dialogue: `{s['full_length_file']}`",
        f"- Cover: `{s['cover_file']}` (1080×1920)",
        f"- Related video: {s['related_video']}", "",
        f"**Title** ({len(s['title'])}/100)", "", block(s["title"]),
        "**Description**", "", block(s["description"]),
        "## TikTok (9:16)", "",
        f"- File: `{t['file']}` (short cut); full dialogue: `{t['full_length_file']}`",
        f"- Cover: `{t['cover_file']}` (1080×1920), cover text to type in the app: {t['cover_text']}", "",
        f"**Caption** ({len(t['caption'])}/2200)", "", block(t["caption"]),
    ])


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    d = Path(sys.argv[1]).resolve()
    problems, warnings = build_publish(d, read_json(d / "dialogue.json"), read_json(d / "episode.json"),
                                       load_config())
    for w in warnings:
        print(f"WARN  {w}")
    for p in problems:
        print(f"FAIL  {p}")
    print("RESULT: FAIL" if problems else f"RESULT: PASS -> {d / 'out' / 'publish.md'}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
