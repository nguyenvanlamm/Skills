import type { Shot, ShotChar } from "../types";
import type { Placed } from "./actor";
import { FullLook } from "./rig";
import { SetInfo } from "./sets/parts";

export type ShotContext = {
  /** True for a portrait frame: less of the set is visible, so characters stand closer together. */
  vertical: boolean;
  looks: Record<string, FullLook>;
  /** The side each speaker usually stands on. */
  sides: Record<string, "left" | "right">;
  info: SetInfo;
};

export type Layout = {
  actors: Placed[];
  /** Zoom reached at the end of the shot: every shot slowly pushes in. */
  zoom: number;
  /** Design-space point kept in the middle of the stage. */
  focus: [number, number];
  /** Close-ups magnify the set behind the character and soften it. */
  bg: { transform?: string; soft: boolean };
  /** Floor shadows and per-actor light pools only make sense when the feet are in frame. */
  grounded: boolean;
  vignette: number;
};

type LayoutFn = (shot: Shot, ctx: ShotContext) => Layout;

const place = (ctx: ShotContext, char: ShotChar, x: number, y: number, s: number, face: number): Placed => ({
  char,
  look: ctx.looks[char.id],
  x: char.x ?? x,
  y: char.y ?? y,
  s: char.s ?? s,
  face: char.face ?? face,
});

const spread = (n: number, vertical: boolean): number[] => {
  if (n === 1) return [vertical ? 960 : 1000];
  if (n === 2) return vertical ? [780, 1140] : [700, 1250];
  if (n === 3) return vertical ? [660, 960, 1260] : [520, 960, 1400];
  const from = vertical ? 600 : 300;
  const step = ((vertical ? 720 : 1320) / Math.max(1, n - 1)) | 0;
  return Array.from({ length: n }, (_, i) => from + i * step);
};

const wide: LayoutFn = (shot, ctx) => {
  const xs = spread(shot.chars.length, ctx.vertical);
  return {
    actors: shot.chars.map((c, i) =>
      place(ctx, c, xs[i], ctx.info.floor, 1, shot.chars.length === 1 ? -0.3 : xs[i] < 960 ? 0.7 : -0.7),
    ),
    zoom: 1.07,
    focus: [960, ctx.vertical ? 480 : 545],
    bg: { soft: false },
    grounded: true,
    vignette: 0.64,
  };
};

const walk: LayoutFn = (shot, ctx) => {
  const path: [number, number] = ctx.vertical ? [480, 1440] : [80, 1700];
  const chars = shot.chars.map((c, i) => ({
    ...c,
    walk: c.walk ?? ([path[0] - i * 270, path[1] - i * 270] as [number, number]),
  }));
  return wide({ ...shot, chars }, ctx);
};

const closeup: LayoutFn = (shot, ctx) => {
  const char = shot.chars[0];
  const side = shot.side ?? ctx.sides[char.id] ?? "left";
  const x = ctx.vertical ? 960 : side === "left" ? 840 : 1080;
  return {
    // In a portrait frame the head sits lower, which leaves room above it for a label.
    actors: [place(ctx, char, x, ctx.vertical ? 1520 : 1390, 2.15, side === "left" ? 0.72 : -0.72)],
    zoom: 1.05,
    focus: [960, ctx.vertical ? 480 : 545],
    bg: { transform: `translate(${side === "right" ? -900 : -1500} -200) scale(1.5)`, soft: true },
    grounded: false,
    vignette: 0.6,
  };
};

/** Shot kinds. A new kind is one layout function plus one line here and in rig.json. */
export const KINDS: Record<string, LayoutFn> = { wide, dialogue: wide, walk, closeup };

/** The set a shot plays in when the storyboard names none. */
export const defaultSet = (kind: string) => (kind === "walk" ? "street" : "home");
