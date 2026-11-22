import type { Beat, ShotChar } from "../types";
import { W } from "./draw";
import { back, blink, easeOut, K, lerp, walkLegs } from "./math";
import type { PuppetProps } from "./Puppet";
import { ArmSpec, EMOTIONS, FullLook, POSES } from "./rig";

/** A cast member placed in a shot: where they stand and what they do when nothing else is said. */
export type Placed = {
  char: ShotChar;
  look: FullLook;
  x: number;
  y: number;
  s: number;
  face: number;
};

type State = { pose: string; emotion: string; face: number };

export type MouthShape = "open" | "mid" | "closed" | null;

/** Every actor idles on its own phase, so two characters never bob in step. */
const phaseOf = (id: string) => {
  let sum = 0;
  for (let i = 0; i < id.length; i++) sum += id.charCodeAt(i);
  return (sum % 17) / 3;
};

/**
 * What the puppet looks like at time t (seconds) of a shot running from t0 to t1.
 * Idle bob, sway and blinks are always on; beats snap the pose with an overshoot and a squash;
 * the mouth follows the voice while this character is the one speaking.
 */
export const actorAt = (
  a: Placed,
  beats: Beat[],
  t: number,
  t0: number,
  t1: number,
  mouthShape: MouthShape,
  night: boolean,
): PuppetProps => {
  const ph = phaseOf(a.char.id);
  let st: State = { pose: a.char.pose ?? "idle", emotion: a.char.emotion ?? "neutral", face: a.face };
  let prev: State = st;
  let tb = t0;
  for (const b of beats) {
    if (b.who !== a.char.id || t < b.atMs / 1000) continue;
    prev = st;
    tb = b.atMs / 1000;
    st = { pose: b.pose ?? st.pose, emotion: b.emotion ?? st.emotion, face: b.face ?? st.face };
  }

  const emotion = EMOTIONS[st.emotion] ?? EMOTIONS.neutral;
  let eyes = emotion[0];
  let mouth = emotion[1];
  const extras = emotion[4];
  const k = K(t, tb, 0.3);
  const pa = POSES[prev.pose] ?? POSES.idle;
  const pb = POSES[st.pose] ?? POSES.idle;
  const arm = (i: number): ArmSpec => (pa[i] !== pb[i] && k < 1 ? [pa[i], pb[i], k] : pb[i]);
  let face = prev.face !== st.face ? lerp(prev.face, st.face, back(k, 1.2)) : st.face;

  let x = a.x;
  let legs: PuppetProps["legs"] = null;
  let walking = false;
  let bob = 2 + 2 * Math.sin(t * 3 + ph);
  let tilt = 1.4 * Math.sin(t * 2.2 + ph);
  const { walk, enter, exit } = a.char;
  let walked = 0; // distance covered so far: the legs step with it, so feet never slide
  if (walk) {
    const u = K(t, t0 + 0.1, Math.max(0.5, t1 - t0 - 0.4));
    x = lerp(walk[0], walk[1], u);
    walked = Math.abs(x - walk[0]);
    walking = u > 0 && u < 1;
  } else if (enter) {
    const u = K(t, t0, 1.1);
    const from = enter === "left" ? -260 : W + 260;
    x = lerp(from, a.x, easeOut(u));
    walked = Math.abs(x - from);
    walking = u < 0.97;
  }
  let leaving = false;
  if (exit) {
    const u = K(t, t1 - 1.1, 1.0);
    if (u > 0) {
      const from = x;
      x = lerp(x, exit === "left" ? -300 : W + 300, u * u);
      walked += Math.abs(x - from);
      walking = true;
      leaving = true;
    }
  }
  if (walking) {
    const p = walked / 17; // one step every 53 px
    legs = walkLegs(p);
    bob = 7 * Math.abs(Math.sin(p));
    tilt = 3 * Math.sin(p);
    const right = leaving ? exit === "right" : walk ? walk[1] > walk[0] : enter === "left";
    face = right ? 0.7 : -0.7;
  }

  if (mouthShape) {
    mouth =
      mouthShape === "open"
        ? "open"
        : mouthShape === "mid"
          ? "mid"
          : mouth === "smile" || mouth === "smirk" || mouth === "flat"
            ? mouth
            : mouth === "open"
              ? "smile" // a laughing face still smiles between syllables
              : "flat";
    if (mouthShape === "open") bob += 3;
  }
  if (eyes !== "closed" && blink(t, 2.5, ph)) eyes = "closed";
  if (st.pose === "facepalm") eyes = "closed";

  const squash =
    0.06 * Math.sin(K(t, t0, 0.26) * Math.PI) + (tb > t0 ? 0.06 * Math.sin(K(t, tb, 0.26) * Math.PI) : 0);
  const droop = st.emotion === "smug" || st.emotion === "sad" || st.emotion === "tired" ? -4 : 0;

  return {
    look: a.look,
    x,
    y: a.y,
    s: a.s,
    face,
    eyes,
    mouth,
    brow: emotion[2],
    browTilt: emotion[3],
    arms: [arm(0), arm(1)],
    tilt: tilt + droop,
    bob,
    squash,
    sweat: extras.sweat ? (t - t0) * 1.1 : -1,
    sparkle: extras.sparkle && t - tb < 1.2 ? (t - tb) / 0.3 : 0,
    pupil: extras.pupil ?? 0,
    light: face < 0 ? 1 : -1,
    rim: night ? "#FFE6B0" : null,
    legs,
  };
};
