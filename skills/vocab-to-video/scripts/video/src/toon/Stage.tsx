import React, { useMemo } from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";
import type { Episode, Line, Shot } from "../types";
import { actorAt, MouthShape } from "./actor";
import { Bubble, BubbleSpot } from "./Bubble";
import { H, W } from "./draw";
import { named, PopLabel, Tag } from "./fx";
import { clamp01, ease, lerp } from "./math";
import { Puppet } from "./Puppet";
import { FullLook, HEAD_CY, HEAD_R, makeLook } from "./rig";
import { SETS } from "./sets";
import { Bulb, Light, SetOpts } from "./sets/parts";
import { defaultSet, LabelSlot, layoutOf, PORTRAIT_SCALE } from "./shots";

const SHAPES: Record<string, MouthShape> = { "0": "closed", "1": "mid", "2": "open" };

const setOf = (shot: Shot) => {
  const name = shot.set && SETS[shot.set] ? shot.set : defaultSet(shot.kind);
  const time = shot.time === "dusk" || shot.time === "night" ? shot.time : "day";
  const o: SetOpts = { time, wall: shot.wall, shop: shot.shop };
  return { name, o, def: SETS[name] };
};

const hex2 = (a: number) => {
  const s = Math.round(Math.min(255, Math.max(0, a))).toString(16);
  return s.length < 2 ? "0" + s : s;
};

/** Darkness multiplied over the scene, with soft holes where the lamps and windows shine. */
const Lighting: React.FC<{ ambient: string; lights: Light[] }> = ({ ambient, lights }) => (
  <>
    <defs>
      <radialGradient id="lightpool">
        <stop offset={0} stopColor="#000" stopOpacity={1} />
        <stop offset={0.5} stopColor="#000" stopOpacity={0.75} />
        <stop offset={1} stopColor="#000" stopOpacity={0} />
      </radialGradient>
      {lights.map((l, i) =>
        l.kind === "path" ? (
          <filter key={i} id={`lightblur${i}`} filterUnits="userSpaceOnUse" x={-400} y={-300} width={W + 800} height={H + 600}>
            <feGaussianBlur stdDeviation={l.blur} />
          </filter>
        ) : null,
      )}
      <mask id="darkness" maskUnits="userSpaceOnUse" x={-900} y={-700} width={W + 1800} height={H + 1400}>
        <rect x={-900} y={-700} width={W + 1800} height={H + 1400} fill="#fff" />
        {lights.map((l, i) =>
          l.kind === "pool" ? (
            <circle key={i} cx={l.x} cy={l.y} r={l.r} fill="url(#lightpool)" opacity={l.a} />
          ) : l.kind === "oval" ? (
            <ellipse key={i} cx={l.x} cy={l.y} rx={l.rx} ry={l.ry} fill="url(#lightpool)" opacity={l.a} />
          ) : (
            <path key={i} d={l.d} fill="#000" opacity={l.a} filter={`url(#lightblur${i})`} />
          ),
        )}
      </mask>
    </defs>
    <rect
      x={-900}
      y={-700}
      width={W + 1800}
      height={H + 1400}
      fill={ambient}
      mask="url(#darkness)"
      style={{ mixBlendMode: "multiply" }}
    />
  </>
);

const Glow: React.FC<{ bulbs: Bulb[] }> = ({ bulbs }) => (
  <>
    {bulbs.map((b, i) => (
      <g key={i} style={{ mixBlendMode: "screen" }}>
        <defs>
          <radialGradient id={`bulb${i}`}>
            <stop offset={0} stopColor={b.color + hex2(b.a)} />
            <stop offset={0.5} stopColor={b.color + hex2(b.a * 0.4)} />
            <stop offset={1} stopColor={b.color + "00"} />
          </radialGradient>
        </defs>
        <circle cx={b.x} cy={b.y} r={b.r} fill={`url(#bulb${i})`} />
      </g>
    ))}
  </>
);

