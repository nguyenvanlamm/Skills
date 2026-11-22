import React from "react";
import { fitSize, H, Hand, Ln, Pg, Rc, W } from "../draw";
import { rng, shade } from "../math";
import { INK, LW } from "../rig";
import { AMBIENT, Block, Cloud, FarCity, Moon, SetDef, Sky, Stars, StreetLamp, Sun } from "./parts";

const CONE = "M 520 300 L 600 300 L 1050 1080 L 290 1080 Z";

export const street: SetDef = {
  Draw: ({ o }) => {
    const time = o.time;
    const day = time === "day";
    const shop = o.shop ?? "CAFÉ";
    const [pav, road] = day ? ["#B8B2A8", "#8C8A90"] : ["#444B70", "#30365A"];
    const r = rng(4);
    const cobbles: React.ReactNode[] = [];
    for (let row = 0; row < 7; row++) {
      const yy = 856 + row * 36 + row * row * 1.5;
      const wd = 84 + row * 8;
      for (let kx = -6; kx < 32; kx++) {
        const xx = kx * (wd + 10) + ((row % 2) * wd) / 2 - 100;
        cobbles.push(
          <rect key={`${row}-${kx}`} x={xx} y={yy} width={wd} height={24 + row * 2} rx={10} fill={shade(road, r() < 0.7 ? 1.12 : 1.25)} />,
        );
      }
    }
    return (
      <>
        <Sky id={`streetsky${time}`} time={time} h={760} />
        {time === "night" ? (
          <>
            <Stars />
            <Moon x={1500} y={150} r={36} />
            <Cloud x={700} y={220} s={1} />
          </>
        ) : day ? (
          <>
            <Sun x={1560} y={160} />
            <Cloud x={500} y={210} s={1.2} color="#FFFFFF" opacity={0.92} />
            <Cloud x={1200} y={300} s={0.9} color="#FFFFFF" opacity={0.86} />
          </>
        ) : (
          <Cloud x={700} y={260} s={1.1} color="#E58A7A" />
        )}
        <FarCity base={660} time={time} seed={8} />
        {[
          [-90, 300, 500, 21],
          [210, 240, 410, 22],
          [1660, 250, 400, 24],
          [1900, 260, 470, 25],
        ].map(([x, w, h, sd]) => (
          <Block key={sd} x={x} w={w} h={h} base={760} seed={sd} time={time} lit={0.34} />
        ))}
        <Rc x0={1090} y0={470} x1={1660} y1={760} fill={day ? "#B9876A" : "#4A3550"} />
        <Rc x0={1140} y0={560} x1={1380} y1={720} fill={day ? "#BFE3F2" : "#F6DE96"} />
        <Ln x0={1260} y0={560} x1={1260} y1={720} w={LW * 0.7} />
        <Rc x0={1440} y0={540} x1={1580} y1={760} fill="#6A4428" />
        <circle cx={1558} cy={660} r={7} fill="#D0A548" stroke={INK} strokeWidth={LW * 0.5} />
        <defs>
          <clipPath id="awning">
            <polygon points="1070,470 1680,470 1710,540 1040,540" />
          </clipPath>
        </defs>
        <polygon points="1070,470 1680,470 1710,540 1040,540" fill="#C8242C" />
        <g clipPath="url(#awning)">
          {[0, 2, 4, 6, 8, 10, 12].map((i) => (
            <Pg
              key={i}
              pts={[
                [1070 + i * 46, 470],
                [1116 + i * 46, 470],
                [1092 + i * 48, 540],
                [1044 + i * 48, 540],
              ]}
              fill="#F4EFE2"
              w={0}
            />
          ))}
        </g>
        <polygon points="1070,470 1680,470 1710,540 1040,540" fill="none" stroke={INK} strokeWidth={LW} strokeLinejoin="round" />
        <Hand text={shop} x={1375} y={452} size={fitSize(shop, 60, 520)} color="#F6DE96" align="middle" stroke={8} skew={-0.1} />
        <rect x={-900} y={760} width={W + 1800} height={80} fill={pav} />
        <Ln x0={-900} y0={760} x1={W + 900} y1={760} />
        <rect x={-900} y={840} width={W + 1800} height={H + 600 - 840} fill={road} />
        <Ln x0={-900} y0={840} x1={W + 900} y1={840} />
        {cobbles}
        <StreetLamp x={560} base={842} top={330} />
      </>
    );
  },
  info: (o) => ({
    floor: 1000,
    ambient: o.time === "night" ? "#5A69B6" : AMBIENT[o.time],
    lights: [
      { kind: "path", d: CONE, a: 0.92, blur: 24 },
      { kind: "oval", x: 690, y: 1000, rx: 520, ry: 120, a: 0.85 },
      { kind: "pool", x: 1260, y: 640, r: 380, a: 0.9 },
      { kind: "pool", x: 960, y: 560, r: 420, a: 0.5 },
    ],
    bulbs: [
      { x: 560, y: 290, r: 130, color: "#FFF0B4", a: 170 },
      { x: 1260, y: 640, r: 360, color: "#FFD98A", a: 44 },
    ],
  }),
};
