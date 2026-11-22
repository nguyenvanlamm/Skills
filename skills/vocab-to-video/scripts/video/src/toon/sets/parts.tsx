import React from "react";
import { rng, shade } from "../math";
import { INK, LW } from "../rig";
import { Ci, H, ink, Ln, Ov, Pg, Rc, W } from "../draw";

export type Time = "day" | "dusk" | "night";

export type Light =
  | { kind: "pool"; x: number; y: number; r: number; a: number }
  | { kind: "oval"; x: number; y: number; rx: number; ry: number; a: number }
  | { kind: "path"; d: string; a: number; blur: number };

/** A lamp's glow, added on top of the lighting: a is 0..255. */
export type Bulb = { x: number; y: number; r: number; color: string; a: number };

export type SetOpts = { time: Time; wall?: string; shop?: string; seed?: number };

export type SetInfo = { floor: number; ambient: string | null; lights: Light[]; bulbs: Bulb[] };

export type SetDef = { Draw: React.FC<{ o: SetOpts }>; info: (o: SetOpts) => SetInfo };

export const AMBIENT: Record<Time, string> = { night: "#4C5CA0", dusk: "#9C7FA6", day: "#F2EEE8" };

export const WALLS: Record<string, [string, string]> = {
  green: ["#2F5449", "#2A4C42"],
  blue: ["#2E3E66", "#283759"],
  plum: ["#4A2F52", "#412948"],
  teal: ["#22545A", "#1E4A50"],
  sand: ["#C9A97A", "#B9986A"],
  grey: ["#4A4E5A", "#41454F"],
  cream: ["#E8DCC0", "#DACDAE"],
  brick: ["#8A4A3A", "#7A3F31"],
};

const SKY: Record<Time, [string, string]> = {
  night: ["#0A1136", "#24338A"],
  dusk: ["#3A2A6A", "#F09A6A"],
  day: ["#5FB2EE", "#CDEBFA"],
};

export const Sky: React.FC<{ id: string; time: Time; h?: number; x0?: number; x1?: number }> = ({
  id,
  time,
  h = 860,
  x0 = -2000,
  x1 = W + 2000,
}) => (
  <>
    <defs>
      <linearGradient id={id} gradientUnits="userSpaceOnUse" x1={0} y1={0} x2={0} y2={h}>
        <stop offset={0} stopColor={SKY[time][0]} />
        <stop offset={1} stopColor={SKY[time][1]} />
      </linearGradient>
    </defs>
    <rect x={x0} y={-1500} width={x1 - x0} height={H + 3000} fill={`url(#${id})`} />
  </>
);

const starRand = rng(7);
const STARS = Array.from({ length: 130 }, () => ({
  x: -300 + starRand() * (W + 600),
  y: -200 + starRand() * 960,
  r: [1.6, 2.0, 2.6, 3.2][Math.floor(starRand() * 4)],
  a: (150 + 90 * Math.sin(starRand() * 6)) / 255,
}));

export const Stars: React.FC = () => (
  <>
    {STARS.map((s, i) => (
      <circle key={i} cx={s.x} cy={s.y} r={s.r} fill="#E8ECFF" opacity={s.a} />
    ))}
  </>
);

export const Moon: React.FC<{ x: number; y: number; r?: number }> = ({ x, y, r = 50 }) => (
  <>
    {[
      [3.0, 16],
      [2.2, 22],
      [1.55, 30],
    ].map(([k, a]) => (
      <circle key={k} cx={x} cy={y} r={r * k} fill="#C9D4FF" opacity={a / 255} />
    ))}
    <circle cx={x} cy={y} r={r} fill="#F3EDD3" />
    <circle cx={x - r * 0.3} cy={y - r * 0.25} r={r * 0.16} fill="#D9D2B4" />
    <circle cx={x + r * 0.25} cy={y + r * 0.3} r={r * 0.22} fill="#DDD6B8" />
  </>
);

export const Sun: React.FC<{ x: number; y: number; r?: number }> = ({ x, y, r = 60 }) => (
  <>
    {[
      [3.2, 20],
      [2.2, 34],
      [1.5, 60],
    ].map(([k, a]) => (
      <circle key={k} cx={x} cy={y} r={r * k} fill="#FFF3B0" opacity={a / 255} />
    ))}
    <Ci x={x} y={y} r={r} fill="#FFE27A" w={LW * 0.8} />
  </>
);

export const Cloud: React.FC<{ x: number; y: number; s: number; color?: string; opacity?: number }> = ({
  x,
  y,
  s,
  color = "#2C3B80",
  opacity = 1,
}) => (
  <g fill={color} opacity={opacity}>
    {[
      [-70, 8, 34],
      [-30, -14, 46],
      [22, -6, 40],
      [64, 10, 30],
    ].map(([dx, dy, r], i) => (
      <circle key={i} cx={x + dx * s} cy={y + dy * s} r={r * s} />
    ))}
    <rect x={x - 100 * s} y={y + 8 * s} width={192 * s} height={32 * s} />
  </g>
);

