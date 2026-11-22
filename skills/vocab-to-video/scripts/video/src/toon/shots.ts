import type { Shot, ShotChar } from "../types";
import type { Placed } from "./actor";
import { ease, lerp } from "./math";
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

/** Where a word label goes, in frame fractions (0-1), so it never depends on the camera. */
export type LabelSlot = { x: number; y: number; maxW: number };

export type Layout = {
  actors: Placed[];
  /** Zoom reached at the end of the shot: every shot slowly pushes in. */
  zoom: number;
  /** Design-space point kept in the middle of the stage. */
  focus: [number, number];
  /** True when the camera follows the characters sideways (a walk in a frame narrower than the set). */
  track: boolean;
  /** Close-ups magnify the set behind the character and soften it. */
  bg: { transform?: string; soft: boolean };
  /** Floor shadows and per-actor light pools only make sense when the feet are in frame. */
  grounded: boolean;
  vignette: number;
  /** The bubble sits over the speaker's head, or beside it when the head fills the frame. */
  bubble: "above" | "side";
  /** Where a bubble with no speaker in the picture goes. */
  freeBubble: "top" | "bottom";
  /**
   * The slot of label number i, given which half of the frame the speaker is in (null: nobody
   * in the picture speaks) and where across the frame the speaker is right now (0-1).
   * A layout puts it where neither the bubble nor the title can be.
   */
  label: (speakerSide: "left" | "right" | null, i: number, speakerX?: number) => LabelSlot;
};

type LayoutFn = (shot: Shot, ctx: ShotContext) => Layout;

/** How much of the design space a portrait frame shows per pixel; landscape shows all of it. */
export const PORTRAIT_SCALE = 1.35;

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
  if (n === 3) return vertical ? [700, 960, 1220] : [520, 960, 1400];
  const from = vertical ? 640 : 300;
  const step = ((vertical ? 640 : 1320) / Math.max(1, n - 1)) | 0;
  return Array.from({ length: n }, (_, i) => from + i * step);
};

/** The point of the set a frame is centred on: a portrait frame looks a little lower. */
const focusOf = (ctx: ShotContext): [number, number] => [960, ctx.vertical ? ctx.info.floor - 445 : 545];

const wide: LayoutFn = (shot, ctx) => {
  const xs = spread(shot.chars.length, ctx.vertical);
  return {
    actors: shot.chars.map((c, i) =>
      place(ctx, c, xs[i], ctx.info.floor, 1, shot.chars.length === 1 ? -0.3 : xs[i] < 960 ? 0.7 : -0.7),
    ),
    zoom: 1.07,
    focus: focusOf(ctx),
    track: false,
    bg: { soft: false },
    grounded: true,
    vignette: 0.64,
    bubble: "above",
    freeBubble: "top",
    // Over the listener, at the height of the bubble; a portrait frame has free sky under the title.
    label: (side, i) =>
      ctx.vertical
        ? { x: 0.5, y: 0.19 + i * 0.062, maxW: 0.8 }
        : side === null
          ? { x: 0.14, y: 0.3 + i * 0.12, maxW: 0.24 } // beside the bubble that hangs from the top
          : { x: side === "left" ? 0.78 : 0.22, y: 0.3 + i * 0.12, maxW: 0.33 },
  };
};

const walk: LayoutFn = (shot, ctx) => {
  // Left to right, the first character in front. A portrait frame is narrower than the path,
  // so there the camera follows the walkers (`track`).
  const [from, to, gap] = ctx.vertical ? [550, 1670, 300] : [460, 1730, 270];
  const chars = shot.chars.map((c, i) => ({
    ...c,
    walk: c.walk ?? ([from - i * gap, to - i * gap] as [number, number]),
  }));
  const base = wide({ ...shot, chars }, ctx);
  return {
    ...base,
    track: true,
    // The walkers stay close together and cross the frame, so the label keeps to the far edge
    // and changes edge once, in a quick glide, when the speaker passes the middle.
    label: (side, i, sx = 0.5) =>
      ctx.vertical
        ? base.label(side, i)
        : { x: lerp(0.85, 0.15, ease((sx - 0.49) / 0.02)), y: 0.3 + i * 0.12, maxW: 0.24 },
  };
};

const closeup: LayoutFn = (shot, ctx) => {
  const char = shot.chars[0];
  const side = shot.side ?? ctx.sides[char.id] ?? "left";
  const x = ctx.vertical ? 960 : side === "left" ? 840 : 1080;
  const focus = focusOf(ctx);
  return {
    // In a portrait frame the head sits lower, which leaves room above it for a label.
    actors: [place(ctx, char, x, ctx.vertical ? focus[1] + 1040 : 1390, 2.15, side === "left" ? 0.72 : -0.72)],
    zoom: 1.05,
    focus,
    track: false,
    bg: { transform: `translate(${side === "right" ? -900 : -1500} -200) scale(1.5)`, soft: true },
    grounded: false,
    vignette: 0.6,
    bubble: ctx.vertical ? "above" : "side",
    freeBubble: ctx.vertical ? "top" : "bottom",
    // Landscape: behind the character's back, the side the bubble never uses.
    label: (_side, i) =>
      ctx.vertical
        ? { x: 0.5, y: 0.19 + i * 0.062, maxW: 0.8 }
        : { x: x < 960 ? 0.15 : 0.85, y: 0.3 + i * 0.13, maxW: 0.24 },
  };
};

/**
 * Shot kinds. A new kind is one layout function plus one line here and in rig.json: the layout
 * says where the actors, the bubble and the labels go, and the stage asks no more about the kind.
 */
export const KINDS: Record<string, LayoutFn> = { wide, dialogue: wide, walk, closeup };

/** The layout of a shot; a kind that cannot be drawn (a close-up of nobody) falls back to wide. */
export const layoutOf = (shot: Shot, ctx: ShotContext): Layout => {
  const fn = KINDS[shot.kind] ?? wide;
  return (fn === closeup && !shot.chars.length ? wide : fn)(shot, ctx);
};

/** The set a shot plays in when the storyboard names none. */
export const defaultSet = (kind: string) => (kind === "walk" ? "street" : "home");
