import { H, Ln, W } from "../draw";
import { rng, shade } from "../math";
import { SetDef } from "./parts";

const PAPER = "#F3E6C8";
const speckRand = rng(11);
const SPECKS = Array.from({ length: 150 }, () => ({
  x: -200 + speckRand() * (W + 400),
  y: -100 + speckRand() * (H + 200),
  r: 1.5 + speckRand() * 3,
  a: (40 + speckRand() * 70) / 255,
}));

/** Plain cream paper with a floor line: for a line that needs no place. */
export const voidSet: SetDef = {
  Draw: () => (
    <>
      <defs>
        <radialGradient id="paper" gradientUnits="userSpaceOnUse" cx={960} cy={520} r={1400}>
          <stop offset={0} stopColor={shade(PAPER, 1.08)} />
          <stop offset={0.55} stopColor={PAPER} />
          <stop offset={1} stopColor={shade(PAPER, 0.8)} />
        </radialGradient>
      </defs>
      <rect x={-900} y={-700} width={W + 1800} height={H + 1400} fill="url(#paper)" />
      {SPECKS.map((s, i) => (
        <circle key={i} cx={s.x} cy={s.y} r={s.r} fill={shade(PAPER, 0.7)} opacity={s.a * 0.6} />
      ))}
      <rect x={-900} y={1010} width={W + 1800} height={H + 700 - 1010} fill={shade(PAPER, 0.82)} />
      <Ln x0={-900} y0={1010} x1={W + 900} y1={1010} />
    </>
  ),
  info: () => ({ floor: 1010, ambient: null, lights: [], bulbs: [] }),
};
