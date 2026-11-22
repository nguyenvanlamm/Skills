/** Motion maths. Everything is a pure function of time in seconds, so any frame rate works. */

export const clamp01 = (u: number) => Math.min(Math.max(u, 0), 1);
export const ease = (u: number) => 0.5 - 0.5 * Math.cos(Math.PI * clamp01(u));
export const easeOut = (u: number) => 1 - Math.pow(1 - clamp01(u), 3);

/** 0 -> 1.15 -> 1: a label or sparkle popping in. */
export const pop = (u: number) => {
  if (u <= 0) return 0;
  if (u >= 1) return 1;
  return u < 0.6 ? 1.15 * easeOut(u / 0.6) : 1.15 - 0.15 * ease((u - 0.6) / 0.4);
};

/** Snappy overshoot, used for every pose change. */
export const back = (u: number, k = 1.9) => {
  const v = clamp01(u) - 1;
  return 1 + (k + 1) * v * v * v + k * v * v;
};

export const lerp = (a: number, b: number, k: number) => a + (b - a) * k;

/** Progress 0..1 of a move that starts at t0 and lasts d seconds. */
export const K = (t: number, t0: number, d: number) => clamp01((t - t0) / d);

export const blink = (t: number, period = 2.7, phase = 0) => (t + phase) % period < 0.1;

export type Leg = [hipX: number, footDx: number, lift: number];

export const walkLegs = (phase: number, stride = 46, lift = 20): [Leg, Leg] => {
  const a = Math.sin(phase);
  return [
    [-10, a * stride, Math.max(0, Math.cos(phase)) * lift],
    [10, -a * stride, Math.max(0, -Math.cos(phase)) * lift],
  ];
};

/** Deterministic random numbers for set dressing: the same seed always draws the same set. */
export const rng = (seed: number) => {
  let s = (seed * 2654435761) >>> 0 || 1;
  return () => {
    s ^= s << 13;
    s >>>= 0;
    s ^= s >>> 17;
    s ^= s << 5;
    s >>>= 0;
    return s / 4294967296;
  };
};

const parse = (h: string): [number, number, number] => {
  const v = h.replace("#", "");
  return [parseInt(v.slice(0, 2), 16), parseInt(v.slice(2, 4), 16), parseInt(v.slice(4, 6), 16)];
};

const two = (n: number) => {
  const s = Math.round(Math.min(255, Math.max(0, n))).toString(16);
  return s.length < 2 ? "0" + s : s;
};

/** k < 1 darker, k > 1 lighter. */
export const shade = (h: string, k: number) => {
  const [r, g, b] = parse(h);
  const f = (c: number) => (k <= 1 ? c * k : c + (255 - c) * (k - 1));
  return "#" + two(f(r)) + two(f(g)) + two(f(b));
};

/** SVG arc segment on an ellipse; angles in degrees, clockwise on screen, 0 = +x. */
export const arc = (cx: number, cy: number, rx: number, ry: number, a0: number, sweep: number) => {
  const p = (a: number) => {
    const r = (a * Math.PI) / 180;
    return [cx + rx * Math.cos(r), cy + ry * Math.sin(r)];
  };
  const [sx, sy] = p(a0);
  const [ex, ey] = p(a0 + sweep);
  return {
    start: `${sx.toFixed(2)} ${sy.toFixed(2)}`,
    to: `A ${rx} ${ry} 0 ${Math.abs(sweep) > 180 ? 1 : 0} ${sweep >= 0 ? 1 : 0} ${ex.toFixed(2)} ${ey.toFixed(2)}`,
  };
};
