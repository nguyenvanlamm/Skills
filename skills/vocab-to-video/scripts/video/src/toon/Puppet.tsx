import React, { useId } from "react";
import { arc, Leg, pop } from "./math";
import { ArmSpec, armAt, BODY_BOT, BODY_TOP, Eyes, FullLook, HEAD_CY, HEAD_R, INK, Mouth, SHOULDER } from "./rig";

export type PuppetProps = {
  look: FullLook;
  /** Feet position and size: s = 1 is a wide shot (head radius 100), about 2.15 is a close-up. */
  x: number;
  y: number;
  s: number;
  /** -1..1, a three-quarter turn: the features slide sideways, the head itself does not rotate. */
  face?: number;
  eyes?: Eyes;
  mouth?: Mouth;
  brow?: number;
  browTilt?: number;
  arms?: [ArmSpec, ArmSpec];
  tilt?: number;
  bob?: number;
  squash?: number;
  /** Seconds the sweat drop has been sliding; negative hides it. */
  sweat?: number;
  /** -1 = key light from the left. */
  light?: number;
  rim?: string | null;
  legs?: [Leg, Leg] | null;
  pupil?: number;
  sparkle?: number;
};

const R = HEAD_R;
const DARK = "#5A1A1E";

export const Puppet: React.FC<PuppetProps> = ({
  look,
  x,
  y,
  s,
  face = 0,
  eyes = "dot",
  mouth = "smile",
  brow = 0,
  browTilt = 0,
  arms = ["down", "down"],
  tilt = 0,
  bob = 0,
  squash = 0,
  sweat = -1,
  light = -1,
  rim = null,
  legs = null,
  pupil = 0,
  sparkle = 0,
}) => {
  const uid = useId().replace(/[^a-zA-Z0-9]/g, "");
  const lw = Math.max(5.2, 4.0 / s);
  const line = (w: number, color: string = INK) =>
    ({ fill: "none", stroke: color, strokeWidth: w, strokeLinecap: "round", strokeLinejoin: "round" }) as const;
  const inked = (fill: string, w: number = lw) =>
    ({ fill, stroke: INK, strokeWidth: w, strokeLinecap: "round", strokeLinejoin: "round" }) as const;
  const { outfit, hair } = look;
  const stand: [Leg, Leg] = legs ?? [
    [-24, 0, 0],
    [24, 0, 0],
  ];

  const fx = face * 40;
  const eyeY = -6;
  const mx = face * 34;
  const my = 42;
  const dir = face >= 0 ? 1 : -1;
  const eyeXs = [-30, 30];
  const squashOf = (ex0: number) => ((face > 0 && ex0 > 0) || (face < 0 && ex0 < 0) ? 1 - 0.3 * Math.abs(face) : 1);

  const hairCap = (fringe: number) => {
    const fs = face * 14;
    const a = arc(0, -1, R + 4, R + 5, 188, 164);
    return `M ${-R - 4} -14 L ${a.start} ${a.to} C ${R - 8} -44 ${46 + fs} ${fringe - 8} ${fs} ${fringe} C ${-44 + fs} ${fringe + 4} ${-R + 6} -40 ${-R - 4} -14 Z`;
  };

  const slick = () => {
    const fs = face * 14;
    const a = arc(0, -1, R + 4, R + 4, 181, 178);
    return `M ${-R - 4} -4 L ${a.start} ${a.to} C ${R - 6} -40 ${56 + fs} -70 ${4 + fs} -62 C ${-36 + fs} -58 -78 -44 ${-R - 4} -4 Z`;
  };

  const star = () => {
    const k = pop(sparkle) * (sparkle < 1 ? 1 : Math.max(0, 2 - sparkle));
    const cx = mx + 26 * dir;
    const cy = my - 8;
    const pts: string[] = [];
    for (let i = 0; i < 8; i++) {
      const r = (i % 2 === 0 ? 20 : 5) * k;
      const a = (i * Math.PI) / 4;
      pts.push(`${cx + r * Math.cos(a)},${cy + r * Math.sin(a)}`);
    }
    return pts.join(" ");
  };

  const mouthOpen = `M ${mx - 20} ${my - 5} L ${mx + 20} ${my - 5} C ${mx + 19} ${my + 24} ${mx - 19} ${my + 24} ${mx - 20} ${my - 5} Z`;
  const neck = arc(0, BODY_TOP - 2, 34, 28, 20, 140);
  const capArc = arc(0, -5, R + 2, R + 5, 182, 176);
  const shine = arc(0, 0, R - 20, R - 14, light < 0 ? 208 : 282, 50);

  return (
    <g transform={`translate(${x} ${y}) scale(${s})`}>
      <defs>
        <clipPath id={`${uid}b`}>
          <rect x={-84} y={BODY_TOP} width={168} height={BODY_BOT - BODY_TOP} rx={66} ry={72} />
        </clipPath>
        <clipPath id={`${uid}h`}>
          <circle r={R} />
        </clipPath>
        <clipPath id={`${uid}m`}>
          <path d={mouthOpen} />
        </clipPath>
        <clipPath id={`${uid}f`}>
          <path d={`M ${-R + 6} -56 C ${-R - 2} ${-R - 82} ${R + 2} ${-R - 82} ${R - 6} -56 Z`} />
        </clipPath>
      </defs>

      {stand.map(([hip, dx, lift], i) => (
        <line key={i} x1={hip} y1={BODY_BOT - 8} x2={hip + dx} y2={-lift} {...line(lw)} />
      ))}

      <g transform={`translate(0 ${-bob}) scale(${1 + squash * 0.6} ${1 - squash})`}>
        {outfit === "dress" ? (
          <path
            d={`M -70 ${BODY_BOT - 70} L 70 ${BODY_BOT - 70} L 104 ${BODY_BOT + 30} Q 0 ${BODY_BOT + 46} -104 ${BODY_BOT + 30} Z`}
            {...inked(look.suit)}
          />
        ) : null}
        {hair === "long" ? (
          <rect x={-R - 14} y={HEAD_CY - 40} width={2 * R + 28} height={190} rx={60} {...inked(look.hairCol)} />
        ) : null}

        {/* Body: flat fill with one hard shadow on the side away from the light. */}
        <g clipPath={`url(#${uid}b)`}>
          <rect x={-200} y={BODY_TOP - 20} width={400} height={300} fill={look.suitD} />
          <rect
            x={-84 + light * 16}
            y={BODY_TOP - 5}
            width={168}
            height={BODY_BOT - BODY_TOP}
            rx={66}
            ry={72}
            fill={look.suit}
          />
          {outfit === "suit" ? (
            <>
              <path d={`M -34 ${BODY_TOP - 4} L 0 ${BODY_TOP + 96} L 34 ${BODY_TOP - 4} Z`} fill={look.shirt} />
              {look.bowtie ? (
                <>
                  <path
                    d={`M 0 ${BODY_TOP + 40} L -24 ${BODY_TOP + 26} L -24 ${BODY_TOP + 54} Z M 0 ${BODY_TOP + 40} L 24 ${BODY_TOP + 26} L 24 ${BODY_TOP + 54} Z`}
                    {...inked(look.tie, lw * 0.75)}
                  />
                  <circle cx={0} cy={BODY_TOP + 40} r={5} {...inked(look.tie, lw * 0.7)} />
                </>
              ) : look.tie !== "none" ? (
                <path
                  d={`M -9 ${BODY_TOP + 24} L 9 ${BODY_TOP + 24} L 13 ${BODY_TOP + 82} L 0 ${BODY_TOP + 98} L -13 ${BODY_TOP + 82} Z`}
                  {...inked(look.tie, lw * 0.75)}
                />
              ) : null}
              {[-1, 1].map((sx) => (
                <g key={sx}>
                  <path
                    d={`M ${sx * 36} ${BODY_TOP - 2} L ${sx * 2} ${BODY_TOP + 98} L ${sx * 2} ${BODY_BOT}`}
                    {...line(lw * 0.75)}
                  />
                  <line x1={sx * 22} y1={BODY_TOP + 58} x2={sx * 40} y2={BODY_TOP + 44} {...line(lw * 0.6)} />
                </g>
              ))}
            </>
          ) : null}
          {outfit === "hoodie" ? (
            <>
              <path d={`M -60 ${BODY_TOP - 2} Q 0 ${BODY_TOP + 44} 60 ${BODY_TOP - 2}`} {...line(lw * 0.8)} />
              {[-1, 1].map((sx) => (
                <line
                  key={sx}
                  x1={sx * 16}
                  y1={BODY_TOP + 20}
                  x2={sx * 18}
                  y2={BODY_TOP + 84}
                  {...line(lw * 0.55, look.shirt)}
                />
              ))}
              <path
                d={`M -48 ${BODY_BOT - 6} L -38 ${BODY_BOT - 66} L 38 ${BODY_BOT - 66} L 48 ${BODY_BOT - 6}`}
                {...line(lw * 0.6)}
              />
            </>
          ) : null}
          {outfit === "tshirt" || outfit === "dress" || outfit === "sweater" ? (
            <path d={`M ${neck.start} ${neck.to}`} {...line(lw * 0.7)} />
          ) : null}
          {outfit === "sweater" ? (
            <line x1={-84} y1={BODY_BOT - 22} x2={84} y2={BODY_BOT - 22} {...line(lw * 0.6)} />
          ) : null}
        </g>
        <rect x={-84} y={BODY_TOP} width={168} height={BODY_BOT - BODY_TOP} rx={66} ry={72} {...line(lw)} />

        {/* Arms: one curve from shoulder through elbow to hand; the right arm is the mirrored table entry. */}
        {arms.map((spec, i) => {
          const m = i === 0 ? 1 : -1;
          const [e, h, show] = armAt(spec);
          const sx = SHOULDER[0] * m;
          const sy = SHOULDER[1];
          const ex = e[0] * m;
          const hx = h[0] * m;
          return (
            <g key={i}>
              <path
                d={`M ${sx} ${sy} Q ${1.35 * ex - 0.175 * (sx + hx)} ${1.35 * e[1] - 0.175 * (sy + h[1])} ${hx} ${h[1]}`}
                {...line(lw)}
              />
              {show ? <circle cx={hx} cy={h[1]} r={13} {...inked(look.skin, lw * 0.8)} /> : null}
            </g>
          );
        })}

        <g transform={`translate(0 ${HEAD_CY}) rotate(${tilt})`}>
          {hair === "bald"
            ? [-1, 1].map((sx) => (
                <path
                  key={sx}
                  d={`M ${sx * 84} -44 L ${sx * 112} -34 L ${sx * 98} -18 L ${sx * 118} -4 L ${sx * 100} 10 L ${sx * 112} 26 L ${sx * 86} 34 Z`}
                  {...inked(look.hairCol === "#1C1B22" ? "#8A8A92" : look.hairCol, lw * 0.8)}
                />
              ))
            : null}
          {hair === "curly"
            ? Array.from({ length: 11 }, (_, i) => {
                const a = ((165 + i * 21) * Math.PI) / 180;
                return (
                  <circle
                    key={i}
                    cx={(R + 4) * Math.cos(a)}
                    cy={(R + 4) * Math.sin(a) + 6}
                    r={34}
                    {...inked(look.hairCol, lw * 0.8)}
                  />
                );
              })
            : null}
          {hair === "bun" ? <circle cx={0} cy={-R - 26} r={44} {...inked(look.hairCol)} /> : null}

          <g clipPath={`url(#${uid}h)`}>
            <rect x={-R} y={-R} width={2 * R} height={2 * R} fill={look.skinD} />
            <circle cx={light * 7} cy={-17} r={R} fill={look.skin} />
            {rim ? (
              <path
                fillRule="evenodd"
                fill={rim}
                opacity={0.84}
                d={`M ${-2 * R} ${-2 * R} H ${2 * R} V ${2 * R} H ${-2 * R} Z M ${-light * 11 - R} 4 a ${R} ${R} 0 1 0 ${2 * R} 0 a ${R} ${R} 0 1 0 ${-2 * R} 0 Z`}
              />
            ) : null}
          </g>

          {hair === "slick" ? (
            <>
              <path d={slick()} {...inked(look.hairCol)} />
              <path d={`M ${shine.start} ${shine.to}`} {...line(lw * 1.3, "#5C607A")} />
            </>
          ) : null}
          {hair === "short" || hair === "bun" || hair === "long" || hair === "curly" ? (
            <path d={hairCap(hair === "curly" ? -66 : -58)} {...inked(look.hairCol)} />
          ) : null}
          <circle r={R} {...line(lw)} />

          {look.hat === "fedora" ? (
            <>
              <path
                d={`M ${-R + 6} -56 C ${-R - 2} ${-R - 82} ${R + 2} ${-R - 82} ${R - 6} -56 Z`}
                fill={look.hatCol}
              />
              <g clipPath={`url(#${uid}f)`}>
                <rect x={-R} y={-86} width={2 * R} height={30} fill={look.hatBand} />
                <line x1={-R} y1={-86} x2={R} y2={-86} {...line(lw * 0.7)} />
              </g>
              <path d={`M ${-R + 6} -56 C ${-R - 2} ${-R - 82} ${R + 2} ${-R - 82} ${R - 6} -56 Z`} {...line(lw)} />
              <ellipse cx={0} cy={-55} rx={R + 40} ry={15} {...inked(look.hatCol)} />
            </>
          ) : null}
          {look.hat === "cap" ? (
            <>
              <path d={`M ${-R - 2} -40 L ${capArc.start} ${capArc.to} Z`} {...inked(look.hatCol)} />
              <path
                d={`M ${dir * 10} -44 Q ${dir * (R + 70)} -52 ${dir * (R + 76)} -30 L ${dir * 10} -34 Z`}
                {...inked(look.hatCol)}
              />
            </>
          ) : null}

          {eyeXs.map((ex0) => {
            const ex = ex0 + fx;
            const sq = squashOf(ex0);
            const inner = ex0 < 0 ? 1 : -1;
            const by = eyeY - 29 - brow * 9;
            const up = pupil < 0 && eyes === "dot" && Math.abs(pupil) > 0.5 ? -4 : 0;
            const chord = 6.5 * sq * 0.9428;
            return (
              <g key={ex0}>
                {eyes === "wide" ? (
                  <>
                    <ellipse cx={ex} cy={eyeY} rx={17 * sq} ry={17} {...inked("#FBFBF7", lw * 0.7)} />
                    <ellipse cx={ex + pupil * 6} cy={eyeY} rx={5.5 * sq} ry={5.5} fill={INK} />
                  </>
                ) : eyes === "closed" ? (
                  <path
                    d={`M ${ex - 11 * sq} ${eyeY} Q ${ex} ${eyeY + 9} ${ex + 11 * sq} ${eyeY}`}
                    {...line(lw * 0.8)}
                  />
                ) : eyes === "half" ? (
                  <>
                    <path
                      d={`M ${ex - chord} ${eyeY - 3} A ${6.5 * sq} 9 0 1 0 ${ex + chord} ${eyeY - 3} Z`}
                      fill={INK}
                    />
                    <line x1={ex - 13 * sq} y1={eyeY - 4} x2={ex + 13 * sq} y2={eyeY - 4} {...line(lw * 0.8)} />
                  </>
                ) : (
                  <>
                    <ellipse cx={ex} cy={eyeY + up} rx={5.5 * sq} ry={8} fill={INK} />
                    <circle cx={ex + 1.5} cy={eyeY - 3 + up} r={1.8} fill="#FFFFFF" opacity={0.86} />
                  </>
                )}
                <line
                  x1={ex - 13 * sq}
                  y1={by + (inner < 0 ? browTilt * 7 : -browTilt * 7)}
                  x2={ex + 13 * sq}
                  y2={by + (inner > 0 ? browTilt * 7 : -browTilt * 7)}
                  {...line(lw * 0.78)}
                />
              </g>
            );
          })}

          {look.glasses ? (
            <>
              {eyeXs.map((ex0) => (
                <ellipse
                  key={ex0}
                  cx={ex0 + fx}
                  cy={eyeY}
                  rx={24 * squashOf(ex0)}
                  ry={24}
                  fill="rgba(225,240,255,0.22)"
                  stroke={INK}
                  strokeWidth={lw * 0.7}
                />
              ))}
              <line x1={fx - 7} y1={eyeY - 3} x2={fx + 7} y2={eyeY - 3} {...line(lw * 0.7)} />
            </>
          ) : null}

          {look.beard ? (
            <path
              d={`M ${-R + 6} 6 Q ${-R + 4} ${R - 4} ${mx} ${R + 18} Q ${R - 4} ${R - 4} ${R - 6} 6 Q ${R * 0.5} 40 ${mx + 26} 30 Q ${mx} 22 ${mx - 26} 30 Q ${-R * 0.5} 40 ${-R + 6} 6 Z`}
              {...inked(look.hairCol, lw * 0.8)}
            />
          ) : null}
          {look.moustache ? (
            <path
              d={`M ${mx} ${my - 20} C ${mx - 12} ${my - 28} ${mx - 30} ${my - 22} ${mx - 40} ${my - 30} C ${mx - 30} ${my - 10} ${mx - 12} ${my - 12} ${mx} ${my - 15} C ${mx + 12} ${my - 12} ${mx + 30} ${my - 10} ${mx + 40} ${my - 30} C ${mx + 30} ${my - 22} ${mx + 12} ${my - 28} ${mx} ${my - 20} Z`}
              fill={look.hairCol}
            />
          ) : null}

          {mouth === "smile" ? (
            <path d={`M ${mx - 17} ${my - 2} Q ${mx} ${my + 13} ${mx + 17} ${my - 2}`} {...line(lw * 0.8)} />
          ) : mouth === "smirk" ? (
            <path
              d={`M ${mx - 15 * dir} ${my + 3} Q ${mx + 4 * dir} ${my + 12} ${mx + 20 * dir} ${my - 6}`}
              {...line(lw * 0.8)}
            />
          ) : mouth === "flat" ? (
            <line x1={mx - 12} y1={my + 2} x2={mx + 12} y2={my + 2} {...line(lw * 0.8)} />
          ) : mouth === "o" ? (
            <ellipse cx={mx} cy={my + 1} rx={8} ry={10} {...inked(DARK, lw * 0.7)} />
          ) : mouth === "mid" ? (
            <ellipse cx={mx} cy={my + 3} rx={12} ry={7} {...inked(DARK, lw * 0.7)} />
          ) : (
            <>
              <path d={mouthOpen} fill={DARK} />
              <g clipPath={`url(#${uid}m)`}>
                <rect x={mx - 22} y={my - 6} width={44} height={8} fill="#FAFAF4" />
                <ellipse cx={mx} cy={my + 17.5} rx={11} ry={8.5} fill="#D05860" />
              </g>
              <path d={mouthOpen} {...line(lw * 0.7)} />
            </>
          )}

          {sparkle > 0 ? <polygon points={star()} fill="#FFFFFF" /> : null}
          {sweat >= 0
            ? (() => {
                const sx0 = (face > 0 ? -1 : 1) * 62;
                const sy0 = -66 + 30 * (sweat % 1);
                return (
                  <path
                    d={`M ${sx0} ${sy0 - 19} C ${sx0 + 12} ${sy0 - 3} ${sx0 + 11} ${sy0 + 10} ${sx0} ${sy0 + 10} C ${sx0 - 11} ${sy0 + 10} ${sx0 - 12} ${sy0 - 3} ${sx0} ${sy0 - 19} Z`}
                    {...inked("#8FC8EE", lw * 0.7)}
                  />
                );
              })()
            : null}
        </g>
      </g>
    </g>
  );
};
