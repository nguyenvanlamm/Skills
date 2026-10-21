#!/usr/bin/env python3
"""Find the beat grid and the sections of a music track, so a trailer can cut on the beat.

  beats.py MUSIC [--drop-at S] [--length L] [--json]

Prints bpm, beat0 (first downbeat, seconds into the track), the bar length, downbeats, sections
(low / mid / high energy, on bar lines), the rises (bars where the energy jumps) and the drop:
the biggest rise, or with --length the biggest one that leaves L seconds of track after
music.start. With --drop-at S it suggests music.start so that the drop lands S seconds into the
trailer (snapped to whole bars, so music.start is itself a downbeat).

Copy bpm, beat0 and start into trailer.json → music. The grid assumes one steady tempo, which
holds for produced background music; it is checked against the onsets (confidence).

Needs ffmpeg and numpy only: spectral-flux onsets from a numpy STFT, tempo by autocorrelation
(70–180 BPM, mild preference for ~120), then a fine search over period and phase.
"""
import argparse
import json
import subprocess
import sys

import numpy as np

SR, N_FFT, HOP = 22050, 1024, 256
# Spectral flux peaks ~12 ms before the attack it marks (measured on click tracks at 97 and
# 120 BPM); the cut should land on the attack itself.
LATENCY = 0.012


