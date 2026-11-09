#!/usr/bin/env python3
"""Synthesizes the game's sound effects with the standard library only (own work, no samples).

    python3 tool/gen_sfx.py            # writes build/sfx/*.wav, then assets/audio/*.m4a via ffmpeg

Starter sounds (rename, retune or replace them; add one function per event the game needs):

step   a soft wooden tick with a little body: the player's action (a move, a placed piece)
tap    a soft click for buttons
win    three rising bell notes: the level is won
lose   a soft falling two-note: the level is lost
chime  two bell tones: a purchase arrived

Every sound is deterministic (fixed seeds) and the AAC encode is bit-exact, so re-running the script reproduces the
same files. Keep one `'id': function,` line per sound in SOUNDS: test/sfx_template_test.dart reads those lines and
checks them against `Sfx.ids` in lib/ui/sfx.dart.
"""
import math
import os
import random
import shutil
import struct
import subprocess
import sys
import wave

RATE = 44100
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WAV_DIR = os.path.join(ROOT, 'build', 'sfx')
OUT_DIR = os.path.join(ROOT, 'assets', 'audio')


# --- building blocks ---------------------------------------------------------------------------------------------


def frames(seconds):
    return int(RATE * seconds)


def envelope(t, attack, decay):
    """Linear attack, exponential decay."""
    if t < attack:
        return t / attack
    return math.exp(-(t - attack) / decay)


def noise(n, seed):
    rng = random.Random(seed)
    return [rng.uniform(-1, 1) for _ in range(n)]


def lowpass(samples, cutoff):
    """One-pole low-pass at roughly `cutoff` Hz."""
    a = math.exp(-2 * math.pi * cutoff / RATE)
    y = 0.0
    out = []
    for x in samples:
        y = (1 - a) * x + a * y
        out.append(y)
    return out


def bandpass(samples, low, high):
    """Low-pass at `high` minus low-pass at `low`: a soft band between the two."""
    return [h - l for h, l in zip(lowpass(samples, high), lowpass(samples, low))]


def fade_out(samples, seconds=0.03):
    """Ramps the tail to silence so a cut-off sound never clicks."""
    n = min(len(samples), frames(seconds))
    for k in range(n):
        samples[len(samples) - n + k] *= 1 - (k + 1) / n
    return samples


def sweep(f0, f1, dur, decay, attack=0.002, harmonics=((1, 1.0),)):
    """A tone gliding from f0 to f1 (exponentially) with a percussive envelope."""
    n = frames(dur)
    out = []
    phase = 0.0
    for i in range(n):
        t = i / RATE
        f = f0 * (f1 / f0) ** (i / n)
        phase += 2 * math.pi * f / RATE
        out.append(sum(a * math.sin(k * phase) for k, a in harmonics) * envelope(t, attack, decay))
    return fade_out(out, 0.01)


def bell(freq, dur, decay=0.45, partials=((1, 1.0), (2.76, 0.4), (5.4, 0.18), (8.93, 0.08))):
    n = frames(dur)
    return fade_out([
        sum(amp * math.sin(2 * math.pi * freq * ratio * i / RATE) * math.exp(-i / RATE / (decay / ratio**0.5))
            for ratio, amp in partials)
        * envelope(i / RATE, 0.003, 10)
        for i in range(n)
    ], 0.08)


def mix(parts, gains=None):
    """Adds (samples, offset_seconds) parts on one timeline."""
    gains = gains or [1.0] * len(parts)
    length = max(len(s) + frames(o) for s, o in parts)
    out = [0.0] * length
    for (s, o), g in zip(parts, gains):
        start = frames(o)
        for i, v in enumerate(s):
            out[start + i] += g * v
    return out


def saturate(samples, drive):
    """Soft-clips (tanh) after normalising, so a short transient carries more body for its peak."""
    top = max(abs(s) for s in samples) or 1.0
    norm = math.tanh(drive)
    return [math.tanh(drive * s / top) / norm for s in samples]


# --- the sounds ----------------------------------------------------------------------------------------------------


def step():
    n = frames(0.02)
    click = lowpass(noise(n, 11), 2400)
    click = [c * envelope(i / RATE, 0.0005, 0.004) for i, c in enumerate(click)]
    body = mix([(sweep(320, 300, 0.12, 0.03), 0), (sweep(760, 720, 0.08, 0.015), 0)], gains=[1.0, 0.4])
    return fade_out(saturate(mix([(click, 0), (body, 0)], gains=[1.6, 0.9]), 2.0), 0.02)


def tap():
    n = frames(0.012)
    click = bandpass(noise(n, 81), 1500, 7000)
    click = [c * envelope(i / RATE, 0.0004, 0.002) for i, c in enumerate(click)]
    tick = sweep(1500, 1100, 0.045, 0.008)
    return fade_out(saturate(mix([(click, 0), (tick, 0)], gains=[1.2, 0.8]), 2.0), 0.01)


def win():
    notes = [(1046.5, 0), (1318.5, 0.11), (1568.0, 0.22)]
    parts = [(bell(f, 0.9, decay=0.35), t) for f, t in notes] + [(bell(2093.0, 1.0, decay=0.4), 0.33)]
    return mix(parts, gains=[0.6, 0.6, 0.65, 0.4])


def soft_tone(freq, dur):
    """A round, slightly hollow note (a few odd harmonics), gently decaying."""
    return sweep(freq, freq * 0.985, dur, dur / 2.5, attack=0.012, harmonics=((1, 1.0), (3, 0.18), (5, 0.05)))


def lose():
    return fade_out(mix([(soft_tone(392.0, 0.26), 0), (soft_tone(311.1, 0.4), 0.2)], gains=[0.85, 1.0]), 0.06)


def chime():
    return mix([(bell(1318.5, 1.1, decay=0.45), 0), (bell(1975.5, 1.0, decay=0.4), 0.12)], gains=[0.7, 0.5])


SOUNDS = {
    'step': step,
    'tap': tap,
    'win': win,
    'lose': lose,
    'chime': chime,
}


# --- output --------------------------------------------------------------------------------------------------------


def write_wav(path, samples, peak=0.8):
    top = max(abs(s) for s in samples) or 1.0
    with wave.open(path, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(b''.join(struct.pack('<h', int(32767 * peak * s / top)) for s in samples))


def main():
    os.makedirs(WAV_DIR, exist_ok=True)
    os.makedirs(OUT_DIR, exist_ok=True)
    ffmpeg = shutil.which('ffmpeg')
    for name, make in SOUNDS.items():
        wav = os.path.join(WAV_DIR, f'{name}.wav')
        write_wav(wav, make())
        if ffmpeg:
            m4a = os.path.join(OUT_DIR, f'{name}.m4a')
            subprocess.run([
                ffmpeg, '-loglevel', 'error', '-y', '-i', wav,
                '-map_metadata', '-1', '-fflags', '+bitexact', '-flags:a', '+bitexact',
                '-c:a', 'aac', '-b:a', '96k', m4a,
            ], check=True)
        print(name, 'ok')
    if not ffmpeg:
        print('ffmpeg not found: WAVs written to build/sfx/, m4a not updated', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