const BLOCK: Record<Time, [string, string, string]> = {
  night: ["#1C2658", "#131A42", "#263272"],
  dusk: ["#5A4070", "#3E2C55", "#6E5288"],
  day: ["#D9C6A5", "#9E6B4A", "#8FB5D0"],
};

/** One building with a grid of windows, some of them lit at night. */
export const Block: React.FC<{
  x: number;
  w: number;
  h: number;
  base: number;
  seed: number;
  time: Time;
  lit?: number;
  lw?: number;
}> = ({ x, w, h, base, seed, time, lit = 0.4, lw = LW }) => {
  const r = rng(seed);
  const top = base - h;
  const pal = BLOCK[time];
  const body = time === "day" ? [pal[0], "#C7B08F", "#B8C4CF", "#D7A98A"][seed % 4] : pal[0];
  const cols = Math.max(2, Math.floor((w - 30) / 46));
  const rows = Math.floor((h - 30) / 62);
  const gap = (w - cols * 22) / (cols + 1);
  const panes: React.ReactNode[] = [];
  for (let j = 0; j < rows; j++) {
    for (let i = 0; i < cols; i++) {
      const wx = x + gap + i * (22 + gap);
      const wy = top + 26 + j * 62;
      const on = r() < lit && time !== "day";
      if (on) {
        panes.push(<rect key={`g${i}-${j}`} x={wx - 8} y={wy - 8} width={38} height={52} rx={8} fill="#FFD98A" opacity={0.13} />);
      }
      panes.push(<Rc key={`${i}-${j}`} x0={wx} y0={wy} x1={wx + 22} y1={wy + 36} fill={on ? "#F2D88C" : pal[2]} w={lw * 0.5} />);
    }
  }
  return (
    <>
      <Rc x0={x} y0={top} x1={x + w} y1={base + 600} fill={body} w={lw} />
      <Pg
        pts={[
          [x - 8, top],
          [x + 16, top - 40],
          [x + w - 16, top - 40],
          [x + w + 8, top],
        ]}
        fill={pal[1]}
        w={lw}
      />
      {panes}
    </>
  );
};

/** A row of flat, far-away buildings. */
export const FarCity: React.FC<{ base: number; time: Time; seed?: number }> = ({ base, time, seed = 3 }) => {
  const v = { night: "#1A2560", dusk: "#5C4A7E", day: "#9DB8D2" }[time];
  const r = rng(seed);
  const out: React.ReactNode[] = [];
  let x = -400;
  let n = 0;
  while (x < W + 400) {
    const w = 90 + r() * 110;
    const h = 120 + r() * 140;
    out.push(<rect key={`b${n}`} x={x} y={base - h} width={w} height={h + 300} fill={v} />);
    out.push(<rect key={`t${n}`} x={x + 10} y={base - h - 26} width={w - 20} height={26} fill={v} />);
    if (time !== "day") {
      for (let j = 0; j < Math.floor(h / 50); j++) {
        for (let i = 0; i < Math.floor(w / 40); i++) {
          if (r() < 0.3) {
            out.push(
              <rect key={`w${n}-${i}-${j}`} x={x + 12 + i * 40} y={base - h + 16 + j * 50} width={12} height={20} fill="#E9CF86" opacity={0.78} />,
            );
          }
        }
      }
    }
    x += w + (-6 + r() * 16);
    n++;
  }
  return <>{out}</>;
};