def decode(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(SR),
                          "-f", "f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32)


def spectrogram(y):
    y = np.pad(y, N_FFT // 2)
    n = 1 + (len(y) - N_FFT) // HOP
    idx = np.arange(N_FFT)[None, :] + HOP * np.arange(n)[:, None]
    return np.abs(np.fft.rfft(y[idx] * np.hanning(N_FFT), axis=1))


def onset_envelope(mag, lo_bin=0, hi_bin=None):
    s = np.log1p(100 * mag[:, lo_bin:hi_bin])
    flux = np.maximum(0, np.diff(s, axis=0)).sum(axis=1)
    flux = np.concatenate([[0], flux])
    # Remove the slow level so quiet and loud passages count alike, keep the peaks.
    win = int(0.5 * SR / HOP) | 1
    local = np.convolve(flux, np.ones(win) / win, mode="same")
    env = np.maximum(0, flux - local)
    return env / (env.max() or 1)


def sample(env, frames):
    """Linear interpolation of env at fractional frame positions (outside → 0)."""
    i = np.floor(frames).astype(int)
    f = frames - i
    ok = (i >= 0) & (i + 1 < len(env))
    out = np.zeros_like(frames, dtype=float)
    out[ok] = env[i[ok]] * (1 - f[ok]) + env[i[ok] + 1] * f[ok]
    return out


def widen(env, frames=2):
    """Max over ±frames, so an accent a few ms off the grid still counts."""
    pad = np.pad(env, frames)
    return np.max([pad[i:i + len(env)] for i in range(2 * frames + 1)], axis=0)


def tempo(env):
    fps = SR / HOP
    ac = np.correlate(env, env, mode="full")[len(env) - 1:]
    lags = np.arange(len(ac))
    lo, hi = int(fps * 60 / 180), int(fps * 60 / 70) + 1
    bpm = 60 * fps / np.maximum(lags[lo:hi], 1)
    # Log-normal prior around 120 BPM keeps the estimate off half/double tempo.
    prior = np.exp(-0.5 * (np.log2(bpm / 120) / 0.9) ** 2)
    coarse = 60 * fps / lags[lo:hi][np.argmax(ac[lo:hi] * prior)]
    # Fine search: period and phase together, scored by the onset energy on the grid.
    best = (-1, coarse, 0.0)
    for cand in np.arange(coarse * 0.97, coarse * 1.03, 0.01):
        period = 60 * fps / cand
        phases = np.arange(0, period, 0.5)
        k = np.arange(int((len(env) - phases[-1]) / period))
        score = sample(env, phases[:, None] + k[None, :] * period).sum(axis=1)
        j = int(np.argmax(score))
        if score[j] > best[0]:
            best = (score[j], cand, phases[j])
    _, bpm, phase = best
    return float(bpm), float(phase) / fps + LATENCY


def analyze(path, drop_at=None, length=None):
    y = decode(path)
    dur = len(y) / SR
    mag = spectrogram(y)
    env = onset_envelope(mag)
    bpm, beat0 = tempo(env)
    spb = 60 / bpm
    fps = SR / HOP
    beats = np.arange(beat0, dur, spb)
    on_grid = sample(widen(env), (beats - LATENCY) * fps).mean()
    confidence = float(on_grid / (env.mean() or 1))

    # Downbeat: of the 4 phases, the one where the low end (kick) hits hardest.
    low = widen(onset_envelope(mag, 0, int(200 * N_FFT / SR)))
    accent = [sample(low, (beats[p::4] - LATENCY) * fps).mean() for p in range(4)]
    first = int(np.argmax(accent))
    downbeats = beats[first::4]
    bar = 4 * spb

    # Energy per bar (RMS), scaled 0–1 between the quiet and loud ends of the track.
    rms = np.array([np.sqrt(np.mean(y[int(t * SR):int((t + bar) * SR)] ** 2) or 0)
                    for t in downbeats])
    lo_e, hi_e = np.percentile(rms, 5), np.percentile(rms, 95)
    flat = hi_e - lo_e < 0.15 * hi_e
    level = np.full(len(rms), 0.5) if flat else np.clip((rms - lo_e) / (hi_e - lo_e), 0, 1)

    # Rises: bars where the next 4 bars outweigh the previous 4 by a quarter of the range or
    # more, at least 8 bars apart. The drop is the biggest one that leaves `length` seconds.
    jumps = np.array([level[i:i + 4].mean() - level[max(0, i - 4):i].mean() if 4 <= i < len(level) - 3
                      else 0.0 for i in range(len(level))])
    rises = []
    for i in np.argsort(-jumps):
        if jumps[i] < 0.25:
            break
        if all(abs(i - j) >= 8 for j, _ in rises):
            rises.append((int(i), float(jumps[i])))
    rises.sort()
    fits = [(i, j) for i, j in rises if length is None or downbeats[i] - (drop_at or 0) + length <= dur]
    drop = float(downbeats[max(fits, key=lambda r: r[1])[0]]) if fits else None

    names = np.where(level < 0.4, "low", np.where(level < 0.75, "mid", "high"))
    sections, start = [], 0
    for i in range(1, len(names) + 1):
        if i == len(names) or names[i] != names[start]:
            sections.append({"start": round(float(downbeats[start]), 3),
                             "end": round(float(downbeats[i]) if i < len(downbeats) else dur, 3),
                             "bars": i - start, "level": str(names[start])})
            start = i
    # Merge runs shorter than 4 bars into the section before them.
    merged = []
    for s in sections:
        if merged and s["bars"] < 4:
            merged[-1]["end"], merged[-1]["bars"] = s["end"], merged[-1]["bars"] + s["bars"]
        elif merged and merged[-1]["level"] == s["level"]:
            merged[-1]["end"], merged[-1]["bars"] = s["end"], merged[-1]["bars"] + s["bars"]
        else:
            merged.append(dict(s))

    out = {"file": str(path), "duration": round(dur, 3), "bpm": round(bpm, 2),
           "beat0": round(float(downbeats[0]) if len(downbeats) else beat0, 3),
           "beat_s": round(spb, 4), "bar_s": round(bar, 4), "confidence": round(confidence, 2),
           "drop": round(drop, 3) if drop is not None else None,
           "rises": [{"t": round(float(downbeats[i]), 3), "jump": round(j, 2)} for i, j in rises],
           "sections": merged,
           "downbeats": [round(float(t), 3) for t in downbeats]}
    if drop_at is not None and drop is not None:
        start = drop - round(drop_at / bar) * bar
        while start < 0:
            start += bar
        out["start_for_drop"] = {"drop_at": round(drop - start, 3), "start": round(start, 3)}
    return out


def report(a):
    lines = [f"▸ {a['file']}  ({a['duration']:.1f}s)",
             f"  bpm {a['bpm']}  · beat {a['beat_s']}s · bar {a['bar_s']}s · beat0 (first downbeat) {a['beat0']}s"
             f"  · confidence {a['confidence']} {'(weak beat: check by ear)' if a['confidence'] < 1.5 else ''}",
             "  rises: " + (", ".join(f"{r['t']}s (+{r['jump']})" for r in a["rises"]) or "none, the energy stays level"),
             f"  drop at {a['drop']}s" if a["drop"] is not None else "  no drop that fits", "  sections:"]
    for s in a["sections"]:
        lines.append(f"    {s['start']:7.2f}–{s['end']:7.2f}s  {s['bars']:3d} bars  {s['level']}")
    if "start_for_drop" in a:
        sd = a["start_for_drop"]
        lines.append(f"  music.start {sd['start']} puts the drop at {sd['drop_at']}s into the trailer"
                     f" and leaves {a['duration'] - sd['start']:.1f}s of track")
    lines.append(f'  → trailer.json: "music": {{"bpm": {a["bpm"]}, "beat0": {a["beat0"]}, "start": '
                 f'{a.get("start_for_drop", {}).get("start", a["beat0"])}}}')
    return "\n".join(lines)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("music")
    p.add_argument("--drop-at", type=float, help="trailer second where the drop should land")
    p.add_argument("--length", type=float, help="trailer length: the drop must leave this much track")
    p.add_argument("--json", action="store_true")
    a = p.parse_args()
    res = analyze(a.music, a.drop_at, a.length)
    print(json.dumps(res, indent=2) if a.json else report(res))


if __name__ == "__main__":
    sys.exit(main())
