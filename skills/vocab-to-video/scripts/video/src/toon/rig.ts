import data from "./rig.json";
import { back, lerp, shade } from "./math";

/** The puppet's skeleton, in its own units: origin at the feet, head radius 100. */
export const BODY_TOP = -345;
export const BODY_BOT = -128;
export const HEAD_R = 100;
export const HEAD_CY = BODY_TOP - 74;
export const SHOULDER: [number, number] = [-56, BODY_TOP + 54];
export const INK = "#18161B";
export const LW = 6;

type Pt = [number, number];
type ArmDef = [elbow: Pt, hand: Pt, showHand: boolean];
export type Eyes = "dot" | "half" | "wide" | "closed";
export type Mouth = "smile" | "smirk" | "flat" | "o" | "mid" | "open";
type Extras = { sweat?: boolean; sparkle?: boolean; pupil?: number };
type EmotionDef = [eyes: Eyes, mouth: Mouth, brow: number, browTilt: number, extras: Extras];

// The names live in rig.json so that the dialogue validator reads the same lists.
export const ARM = data.arms as unknown as Record<string, ArmDef>;
export const POSES = data.poses as unknown as Record<string, [string, string]>;
export const EMOTIONS = data.emotions as unknown as Record<string, EmotionDef>;
const SKINS = data.skins as unknown as Record<string, [string, string]>;

/** A cast entry as written in the storyboard; every key is optional. */
export type Look = {
  skin?: string;
  outfit?: string;
  color?: string;
  shirt?: string;
  tie?: string;
  bowtie?: boolean;
  hair?: string;
  hair_col?: string;
  glasses?: boolean;
  moustache?: boolean;
  beard?: boolean;
  hat?: string | boolean;
  hat_col?: string;
};

export type FullLook = {
  skin: string;
  skinD: string;
  outfit: string;
  suit: string;
  suitD: string;
  shirt: string;
  tie: string;
  bowtie: boolean;
  hair: string;
  hairCol: string;
  glasses: boolean;
  moustache: boolean;
  beard: boolean;
  hat: string;
  hatCol: string;
  hatBand: string;
};

export const makeLook = (d: Look = {}): FullLook => {
  const sk = d.skin ?? "tan";
  const preset = SKINS[sk];
  const color = d.color ?? "#3B4660";
  return {
    skin: preset ? preset[0] : sk,
    skinD: preset ? preset[1] : shade(sk, 0.84),
    outfit: d.outfit ?? "suit",
    suit: color,
    suitD: shade(color, 0.74),
    shirt: d.shirt ?? "#F4EFE2",
    tie: d.tie ?? "#A8232B",
    bowtie: Boolean(d.bowtie),
    hair: d.hair ?? "short",
    hairCol: d.hair_col ?? "#1C1B22",
    glasses: Boolean(d.glasses),
    moustache: Boolean(d.moustache),
    beard: Boolean(d.beard),
    hat: d.hat === true ? "fedora" : d.hat || "none",
    hatCol: d.hat_col ?? "#2E2E38",
    hatBand: "#7E1C24",
  };
};

/** An arm is a named pose, or a move from one pose to another with progress k (0..1). */
export type ArmSpec = string | [from: string, to: string, k: number];

export const armAt = (spec: ArmSpec): ArmDef => {
  if (typeof spec === "string") return ARM[spec] ?? ARM.down;
  const [a, b, raw] = spec;
  const k = back(raw, 1.6);
  const [ea, ha, sa] = ARM[a] ?? ARM.down;
  const [eb, hb, sb] = ARM[b] ?? ARM.down;
  return [
    [lerp(ea[0], eb[0], k), lerp(ea[1], eb[1], k)],
    [lerp(ha[0], hb[0], k), lerp(ha[1], hb[1], k)],
    k > 0.5 ? sb : sa,
  ];
};