/** A framed window with a city view; `id` must be unique in the set. */
export const Window: React.FC<{
  id: string;
  x0: number;
  y0: number;
  x1: number;
  y1: number;
  time: Time;
  frame?: string;
  seed?: number;
  curtains?: string;
}> = ({ id, x0, y0, x1, y1, time, frame = "#3B2416", seed = 5, curtains = "#93222B" }) => {
  const w = x1 - x0;
  const mx = (x0 + x1) / 2;
  const my = y0 + (y1 - y0) * 0.38;
  return (
    <>
      <defs>
        <clipPath id={id}>
          <rect x={x0} y={y0} width={w} height={y1 - y0} />
        </clipPath>
      </defs>
      <g clipPath={`url(#${id})`}>
        <Sky id={`${id}sky`} time={time} h={y1} x0={x0} x1={x1} />
        {time === "night" ? (
          <>
            <Stars />
            <Moon x={x0 + 100} y={y0 + 84} r={30} />
          </>
        ) : null}
        {time === "day" ? (
          <>
            <Sun x={x1 - 120} y={y0 + 100} r={40} />
            <Cloud x={x0 + 230} y={y0 + 150} s={0.7} color="#FFFFFF" opacity={0.9} />
          </>
        ) : null}
        <g transform={`translate(${x0} ${y0 + 160}) scale(0.5)`}>
          <FarCity base={800} time={time} seed={seed} />
        </g>
        {[
          [0.0, 0.23, 0.28],
          [0.26, 0.2, 0.4],
          [0.62, 0.22, 0.33],
          [0.86, 0.2, 0.46],
        ].map(([fx, fw, fh], k) => (
          <Block key={k} x={x0 + fx * w} w={fw * w} h={fh * (y1 - y0)} base={y1} seed={seed * 10 + k} time={time} lw={LW * 0.7} />
        ))}
        {[0, 1].map((k) => {
          const px = x0 + 100 + k * 150;
          return (
            <Pg
              key={k}
              pts={[
                [px, y0],
                [px + 60 - k * 30, y0],
                [px - 130 - k * 30, y1],
                [px - 190, y1],
              ]}
              fill="#FFFFFF"
              w={0}
              opacity={0.06}
            />
          );
        })}
      </g>
      <Rc x0={x0 - 22} y0={y0 - 22} x1={x1 + 22} y1={y0} fill={frame} w={LW * 0.8} />
      <Rc x0={x0 - 22} y0={y1} x1={x1 + 22} y1={y1 + 22} fill={frame} w={LW * 0.8} />
      <Rc x0={x0 - 22} y0={y0} x1={x0} y1={y1} fill={frame} w={LW * 0.8} />
      <Rc x0={x1} y0={y0} x1={x1 + 22} y1={y1} fill={frame} w={LW * 0.8} />
      <Ln x0={mx} y0={y0} x1={mx} y1={y1} w={14} />
      <Ln x0={mx} y0={y0} x1={mx} y1={y1} w={7} color={frame} />
      <Ln x0={x0} y0={my} x1={x1} y1={my} w={14} />
      <Ln x0={x0} y0={my} x1={x1} y1={my} w={7} color={frame} />
      <Rc x0={x0 - 44} y0={y1 + 22} x1={x1 + 44} y1={y1 + 48} fill={shade(frame, 1.3)} w={LW * 0.8} />
      {curtains ? (
        <>
          <Ln x0={x0 - 110} y0={y0 - 36} x1={x1 + 110} y1={y0 - 36} w={12} />
          <Ln x0={x0 - 110} y0={y0 - 36} x1={x1 + 110} y1={y0 - 36} w={6} color="#C9A04A" />
          {[
            [x0 - 96, x0 - 14],
            [x1 + 14, x1 + 96],
          ].map(([c0, c1], i) => (
            <g key={i}>
              <Pg
                pts={[
                  [c0, y0 - 36],
                  [c1, y0 - 36],
                  [c1 + 8, y1 + 60],
                  [c0 - 10, y1 + 60],
                ]}
                fill={curtains}
              />
              {[1, 2, 3].map((k) => (
                <Ln
                  key={k}
                  x0={c0 + (k * (c1 - c0)) / 4}
                  y0={y0 - 30}
                  x1={c0 - 6 + (k * (c1 - c0 + 14)) / 4}
                  y1={y1 + 54}
                  w={4}
                  color={shade(curtains, 0.75)}
                />
              ))}
            </g>
          ))}
        </>
      ) : null}
    </>
  );
};

export const WallClock: React.FC<{ x: number; y: number; r?: number }> = ({ x, y, r = 62 }) => (
  <>
    <Ci x={x} y={y} r={r} fill="#F4EFE2" />
    <Ln x0={x} y0={y} x1={x} y1={y - r * 0.68} w={LW * 0.8} />
    <Ln x0={x} y0={y} x1={x + r * 0.45} y1={y + r * 0.2} w={LW * 0.8} />
    <circle cx={x} cy={y} r={5} fill={INK} />
  </>
);

export const FramePic: React.FC<{ x: number; y: number; w?: number; h?: number }> = ({ x, y, w = 170, h = 210 }) => (
  <>
    <Rc x0={x} y0={y} x1={x + w} y1={y + h} fill="#C39A45" />
    <Rc x0={x + 18} y0={y + 18} x1={x + w - 18} y1={y + h - 18} fill="#EFE6CE" w={LW * 0.6} />
    <Pg
      pts={[
        [x + 26, y + h - 28],
        [x + 60, y + h - 100],
        [x + 86, y + h - 60],
        [x + 114, y + h - 120],
        [x + w - 26, y + h - 28],
      ]}
      fill="#9DB7A6"
      w={LW * 0.5}
    />
    <circle cx={x + w - 58} cy={y + 54} r={13} fill="#E9B44C" />
  </>
);

