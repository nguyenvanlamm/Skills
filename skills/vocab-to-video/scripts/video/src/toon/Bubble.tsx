import React from "react";
import { interpolate } from "remotion";
import { Line } from "../types";
import { back } from "./math";
import { INK } from "./rig";

export const FONT = "Be Vietnam Pro";
export const VOCAB = "#FFD54A";
export const BG = "#0D1326";

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const BORDER = 6;
const PAD_X = 30;
const PAD_Y = 20;

/** Where a bubble goes: over a head, beside a head (close-up), or free at the top when nobody is shown. */
export type BubbleSpot =
  | { kind: "above"; x: number; y: number }
  | { kind: "side"; x: number; y: number; dir: 1 | -1 }
  | { kind: "free"; y: number; from: "top" | "bottom" };

/** Text size for a line: short lines are big, long ones shrink so the bubble stays off the faces. */
export const bubbleType = (line: Line, vertical: boolean) => {
  const chars = line.text.length;
  const base = vertical ? (chars <= 40 ? 58 : chars <= 80 ? 50 : 44) : chars <= 40 ? 54 : chars <= 90 ? 48 : 42;
  return line.kind === "hook" ? Math.round(base * 1.12) : base;
};

/**
 * Speech bubble with the karaoke caption: words turn from grey to black as they are spoken and
 * new words carry a yellow marker stroke. No word changes size, so the spacing never moves. It pops out of the speaker and its tail points back at them.
 */
export const Bubble: React.FC<{
  line: Line;
  t: number;
  vertical: boolean;
  spot: BubbleSpot;
  maxW: number;
  frameW: number;
  frameH: number;
  opacity?: number;
}> = ({ line, t, vertical, spot, maxW, frameW, frameH, opacity = 1 }) => {
  const hook = line.kind === "hook";
  const fontSize = bubbleType(line, vertical);
  const margin = vertical ? 36 : 48;
  const width = Math.min(maxW, Math.round(line.text.length * fontSize * 0.6) + 2 * PAD_X + 2 * BORDER);
  const grow = back(interpolate(t, [line.startMs - 150, line.startMs + 120], [hook ? 1 : 0, 1], clamp), 1.4);

  let box: React.CSSProperties;
  let tail: React.ReactNode = null;
  let origin = "50% 100%";
  if (spot.kind === "above") {
    const left = Math.min(Math.max(spot.x - width / 2, margin), frameW - width - margin);
    const tx = Math.min(Math.max(spot.x - left, 56), width - 56);
    box = { left, bottom: frameH - spot.y + 40 };
    origin = `${tx}px 100%`;
    tail = (
      <svg width={64} height={50} style={{ position: "absolute", left: tx - 32 - BORDER, top: "100%", marginTop: -BORDER - 1 }}>
        <rect x={BORDER} y={0} width={64 - 2 * BORDER} height={BORDER + 2} fill="#fff" />
        <path d="M 4 5 L 32 46 L 60 5" fill="#fff" stroke={INK} strokeWidth={BORDER} strokeLinejoin="round" strokeLinecap="round" />
      </svg>
    );
  } else if (spot.kind === "side") {
    box =
      spot.dir > 0
        ? { left: spot.x + 46, top: spot.y, transform: "translateY(-50%)" }
        : { right: frameW - spot.x + 46, top: spot.y, transform: "translateY(-50%)" };
    origin = spot.dir > 0 ? "0% 50%" : "100% 50%";
    tail = (
      <svg
        width={50}
        height={64}
        style={{
          position: "absolute",
          top: "50%",
          marginTop: -32,
          ...(spot.dir > 0 ? { right: "100%", marginRight: -BORDER - 1 } : { left: "100%", marginLeft: -BORDER - 1 }),
          transform: spot.dir > 0 ? undefined : "scaleX(-1)",
        }}
      >
        <rect x={50 - BORDER - 2} y={BORDER} width={BORDER + 2} height={64 - 2 * BORDER} fill="#fff" />
        <path d="M 45 4 L 4 32 L 45 60" fill="#fff" stroke={INK} strokeWidth={BORDER} strokeLinejoin="round" strokeLinecap="round" />
      </svg>
    );
  } else {
    box = { left: (frameW - width) / 2, ...(spot.from === "bottom" ? { bottom: spot.y } : { top: spot.y }) };
    origin = spot.from === "bottom" ? "50% 100%" : "50% 0%";
  }

  return (
    <div style={{ position: "absolute", width, opacity, ...box }}>
      <div
        style={{
          position: "relative",
          transform: `scale(${grow})`,
          transformOrigin: origin,
          backgroundColor: "#FFFFFF",
          border: `${BORDER}px solid ${INK}`,
          borderRadius: 34,
          padding: `${PAD_Y}px ${PAD_X}px`,
          boxShadow: "0 10px 0 rgba(24,22,27,0.18)",
          display: "flex",
          flexWrap: "wrap",
          justifyContent: "center",
          columnGap: fontSize * 0.3,
          rowGap: fontSize * 0.06,
          fontFamily: FONT,
          fontSize,
          lineHeight: 1.2,
        }}
      >
        {line.words.map((w, i) => {
          const said = interpolate(t, [w.startMs - 50, w.startMs + 70], [0, 1], clamp);
          // Words not yet spoken are grey but readable ahead; the hook is dark from the first frame.
          const alpha = (hook ? 0.75 : 0.55) + (hook ? 0.25 : 0.45) * said;
          return (
            <span
              key={i}
              style={{
                display: "inline-block",
                fontWeight: w.isVocab || hook ? 800 : 600,
                // Only the letters fade: the yellow marker of a new word is solid all along.
                color: `rgba(24,22,27,${alpha})`,
                backgroundColor: w.isVocab ? VOCAB : undefined,
                borderRadius: w.isVocab ? fontSize * 0.2 : undefined,
                padding: w.isVocab ? `0 ${fontSize * 0.14}px` : undefined,
                whiteSpace: "nowrap",
              }}
            >
              {w.text}
            </span>
          );
        })}
        {tail}
      </div>
    </div>
  );
};
