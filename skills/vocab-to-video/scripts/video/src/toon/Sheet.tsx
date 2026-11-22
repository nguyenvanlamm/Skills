import React from "react";
import { AbsoluteFill } from "remotion";
import { Puppet } from "./Puppet";
import { EMOTIONS, Look, makeLook, POSES } from "./rig";

const LOOKS: Look[] = [
  { skin: "fair", outfit: "sweater", color: "#E0A22B", hair: "long", hair_col: "#6B3F22" },
  { skin: "tan", outfit: "tshirt", color: "#2F4A7A", hair: "short", beard: true },
  { skin: "brown", outfit: "suit", color: "#3B4660", hair: "slick", moustache: true, hat: "fedora" },
  { skin: "light", outfit: "hoodie", color: "#5FA36B", hair: "curly", hair_col: "#C2562E", glasses: true },
  { skin: "olive", outfit: "dress", color: "#B84A6A", hair: "bun" },
  { skin: "dark", outfit: "suit", color: "#6B4A8A", hair: "bald", bowtie: true, hat: "cap" },
];

/** Every pose and emotion on one page: the picture to look at after changing the puppet. */
export const Sheet: React.FC = () => {
  const poses = Object.keys(POSES);
  const emotions = Object.keys(EMOTIONS);
  const cells = Array.from({ length: 18 }, (_, i) => i);
  return (
    <AbsoluteFill style={{ backgroundColor: "#F3E6C8" }}>
      <svg viewBox="0 0 3600 2000" width="100%" height="100%">
        {cells.map((i) => {
          const pose = poses[i % poses.length];
          const emotion = emotions[i % emotions.length];
          const [eyes, mouth, brow, browTilt, extra] = EMOTIONS[emotion];
          const col = i % 6;
          const row = Math.floor(i / 6);
          const face = [-0.7, 0, 0.7][i % 3];
          return (
            <g key={i}>
              <Puppet
                look={makeLook(LOOKS[(i + row) % LOOKS.length])}
                x={300 + col * 600}
                y={620 + row * 650}
                s={1}
                face={face}
                eyes={eyes}
                mouth={i % 5 === 4 ? "mid" : mouth}
                brow={brow}
                browTilt={browTilt}
                arms={POSES[pose]}
                light={face < 0 ? 1 : -1}
                rim={row === 2 ? "#FFE6B0" : null}
                sweat={extra.sweat ? 0.4 : -1}
                sparkle={extra.sparkle ? 1 : 0}
                pupil={extra.pupil ?? 0}
              />
              <text x={300 + col * 600} y={660 + row * 650} textAnchor="middle" fontSize={34} fontFamily="sans-serif" fill="#18161B">
                {pose} · {emotion}
              </text>
            </g>
          );
        })}
      </svg>
    </AbsoluteFill>
  );
};
