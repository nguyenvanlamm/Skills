import React from "react";
import { fitSize, Hand, HAND } from "./draw";
import { easeOut, pop } from "./math";

const NAMED: Record<string, string> = {
  lime: "#B8F04A",
  cream: "#FFF6DC",
  red: "#C8242C",
  gold: "#F2C14E",
  sky: "#7FC8F8",
  pink: "#FF6FA0",
  white: "#FFFFFF",
};

export const named = (v: string | undefined, fallback: string) => (v ? (NAMED[v] ?? v) : fallback);

/** Hand-lettered word that pops in over the scene; u = seconds since its cue. */
export const PopLabel: React.FC<{
  text: string;
  x: number;
  y: number;
  u: number;
  color: string;
  rot?: number;
  size?: number;
  maxW?: number;
}> = ({ text, x, y, u, color, rot = -5, size = 120, maxW = 900 }) => {
  if (u <= 0) return null;
  const k = pop(Math.min(u / 0.3, 1));
  return (
    <g transform={`translate(${x} ${y}) rotate(${rot}) scale(${k})`}>
      <Hand text={text} x={0} y={0} size={fitSize(text, size, maxW)} color={color} align="middle" stroke={15} skew={-0.14} />
    </g>
  );
};

/** Place tag that slides in at the bottom left of the stage; u = seconds since the shot began. */
export const Tag: React.FC<{ text: string; u: number; x: number; y: number }> = ({ text, u, x, y }) => {
  const a = easeOut(u * 3);
  if (a <= 0) return null;
  const w = text.length * 44 * 0.56 + 64;
  return (
    <g transform={`translate(${-50 * (1 - a)} 0)`} opacity={a}>
      <rect x={x} y={y - 52} width={w} height={70} rx={10} fill="rgb(10,12,26)" opacity={0.8} />
      <rect x={x} y={y - 52} width={10} height={70} fill="#F2C14E" />
      <text x={x + 34} y={y} fontFamily={HAND} fontWeight={700} fontSize={44} fill="#FFF6DC">
        {text}
      </text>
    </g>
  );
};
