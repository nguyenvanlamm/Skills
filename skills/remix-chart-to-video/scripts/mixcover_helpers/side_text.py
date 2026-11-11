"""Draw the video background of the "visualizer" look: the AI picture with a column at the side
away from the DJ, holding a title (`video.side_title`) above the song list (one line per song in
playing order: `01  Title`, no artist, no time).

The title is a slanted poster block in Anton, a condensed display face: upper case, each line
scaled to fill the column's width, lines alternating white and lime, each with a solid pink copy
offset behind it. The list uses m10-mixcover's track and number fonts and its colours.

Runs under m10-mixcover's venv, not the skill's Python: it needs Pillow and reads the fonts and
the colours from m10-mixcover's preset. It lives in a folder of its own so that nothing next to
it can shadow a module Pillow or mixcover imports.

    side_text.py SPEC_JSON
    SPEC: {repo, preset, raw, out, size, side, column_width, title, title_font, tracks,
           title_min_px, track_max_px, track_min_px}

`side` is where the column goes ("right" when the DJ stands left). It is `column_width` of the
frame wide, inside the preset's `layout.margin`; the skill sets that width so the spectrum ring
cannot reach it. The song list gets the largest row size from `track_max_px` down to
`track_min_px` that still leaves the title room with no line below `title_min_px`. The title's
words are then broken into the lines whose smallest line is largest within that room. A song
title too long for the column is cut with "…".

Prints one JSON object: whether it all fits, the sizes, the title's lines, how many song titles
were cut, the lowest contrast of the list against its background, the column and the ink box.
"""
from __future__ import annotations

import json
import sys
from functools import lru_cache
from itertools import combinations
from pathlib import Path

SLANT = 0.18             # title: italic slant, sideways shift per pixel of height (about 10 degrees)
SHADOW = 0.06            # title: offset of the solid pink copy behind each line, in that line's size
LINE_GAP = 0.12          # title: space between the ink of two lines, in the lower line's size
MAX_RATIO = 1.4          # title: no line larger than this times the smallest, so the block holds together
MAX_LINES = 4
MAX_TITLE_SIZE_H = 0.20  # title: largest font size, as a share of the height
MAX_TITLE_BLOCK_H = 0.45 # title: largest share of the height it may take
ROW_PITCH = 1.75         # list: baseline to baseline, in row sizes
NUMBER_SCALE = 0.86      # list: the number's size against the song title's
NUMBER_GAP = 0.7         # list: space between number and song title, in row sizes
TITLE_LIST_GAP = 1.5     # space between the title and the list, in row sizes
PANEL_OPACITY = 0.70     # the dark gradient behind the column (raised until the list reads)
PANEL_MAX = 0.90
PANEL_FADE = 0.16        # width of its fade towards the DJ (share of the width)
MIN_CONTRAST = 4.5       # WCAG AA for normal text


def partitions(words: list[str], most: int):
    """Every way to break the words into at most `most` lines, keeping their order."""
    n = len(words)
    for k in range(min(n, most)):
        for cuts in combinations(range(1, n), k):
            bounds = (0, *cuts, n)
            yield tuple(' '.join(words[a:b]) for a, b in zip(bounds, bounds[1:]))


