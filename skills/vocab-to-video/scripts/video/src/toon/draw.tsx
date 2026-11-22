import React from "react";
import { INK, LW } from "./rig";

/** Small drawing helpers: every shape gets the same round ink line. */
export const W = 1920;
export const H = 1080;
export const HAND = "Kalam, 'Be Vietnam Pro', sans-serif";

export const ink = (w: number = LW, color: string = INK, opacity = 1) =>
  ({
    fill: "none",
    stroke: color,
    strokeWidth: w,
    strokeLinecap: "round",
    strokeLinejoin: "round",
    strokeOpacity: opacity,
  }) as const;

const outline = (w: number) =>
  w > 0 ? ({ stroke: INK, strokeWidth: w, strokeLinecap: "round", strokeLinejoin: "round" } as const) : {};

type Box = { x0: number; y0: number; x1: number; y1: number; fill: string; w?: number; r?: number; opacity?: number };

export const Rc: React.FC<Box> = ({ x0, y0, x1, y1, fill, w = LW, r = 0, opacity }) => (
  <rect x={x0} y={y0} width={x1 - x0} height={y1 - y0} rx={r} fill={fill} opacity={opacity} {...outline(w)} />
);

export const Ov: React.FC<Box> = ({ x0, y0, x1, y1, fill, w = LW, opacity }) => (
  <ellipse
    cx={(x0 + x1) / 2}
    cy={(y0 + y1) / 2}
    rx={(x1 - x0) / 2}
    ry={(y1 - y0) / 2}
    fill={fill}
    opacity={opacity}
    {...outline(w)}
  />
);

export const Ci: React.FC<{ x: number; y: number; r: number; fill: string; w?: number; opacity?: number }> = ({
  x,
  y,
  r,
  fill,
  w = LW,
  opacity,
}) => <circle cx={x} cy={y} r={r} fill={fill} opacity={opacity} {...outline(w)} />;

export const Ln: React.FC<{
  x0: number;
  y0: number;
  x1: number;
  y1: number;
  w?: number;
  color?: string;
  opacity?: number;
}> = ({ x0, y0, x1, y1, w = LW, color = INK, opacity = 1 }) => (
  <line x1={x0} y1={y0} x2={x1} y2={y1} {...ink(w, color, opacity)} />
);

export const Pg: React.FC<{ pts: [number, number][]; fill: string; w?: number; opacity?: number }> = ({
  pts,
  fill,
  w = LW,
  opacity,
}) => <polygon points={pts.map((p) => p.join(",")).join(" ")} fill={fill} opacity={opacity} {...outline(w)} />;

/** Size that keeps a hand-lettered string inside maxW (width estimated from the letter count). */
export const fitSize = (text: string, size: number, maxW: number) => {
  const est = text.length * size * 0.56;
  return est <= maxW ? size : (size * maxW) / est;
};

/** Hand lettering, slightly slanted, with an optional thick ink outline. */
export const Hand: React.FC<{
  text: string;
  x: number;
  y: number;
  size: number;
  color: string;
  align?: "start" | "middle" | "end";
  stroke?: number;
  skew?: number;
  opacity?: number;
}> = ({ text, x, y, size, color, align = "start", stroke = 0, skew = -0.16, opacity = 1 }) => (
  <text
    transform={`translate(${x} ${y}) skewX(${(Math.atan(skew) * 180) / Math.PI})`}
    fontFamily={HAND}
    fontWeight={700}
    fontSize={size}
    textAnchor={align}
    fill={color}
    opacity={opacity}
    stroke={stroke ? INK : "none"}
    strokeWidth={stroke}
    strokeLinejoin="round"
    paintOrder="stroke"
  >
    {text}
  </text>
);