/**
 * The animated picture: the current shot's set, its characters, the lighting, the camera, and
 * the speech bubble of whoever is talking. `width` and `height` are the pixels the stage fills.
 * The design space is 1920x1080; a portrait frame shows a narrower, taller part of the set, so
 * there is wall or sky above the heads for the bubble.
 */
export const Stage: React.FC<{ episode: Episode; width: number; height: number; vertical: boolean }> = ({
  episode,
  width,
  height,
  vertical,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;

  const looks = useMemo(() => {
    const out: Record<string, FullLook> = {};
    for (const s of episode.speakers) out[s.id] = makeLook(episode.cast?.[s.id]);
    for (const id of Object.keys(episode.cast ?? {})) out[id] = makeLook(episode.cast[id]);
    return out;
  }, [episode.cast, episode.speakers]);
  const sides = useMemo(() => {
    const out: Record<string, "left" | "right"> = {};
    for (const s of episode.speakers) out[s.id] = s.side;
    return out;
  }, [episode.speakers]);
  const shots = useMemo<Shot[]>(
    () =>
      episode.shots && episode.shots.length
        ? [...episode.shots].sort((a, b) => a.startMs - b.startMs)
        : [
            {
              kind: "wide",
              startMs: 0,
              endMs: episode.durationMs,
              chars: episode.speakers.map((s) => ({ id: s.id })),
              beats: [],
              labels: [],
            },
          ],
    [episode.shots, episode.speakers, episode.durationMs],
  );

  let index = 0;
  for (let i = 0; i < shots.length; i++) {
    if (t * 1000 >= shots[i].startMs) index = i;
  }
  const shot = shots[index];
  const beats = useMemo(() => [...shot.beats].sort((a, b) => a.atMs - b.atMs), [shot.beats]);
  const t0 = shot.startMs / 1000;
  const t1 = Math.max(shot.endMs / 1000, t0 + 0.1);
  const { name, o, def } = setOf(shot);
  const info = def.info(o);
  const night = o.time === "night";
  const chars = shot.chars.filter((c) => looks[c.id]);
  const layout = layoutOf({ ...shot, chars }, { vertical, looks, sides, info });

  // Camera: a slow push-in over the whole shot, and a whip pan when the place changes.
  const zoom = Array.isArray(shot.zoom) && shot.zoom.length === 2 ? shot.zoom : [1, layout.zoom];
  const z = lerp(zoom[0], zoom[1], ease((t - t0) / (t1 - t0)));
  const changed = (a: Shot | undefined) => {
    if (!a) return false;
    const other = setOf(a);
    return other.name !== name || other.o.time !== o.time;
  };
  let whipX = 0;
  let whipBlur = 0;
  let whipOut = 0; // 0 -> 1 over the last frames before the picture is whipped away
  const left = Math.max(0, t1 - t) * 30;
  const into = (t - t0) * 30;
  if (changed(shots[index + 1]) && left <= 5) {
    whipX = -Math.pow(6 - left, 2) * 23; // stays inside the part of the set that is drawn
    whipBlur = (6 - left) * 16;
    whipOut = clamp01(1 - left / 5);
  } else if (changed(shots[index - 1]) && into < 4) {
    whipX = Math.pow(4 - into, 2) * 52;
    whipBlur = (4 - into) * 18;
  }
  const base = vertical ? (PORTRAIT_SCALE * width) / 1080 : Math.max(width / W, height / H);

  // Only the character whose line is being spoken moves their mouth.
  const ms = t * 1000;
  let speaking: string | null = null;
  for (const l of episode.lines) {
    if (ms >= l.startMs - 20 && ms <= l.endMs) speaking = l.speaker;
  }
  const shape = SHAPES[episode.mouth?.[frame] ?? "0"] ?? "closed";

  const actors = [...layout.actors].sort((a, b) => a.y - b.y);
  const posed = actors.map((a) => ({
    a,
    p: actorAt(a, beats, t, t0, t1, speaking === a.char.id ? shape : null, night),
  }));

  // A tracking camera keeps the walkers in the middle, as far as the set reaches.
  const focusAt = (zNow: number) => {
    if (!layout.track || !posed.length) return layout.focus[0];
    const half = width / (2 * base * zNow);
    if (half >= W / 2) return W / 2;
    const mid = posed.reduce((sum, x) => sum + x.p.x, 0) / posed.length;
    return Math.min(Math.max(mid, half), W - half);
  };
  const fx = focusAt(z);
  const camera = `translate(${width / 2 + whipX * base} ${height / 2}) scale(${base * z}) translate(${-fx} ${-layout.focus[1]})`;

  const lights: Light[] = layout.grounded
    ? [...info.lights, ...posed.map(({ a, p }): Light => ({ kind: "pool", x: p.x, y: a.y - 300 * a.s, r: 330 * a.s, a: 0.55 }))]
    : [{ kind: "pool", x: 960, y: 520, r: 900, a: 0.7 }];
  const ambient = info.ambient ? (layout.grounded || o.time !== "day" ? info.ambient : "#E8E2DA") : null;
  const bulbs: Bulb[] = layout.grounded
    ? info.bulbs
    : actors.map((a) => ({ x: a.x - (a.x > 960 ? 600 : -420), y: 380, r: 700, color: "#FFD98A", a: night ? 36 : 18 }));

  // The bubble belongs to a line of this shot: from just before it starts until the next one.
  // A line that ended before the cut never follows the picture into the next shot.
  const mine = episode.lines.filter((l) => l.endMs > shot.startMs && l.startMs < shot.endMs);
  let line: Line | null = null;
  let before: Line | null = null;
  for (const l of mine) {
    if (ms >= l.startMs - 150) {
      before = line;
      line = l;
    }
  }
  const find = (l: Line | null) => (l ? posed.find((x) => x.a.char.id === l.speaker) : undefined);
  const sideOf = (l: Line | null) => {
    const who = find(l);
    return who ? (who.a.x < 960 ? "left" : "right") : null;
  };
  const talker = find(line);
  let spot: BubbleSpot = {
    kind: "free",
    from: layout.freeBubble,
    y: layout.freeBubble === "bottom" ? 56 : vertical ? height * 0.21 : 110,
  };
  let bubbleW = vertical ? width * 0.8 : 900;
  if (talker && line) {
    // The bubble stands still while its line is on screen: it is placed from where the speaker
    // stands and how far the camera had pushed in when the line began, not from the bobbing head.
    // Only a character who walks carries it along.
    const { a, p } = talker;
    const began = Math.min(Math.max(line.startMs / 1000 - 0.15, t0), t1);
    const zThen = lerp(zoom[0], zoom[1], ease((began - t0) / (t1 - t0)));
    const fxThen = layout.track ? fx : layout.focus[0];
    const toScreen = (dx: number, dy: number): [number, number] => [
      width / 2 + (dx - fxThen) * base * zThen,
      height / 2 + (dy - layout.focus[1]) * base * zThen,
    ];
    const headY = a.y + HEAD_CY * a.s;
    if (layout.bubble === "above") {
      const [sx, sy] = toScreen(p.x, headY - (HEAD_R + 40) * a.s);
      spot = { kind: "above", x: sx, y: sy };
      bubbleW = vertical ? width * 0.8 : 840;
    } else {
      const dir = a.x < 960 ? 1 : -1;
      const [sx, sy] = toScreen(p.x + dir * HEAD_R * a.s, headY);
      spot = { kind: "side", x: sx, y: sy, dir };
      bubbleW = Math.min(720, (dir > 0 ? width - sx : sx) - 46 - 60);
    }
  }

  // A word label keeps away from the bubble. When the other character starts to speak, the
  // bubble changes sides, and a label already on screen glides across instead of jumping.
  const glide = line ? ease((ms - (line.startMs - 150)) / 350) : 1;
  const slotOf = (i: number, atMs: number): LabelSlot => {
    const sx = talker ? 0.5 + ((talker.p.x - fx) * base * z) / width : undefined;
    const now = layout.label(sideOf(line), i, sx);
    if (!line || !before || atMs >= line.startMs - 150 || glide >= 1) return now;
    const then = layout.label(sideOf(before), i);
    return { x: lerp(then.x, now.x, glide), y: lerp(then.y, now.y, glide), maxW: now.maxW };
  };
  const vr = Math.max(width, height) * 0.74;
  const unit = vertical ? width / 1080 : base;

  return (
    <div style={{ position: "relative", width, height, overflow: "hidden" }}>
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} style={{ display: "block", backgroundColor: "#0D1326" }}>
      <defs>
        <filter id="soft" filterUnits="userSpaceOnUse" x={-500} y={-800} width={W + 1000} height={H + 1600}>
          <feGaussianBlur stdDeviation={13} />
        </filter>
        <filter id="whip" x="-20%" y="0%" width="140%" height="100%">
          <feGaussianBlur stdDeviation={`${whipBlur * base} 0`} />
        </filter>
        <radialGradient id="floorshadow">
          <stop offset={0} stopColor="#000" stopOpacity={0.4} />
          <stop offset={0.6} stopColor="#000" stopOpacity={0.3} />
          <stop offset={1} stopColor="#000" stopOpacity={0} />
        </radialGradient>
        <radialGradient id="vignette" gradientUnits="userSpaceOnUse" cx={width / 2} cy={height / 2} r={vr}>
          <stop offset={0} stopColor="rgb(2,3,12)" stopOpacity={0} />
          <stop offset={0.42} stopColor="rgb(2,3,12)" stopOpacity={0} />
          <stop offset={1} stopColor="rgb(2,3,12)" stopOpacity={layout.vignette} />
        </radialGradient>
      </defs>
      <g filter={whipBlur > 0 ? "url(#whip)" : undefined}>
        <g transform={camera}>
          <g filter={layout.bg.soft ? "url(#soft)" : undefined}>
            <g transform={layout.bg.transform}>
              <def.Draw o={o} />
            </g>
          </g>
          {posed.map(({ a, p }) => (
            <g key={a.char.id}>
              {layout.grounded ? <ellipse cx={p.x} cy={a.y} rx={120 * a.s} ry={26 * a.s} fill="url(#floorshadow)" /> : null}
              <Puppet {...p} />
            </g>
          ))}
          {ambient ? <Lighting ambient={ambient} lights={lights} /> : null}
          <Glow bulbs={bulbs} />
        </g>
        {/* Labels are placed on the frame, not in the set, so the camera never moves them. */}
        <g transform={`translate(${whipX * base} 0)`}>
          {shot.labels.map((l, i) => {
            const slot = slotOf(i, l.atMs);
            return (
              <PopLabel
                key={i}
                text={l.text}
                x={slot.x * width}
                y={slot.y * height}
                u={t - l.atMs / 1000}
                rot={i % 2 ? 4 : -5}
                size={(vertical ? 100 : 104) * unit}
                maxW={slot.maxW * width}
                color={named(l.color, i % 2 ? "#FFF6DC" : "#B8F04A")}
              />
            );
          })}
        </g>
      </g>
      <rect x={0} y={0} width={width} height={height} fill="url(#vignette)" />
      {shot.tag ? (
        <Tag text={shot.tag} u={t - t0 - 0.2} x={(vertical ? 40 : 70) * unit} y={vertical ? height * 0.143 : height - 46 * unit} k={unit} />
      ) : null}
    </svg>
    {line ? (
      <Bubble line={line} t={ms} vertical={vertical} spot={spot} maxW={bubbleW} frameW={width} frameH={height} opacity={1 - whipOut} />
    ) : null}
    </div>
  );
};