def main() -> int:
    spec = json.loads(sys.argv[1])
    sys.path.insert(0, spec['repo'])
    from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps
    from mixcover.fonts import resolve
    from mixcover.preset import Preset

    preset = Preset.load(spec['preset'])
    W, H = spec['size']
    margin = round(float(preset.get('layout.margin')) * H)
    col_w = round(float(spec['column_width']) * W)
    x0 = W - margin - col_w if spec['side'] == 'right' else margin       # the column
    x1 = x0 + col_w
    f_title = str(spec['title_font'])
    f_track, f_num = (str(resolve(preset.get(k))) for k in ('fonts.track', 'fonts.number'))
    white, lime = preset.color('secondary'), preset.color('primary')
    pink, panel = preset.color('accent'), preset.color('panel')

    title = ' '.join(str(spec.get('title') or '').split()).upper()
    words = title.split(' ') if title else []
    tracks = [' '.join(str(t).split()) for t in spec.get('tracks') or []]
    n = len(tracks)
    cap = round(MAX_TITLE_SIZE_H * H)

    def width(font, text: str) -> int:
        b = font.getbbox(text, anchor='ls')
        return b[2] - b[0]

    # -- the title ---------------------------------------------------------------------------
    @lru_cache(maxsize=None)
    def line_ink(text: str, size: int):
        """One title line, white on black, slanted, cropped to its ink."""
        font = ImageFont.truetype(f_title, size)
        b = font.getbbox(text, anchor='ls')
        canvas = Image.new('L', (b[2] - b[0] + 2 * size, round(size * 2.8)))
        ImageDraw.Draw(canvas).text((size - b[0], 1.8 * size), text, font=font, fill=255, anchor='ls')
        m = canvas.crop(canvas.getbbox())
        extra = round(SLANT * m.height)
        return m.transform((m.width + extra, m.height), Image.Transform.AFFINE, (1, SLANT, -extra, 0, 1, 0),
                           Image.Resampling.BICUBIC)

    def offset(size: int) -> int:
        return max(1, round(SHADOW * size))

    @lru_cache(maxsize=None)
    def fill_size(text: str) -> int:
        """The size at which a line, with its shadow, fills the column's width (at most `cap`)."""
        lo, hi = 1, cap
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if line_ink(text, mid).width + offset(mid) <= col_w:
                lo = mid
            else:
                hi = mid - 1
        return lo

    def block(lines: tuple[str, ...]):
        sizes = [fill_size(line) for line in lines]
        smallest = min(sizes)
        sizes = [min(s, round(MAX_RATIO * smallest)) for s in sizes]
        masks = [line_ink(line, s) for line, s in zip(lines, sizes)]
        gaps = [round(LINE_GAP * s) for s in sizes[1:]]
        height = sum(m.height for m in masks) + sum(gaps) + offset(sizes[-1])
        return smallest, sizes, masks, gaps, height

    def best_title(room: float):
        """The line breaks whose smallest line is largest while the block fits `room`; fewer
        lines win a tie. None when no break keeps every line at `title_min_px` or more."""
        best = None
        for lines in partitions(words, MAX_LINES):
            smallest, sizes, masks, gaps, height = block(lines)
            if height > room or smallest < int(spec['title_min_px']):
                continue
            key = (smallest, -len(lines))
            if best is None or key > best[0]:
                best = (key, lines, sizes, masks, gaps, height)
        return best

    # -- the list ----------------------------------------------------------------------------
    def rows(t: int):
        ft, fn = ImageFont.truetype(f_track, t), ImageFont.truetype(f_num, max(1, round(t * NUMBER_SCALE)))
        nums = [f'{i:02d}' for i in range(1, n + 1)]
        num_w = max((width(fn, s) for s in nums), default=0)
        room = col_w - num_w - NUMBER_GAP * t
        shown, cut = [], 0
        for name in tracks:
            s = name
            if width(ft, s) > room:
                cut += 1
                while s and width(ft, s.rstrip() + '…') > room:
                    s = s[:-1]
                s = s.rstrip() + '…'
            shown.append(s)
        asc = max((-ft.getbbox(s, anchor='ls')[1] for s in shown), default=t)
        desc = max((ft.getbbox(s, anchor='ls')[3] for s in shown), default=0)
        height = (n - 1) * ROW_PITCH * t + asc + desc if n else 0
        return ft, fn, nums, num_w, shown, cut, asc, height

    avail = H - 2 * margin
    t_max, t_min = int(spec['track_max_px']), max(1, int(spec['track_min_px']))
    plan = None
    for t in range(t_max, t_min - 1, -1):              # the largest rows that leave the title its room
        r = rows(t)
        gap = TITLE_LIST_GAP * t if n and words else 0
        room = min(MAX_TITLE_BLOCK_H * H, avail - r[-1] - gap)
        head = best_title(room) if words and room > 0 else None
        if words and head is None:
            continue
        plan = (True, t, r, gap, head)
        break
    if plan is None:                                   # nothing fits: smallest rows, the title on one line per word
        t = t_min
        r = rows(t)
        gap = TITLE_LIST_GAP * t if n and words else 0
        lines = tuple(words[:MAX_LINES - 1] + [' '.join(words[MAX_LINES - 1:])]) if len(words) > MAX_LINES else tuple(words)
        head = ((0, 0), lines, *block(lines)[1:]) if words else None
        plan = (False, t, r, gap, head)
    fits, t, (ft, fn, nums, num_w, shown, cut, asc, list_h), gap, head = plan
    _, lines, sizes, masks, gaps, title_h = head if head else (None, (), [], [], [], 0)

    top = max(margin, round((H - (title_h + gap + list_h)) / 2))
    list_top = top + title_h + gap

    # -- the background, with a dark gradient on the column side --------------------------
    raw = spec.get('raw')
    if raw and Path(raw).is_file():
        base = ImageOps.fit(Image.open(raw).convert('RGB'), (W, H), Image.Resampling.LANCZOS)
    else:
        base = Image.new('RGB', (W, H), preset.color('background'))
    full = W - margin - col_w                           # drawn for the right side, mirrored for the left
    start = full - PANEL_FADE * W
    shape = [min(1.0, max(0.0, (x - start) / (full - start))) for x in range(W)]

    def shaded(opacity: float):
        ramp = Image.new('L', (W, 1))
        ramp.putdata([round(255 * opacity * v) for v in shape])
        shade = ramp.resize((W, H))
        if spec['side'] == 'left':
            shade = ImageOps.mirror(shade)
        return Image.composite(Image.new('RGB', (W, H), panel), base, shade)

    def lum(rgb) -> float:
        lin = [(c / 255) / 12.92 if c / 255 <= 0.04045 else ((c / 255 + 0.055) / 1.055) ** 2.4 for c in rgb]
        return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]

    def contrast(img) -> float | None:
        """Lime numbers (the darker of the two text colours) against the 95th-percentile
        brightest background in the list's box."""
        if not n:
            return None
        hist = img.crop((x0, list_top, x1, round(list_top + list_h))).convert('L').histogram()
        total, seen, p95 = sum(hist), 0, 255
        for v, count in enumerate(hist):
            seen += count
            if seen >= 0.95 * total:
                p95 = v
                break
        return (lum(lime) + 0.05) / (lum((p95, p95, p95)) + 0.05)

    opacity = PANEL_OPACITY
    img = shaded(opacity)
    low = contrast(img)
    while low is not None and low < MIN_CONTRAST and opacity < PANEL_MAX:
        opacity = min(PANEL_MAX, opacity + 0.05)
        img = shaded(opacity)
        low = contrast(img)

    # -- the title: slanted lines, white and lime in turn, a solid pink copy behind each -------
    box = [x1, H, x0, 0]
    y = top
    for i, (mask, size) in enumerate(zip(masks, sizes)):
        o = offset(size)
        img.paste(Image.new('RGB', mask.size, pink), (x0 + o, y + o), mask)
        img.paste(Image.new('RGB', mask.size, white if i % 2 == 0 else lime), (x0, y), mask)
        box = [min(box[0], x0), min(box[1], y), max(box[2], x0 + mask.width + o), max(box[3], y + mask.height + o)]
        y += mask.height + (gaps[i] if i < len(gaps) else 0)

    # -- the list: lime numbers, white song titles, a soft shadow ------------------------------
    if n:
        name_x = x0 + num_w + NUMBER_GAP * t
        shadow = Image.new('L', (W, H))
        sd = ImageDraw.Draw(shadow)
        off = max(1, round(t * 0.06))
        for i, (num, name) in enumerate(zip(nums, shown)):
            y = list_top + asc + i * ROW_PITCH * t
            sd.text((x0 + off, y + off), num, font=fn, fill=255, anchor='ls')
            sd.text((name_x + off, y + off), name, font=ft, fill=255, anchor='ls')
        shadow = shadow.filter(ImageFilter.GaussianBlur(max(1, t * 0.08))).point(lambda v: round(v * 0.75))
        img = Image.composite(Image.new('RGB', (W, H), (0, 0, 0)), img, shadow)
        draw = ImageDraw.Draw(img)
        for i, (num, name) in enumerate(zip(nums, shown)):
            y = list_top + asc + i * ROW_PITCH * t
            draw.text((x0, y), num, font=fn, fill=lime, anchor='ls')
            draw.text((name_x, y), name, font=ft, fill=white, anchor='ls')
            right = name_x + width(ft, name)
            box = [min(box[0], x0), min(box[1], round(y - asc)), max(box[2], round(right)), max(box[3], round(y + 0.3 * t))]

    Path(spec['out']).parent.mkdir(parents=True, exist_ok=True)
    img.save(spec['out'])
    print(json.dumps({'ok': True, 'fits': fits, 'title_px': min(sizes) if sizes else 0, 'title_sizes': sizes,
                      'title_lines': list(lines), 'title_font': Path(f_title).name, 'track_px': t, 'tracks': n,
                      'cut': cut, 'contrast': round(low, 2) if low is not None else None,
                      'panel_opacity': round(opacity, 2), 'column': [x0, x1], 'box': box,
                      'side': spec['side']}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
