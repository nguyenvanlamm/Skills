import { H, ink, Ln, Rc, W } from "../draw";
import { LW } from "../rig";
import { AMBIENT, BankerLamp, FloorShadow, FramePic, Monitor, Plant, Rug, SetDef, WallClock, WALLS, Window } from "./parts";

const range = (a: number, b: number) => Array.from({ length: b - a }, (_, i) => a + i);

export const office: SetDef = {
  Draw: ({ o }) => {
    const [wall, stripe] = WALLS[o.wall ?? "green"] ?? WALLS.green;
    return (
      <>
        <rect x={-900} y={-600} width={W + 1800} height={1420} fill={wall} />
        {range(-14, 48).map((i) => (
          <line key={i} x1={i * 62} y1={-600} x2={i * 62} y2={650} {...ink(10, stripe)} />
        ))}
        <rect x={-900} y={650} width={W + 1800} height={170} fill="#4E3020" />
        {range(-5, 16).map((i) => (
          <Rc key={i} x0={i * 190 + 24} y0={676} x1={i * 190 + 170} y1={796} fill="#462A1B" w={LW * 0.6} />
        ))}
        <Ln x0={-900} y0={650} x1={W + 900} y1={650} />
        <rect x={-900} y={820} width={W + 1800} height={H + 600 - 820} fill="#6A4429" />
        {range(1, 9).map((i) => (
          <line key={i} x1={-900} y1={820 + i * i * 6.5} x2={W + 900} y2={820 + i * i * 6.5} {...ink(3, "#553520")} />
        ))}
        <Ln x0={-900} y0={820} x1={W + 900} y1={820} />
        <Window id="officewin" x0={150} y0={96} x1={800} y1={640} time={o.time} seed={o.seed ?? 5} />
        <FramePic x={990} y={190} />
        <WallClock x={1330} y={250} />
        <Rc x0={1430} y0={560} x1={1610} y1={800} fill="#7A2228" r={26} />
        <FloorShadow x0={1160} y0={1030} x1={1900} y1={1090} />
        <Rc x0={1230} y0={800} x1={1850} y1={1062} fill="#6E4426" />
        {[
          [1262, 1520],
          [1560, 1818],
        ].map(([a, b]) => (
          <g key={a}>
            <Rc x0={a} y0={836} x1={b} y1={930} fill="#7C4E2C" w={LW * 0.7} />
            <circle cx={(a + b) / 2} cy={883} r={9} fill="#D0A548" stroke="#18161B" strokeWidth={LW * 0.6} />
            <Rc x0={a} y0={956} x1={b} y1={1040} fill="#7C4E2C" w={LW * 0.7} />
            <circle cx={(a + b) / 2} cy={998} r={9} fill="#D0A548" stroke="#18161B" strokeWidth={LW * 0.6} />
          </g>
        ))}
        <Rc x0={1196} y0={770} x1={1884} y1={802} fill="#8E5C36" />
        <rect x={1250} y={773} width={580} height={9} fill="#2F6B45" />
        <BankerLamp x={1740} y={770} />
        <Monitor x={1440} y={770} />
        {[0, 1, 2].map((k) => (
          <Rc key={k} x0={1260 + k * 5} y0={752 - k * 6} x1={1380 + k * 5} y1={764 - k * 6} fill="#F7F3E8" w={LW * 0.6} />
        ))}
        <Plant x={60} y={1000} s={0.9} />
        <Rug x0={560} y0={930} x1={1360} y1={1070} />
      </>
    );
  },
  info: (o) => ({
    floor: 1024,
    ambient: AMBIENT[o.time],
    lights: [
      { kind: "pool", x: 1740, y: 720, r: 600, a: 0.95 },
      { kind: "pool", x: 1000, y: 560, r: 430, a: 0.92 },
      { kind: "oval", x: 1000, y: 1000, rx: 380, ry: 110, a: 0.7 },
      { kind: "path", d: "M 150 96 H 800 V 640 H 150 Z", a: 0.82, blur: 10 },
      { kind: "path", d: "M 190 700 L 760 700 L 1040 1090 L 330 1090 Z", a: 0.36, blur: 34 },
    ],
    bulbs: [
      { x: 1740, y: 690, r: 430, color: "#FFD98A", a: 70 },
      { x: 1740, y: 664, r: 120, color: "#FFF3C8", a: 150 },
    ],
  }),
};