export const BankerLamp: React.FC<{ x: number; y: number }> = ({ x, y }) => (
  <>
    <Ov x0={x - 58} y0={y - 16} x1={x + 58} y1={y + 6} fill="#D0A548" w={LW * 0.8} />
    <Ln x0={x} y0={y - 8} x1={x} y1={y - 118} w={12} />
    <Ln x0={x} y0={y - 8} x1={x} y1={y - 118} w={6} color="#E3BC5C" />
    <path
      d={`M ${x - 116} ${y - 112} C ${x - 96} ${y - 196} ${x + 96} ${y - 196} ${x + 116} ${y - 112} Z`}
      fill="#2FA25E"
      stroke={INK}
      strokeWidth={LW}
      strokeLinejoin="round"
    />
    <path d={`M ${x - 82} ${y - 138} Q ${x - 50} ${y - 172} ${x - 4} ${y - 174}`} {...ink(7, "#8FE0AE")} />
    <Ov x0={x - 104} y0={y - 122} x1={x + 104} y1={y - 100} fill="#FFF3B8" w={LW * 0.7} />
  </>
);

export const Monitor: React.FC<{ x: number; y: number }> = ({ x, y }) => (
  <>
    <Rc x0={x - 20} y0={y - 70} x1={x + 20} y1={y} fill="#3A3A46" w={LW * 0.8} />
    <Rc x0={x - 70} y0={y - 10} x1={x + 70} y1={y + 4} fill="#3A3A46" w={LW * 0.8} />
    <Rc x0={x - 170} y0={y - 260} x1={x + 170} y1={y - 60} fill="#2A2A34" r={10} />
    <Rc x0={x - 150} y0={y - 244} x1={x + 150} y1={y - 78} fill="#7FD0FF" w={LW * 0.6} r={4} />
    {[0, 1, 2, 3, 4].map((i) => (
      <rect key={i} x={x - 130} y={y - 220 + i * 28} width={((180 - i * 23) % 240) + 40} height={12} fill="#FFFFFF" opacity={0.59} />
    ))}
  </>
);

export const Plant: React.FC<{ x: number; y: number; s?: number }> = ({ x, y, s = 1 }) => (
  <>
    <Pg
      pts={[
        [x - 46 * s, y - 90 * s],
        [x + 46 * s, y - 90 * s],
        [x + 34 * s, y],
        [x - 34 * s, y],
      ]}
      fill="#B5653A"
    />
    {[-70, -35, 0, 30, 60].map((a) => {
      const d = `M ${x} ${y - 90 * s} Q ${x + a * 1.2 * s} ${y - 250 * s} ${x + a * 2.6 * s} ${y - (280 - Math.abs(a)) * s}`;
      return (
        <g key={a}>
          <path d={d} {...ink(24 * s)} />
          <path d={d} {...ink(13 * s, "#3E9A56")} />
        </g>
      );
    })}
  </>
);

export const Rug: React.FC<{ x0: number; y0: number; x1: number; y1: number; color?: string }> = ({
  x0,
  y0,
  x1,
  y1,
  color = "#7E2A30",
}) => (
  <>
    <Ov x0={x0} y0={y0} x1={x1} y1={y1} fill={color} w={LW * 0.8} />
    <ellipse cx={(x0 + x1) / 2} cy={(y0 + y1) / 2} rx={(x1 - x0) / 2 - 40} ry={(y1 - y0) / 2 - 14} {...ink(6, "#C39A45")} />
  </>
);

export const StreetLamp: React.FC<{ x: number; base: number; top: number }> = ({ x, base, top }) => (
  <>
    <Ln x0={x} y0={base} x1={x} y1={top} w={22} />
    <Ln x0={x} y0={base} x1={x} y1={top} w={11} color="#2B2D3C" />
    <Rc x0={x - 22} y0={base - 26} x1={x + 22} y1={base + 4} fill="#2B2D3C" w={LW * 0.8} />
    <Pg
      pts={[
        [x - 40, top + 4],
        [x + 40, top + 4],
        [x + 26, top - 72],
        [x - 26, top - 72],
      ]}
      fill="#FFF0B4"
    />
    <Pg
      pts={[
        [x - 48, top - 72],
        [x + 48, top - 72],
        [x, top - 112],
      ]}
      fill="#2B2D3C"
    />
  </>
);

/** Soft shadow under furniture (a flat ellipse, no blur filter). */
export const FloorShadow: React.FC<{ x0: number; y0: number; x1: number; y1: number }> = ({ x0, y0, x1, y1 }) => (
  <ellipse cx={(x0 + x1) / 2} cy={(y0 + y1) / 2} rx={(x1 - x0) / 2} ry={(y1 - y0) / 2} fill="#000000" opacity={0.2} />
);
