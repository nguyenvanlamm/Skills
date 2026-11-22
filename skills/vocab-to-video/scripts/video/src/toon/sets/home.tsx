import React from "react";
import { H, ink, Ln, Ov, Pg, Rc, W } from "../draw";
import { rng, shade } from "../math";
import { LW } from "../rig";
import { AMBIENT, FloorShadow, Plant, Rug, SetDef, WALLS, Window } from "./parts";

const BOOKS = ["#C8242C", "#2F6B9A", "#D0A548", "#3E9A56", "#E8E0D0", "#7A4A8A"];

const Shelf: React.FC = () => {
  const r = rng(3);
  const out: React.ReactNode[] = [];
  for (let k = 0; k < 4; k++) {
    const y = 230 + k * 150;
    out.push(<Rc key={`s${k}`} x0={140} y0={y + 128} x1={500} y1={y + 142} fill="#5A3824" w={LW * 0.6} />);
    let x = 152;
    let n = 0;
    while (x < 480) {
      const w = 22 + r() * 18;
      const h = 80 + r() * 40;
      out.push(
        <Rc key={`b${k}-${n}`} x0={x} y0={y + 128 - h} x1={x + w} y1={y + 128} fill={BOOKS[Math.floor(r() * BOOKS.length)]} w={LW * 0.5} />,
      );
      x += w + 4;
      n++;
    }
  }
  return (
    <>
      <Rc x0={120} y0={200} x1={520} y1={820} fill="#6A4428" />
      {out}
    </>
  );
};

export const home: SetDef = {
  Draw: ({ o }) => {
    const [wall, dot] = WALLS[o.wall ?? "plum"] ?? WALLS.plum;
    const dots: React.ReactNode[] = [];
    for (let i = -14; i < 48; i++) {
      for (let j = -6; j < 11; j++) {
        dots.push(<circle key={`${i}-${j}`} cx={i * 70 + (Math.abs(j) % 2) * 35} cy={j * 70} r={7} fill={dot} />);
      }
    }
    return (
      <>
        <rect x={-900} y={-600} width={W + 1800} height={1440} fill={wall} />
        {dots}
        <rect x={-900} y={760} width={W + 1800} height={80} fill={shade(wall, 0.7)} />
        <Ln x0={-900} y0={760} x1={W + 900} y1={760} />
        <rect x={-900} y={840} width={W + 1800} height={H + 600 - 840} fill="#8A5A36" />
        {Array.from({ length: 50 }, (_, i) => i - 10).map((i) => (
          <line key={i} x1={i * 120} y1={840} x2={i * 120 - 260} y2={H + 300} {...ink(3, "#764C2C")} />
        ))}
        <Ln x0={-900} y0={840} x1={W + 900} y1={840} />
        <Window id="homewin" x0={1180} y0={130} x1={1700} y1={600} time={o.time} frame="#E8E0D0" seed={o.seed ?? 8} curtains="#3F7A8C" />
        <Shelf />
        <FloorShadow x0={620} y0={1020} x1={1300} y1={1080} />
        <Rc x0={640} y0={760} x1={1280} y1={900} fill="#C2563A" r={30} />
        <Rc x0={610} y0={840} x1={700} y1={1040} fill="#C2563A" r={26} />
        <Rc x0={1220} y0={840} x1={1310} y1={1040} fill="#C2563A" r={26} />
        <Rc x0={690} y0={880} x1={1230} y1={1000} fill="#D8694A" r={20} />
        <Ln x0={960} y0={885} x1={960} y1={995} w={LW * 0.7} />
        <Ln x0={1500} y0={1040} x1={1500} y1={640} w={14} />
        <Ln x0={1500} y0={1040} x1={1500} y1={640} w={7} color="#D0A548" />
        <Ov x0={1440} y0={1030} x1={1560} y1={1052} fill="#2B2D3C" w={LW * 0.7} />
        <Pg
          pts={[
            [1430, 640],
            [1570, 640],
            [1540, 540],
            [1460, 540],
          ]}
          fill="#FFF0C8"
        />
        <Plant x={1800} y={1010} />
        <Rug x0={520} y0={980} x1={1420} y1={1120} color="#3F6E8C" />
      </>
    );
  },
  info: (o) => ({
    floor: 1030,
    ambient: AMBIENT[o.time],
    lights: [
      { kind: "pool", x: 1500, y: 640, r: 640, a: 0.95 },
      { kind: "pool", x: 960, y: 640, r: 520, a: 0.8 },
      { kind: "path", d: "M 1180 130 H 1700 V 600 H 1180 Z", a: 0.8, blur: 10 },
      { kind: "oval", x: 960, y: 1030, rx: 520, ry: 120, a: 0.6 },
    ],
    bulbs: [{ x: 1500, y: 600, r: 360, color: "#FFD98A", a: 80 }],
  }),
};
