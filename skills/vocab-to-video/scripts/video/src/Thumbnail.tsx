import { loadFont } from "@remotion/fonts";
import { AbsoluteFill, staticFile, useVideoConfig } from "remotion";
import { Puppet } from "./toon/Puppet";
import { H, W } from "./toon/draw";
import { HEAD_CY, Look, makeLook } from "./toon/rig";
import { SETS } from "./toon/sets";
import { Speaker } from "./types";

export type ThumbnailProps = {
  text: string;
  level: string;
  vocab: string[];
  speakers: Speaker[];
  cast?: Record<string, Look>;
  /** The place the episode opens in: drawn, dimmed, behind the text. */
  scene?: { set?: string; time?: string; wall?: string; shop?: string };
  /** True when the episode's public folder (with the fonts) is mounted. */
  fonts?: boolean;
};

const FONT = "Be Vietnam Pro";
const YELLOW = "#FFD54A";
const BG = "#0D1326";

let fontsRequested = false;
const ensureFonts = (available: boolean) => {
  if (fontsRequested || !available) return;
  fontsRequested = true;
  (
    [
      ["600", "BeVietnamPro-SemiBold.ttf"],
      ["800", "BeVietnamPro-ExtraBold.ttf"],
    ] as const
  ).forEach(([weight, file]) =>
    loadFont({ family: FONT, url: staticFile(`fonts/${file}`), weight }),
  );
};

/** A character's head and shoulders in a round frame, facing the middle of the picture. */
const Face: React.FC<{ speaker: Speaker; look?: Look; size: number }> = ({ speaker, look, size }) => (
  <div
    style={{
      width: size,
      height: size,
      borderRadius: "50%",
      overflow: "hidden",
      border: `${Math.round(size * 0.03)}px solid ${speaker.color}`,
      boxShadow: `0 0 ${size * 0.25}px ${speaker.color}77`,
      backgroundColor: "#F3E6C8",
      flexShrink: 0,
    }}
  >
    <svg viewBox={`-160 ${HEAD_CY - 150} 320 320`} width="100%" height="100%">
      <Puppet look={makeLook(look)} x={0} y={0} s={1} face={speaker.side === "left" ? 0.45 : -0.45} light={speaker.side === "left" ? -1 : 1} />
    </svg>
  </div>
);

/** One still image: YouTube thumbnail (landscape) or Shorts/TikTok cover (portrait). */
export const Thumbnail: React.FC<ThumbnailProps> = ({ text, level, vocab, speakers, cast, scene, fonts }) => {
  const { width, height } = useVideoConfig();
  const vertical = height > width;
  ensureFonts(Boolean(fonts));

  // "MOT · Dialogue A2" -> first part white, the rest yellow, one part per line.
  const parts = text.split(/\s*[·|]\s*/).filter(Boolean);
  // The headline may wrap between words, so it is sized by its longest word (bold capitals are
  // up to 0.8 em wide); the smaller second line must fit on one line.
  const column = vertical ? width - 140 : width * 0.6 - 60;
  const longestWord = Math.max(...(parts[0] ?? "").split(/\s+/).map((w) => w.length), 1);
  const subtitle = Math.max(...parts.slice(1).map((p) => p.length), 1);
  const fontSize = Math.min(
    vertical ? 170 : 132,
    column / (longestWord * 0.8),
    column / (subtitle * 0.6 * 0.62),
  );
  const face = vertical ? 400 : 270;
  // The headline already shows one word: the chips are the next ones, never the same word twice.
  const plain = (v: string) => v.toLowerCase().replace(/[^a-zà-öø-ÿœæ]/g, "");
  const chips = vocab.filter((v) => !plain(parts[0] ?? "").includes(plain(v))).slice(0, vertical ? 4 : 3);
  const place = scene?.set && SETS[scene.set] ? SETS[scene.set] : null;
  const time = scene?.time === "dusk" || scene?.time === "night" ? scene.time : "day";
  const unit = width / (vertical ? 1080 : 1280);

  const badge = (
    <div
      style={{
        alignSelf: vertical ? "center" : "flex-start",
        fontWeight: 800,
        fontSize: 64 * unit,
        color: BG,
        backgroundColor: YELLOW,
        borderRadius: 20 * unit,
        padding: `${6 * unit}px ${30 * unit}px`,
      }}
    >
      {level}
    </div>
  );
  const title = (
    <div style={{ display: "flex", flexDirection: "column", alignItems: vertical ? "center" : "flex-start" }}>
      {parts.map((p, i) => (
        <div
          key={i}
          style={{
            fontWeight: 800,
            fontSize: i === 0 ? fontSize : fontSize * 0.62,
            lineHeight: 1.08,
            color: i === 0 ? "#FFFFFF" : YELLOW,
            textAlign: vertical ? "center" : "left",
            textShadow: "0 6px 30px rgba(0,0,0,0.55)",
            marginTop: i === 0 ? 0 : 14 * unit,
          }}
        >
          {p}
        </div>
      ))}
    </div>
  );
  const chipRow = (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 14 * unit, justifyContent: vertical ? "center" : "flex-start" }}>
      {chips.map((c) => (
        <div
          key={c}
          style={{
            fontWeight: 600,
            fontSize: 34 * unit,
            color: "#FFFFFF",
            border: `${3 * unit}px solid rgba(255,255,255,0.45)`,
            borderRadius: 60 * unit,
            padding: `${6 * unit}px ${24 * unit}px`,
          }}
        >
          {c}
        </div>
      ))}
    </div>
  );
  const faces = (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "center" }}>
      {speakers.slice(0, 2).map((sp, i) => (
        <div key={sp.id} style={i ? { marginLeft: vertical ? 40 : -50, marginTop: vertical ? 0 : 150 } : undefined}>
          <Face speaker={sp} look={cast?.[sp.id]} size={face} />
        </div>
      ))}
    </div>
  );

  return (
    <AbsoluteFill
      style={{
        fontFamily: FONT,
        backgroundColor: BG,
        backgroundImage: `radial-gradient(circle at ${vertical ? "50% 62%" : "80% 55%"}, #2a3a7a 0%, transparent 55%), linear-gradient(160deg, #16204a 0%, ${BG} 70%)`,
      }}
    >
      {place ? (
        <>
          <svg width={width} height={height} viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="xMidYMid slice" style={{ position: "absolute" }}>
            <place.Draw o={{ time, wall: scene?.wall, shop: scene?.shop }} />
          </svg>
          <AbsoluteFill
            style={{
              backgroundImage: vertical
                ? `linear-gradient(180deg, ${BG}F2 0%, ${BG}D9 45%, ${BG}B3 100%)`
                : `linear-gradient(90deg, ${BG}F5 0%, ${BG}E0 55%, ${BG}8C 100%)`,
            }}
          />
        </>
      ) : null}
      {vertical ? (
        <AbsoluteFill
          style={{ padding: "230px 70px 330px", display: "flex", flexDirection: "column", justifyContent: "space-between", alignItems: "center" }}
        >
          {badge}
          {title}
          {faces}
          {chipRow}
        </AbsoluteFill>
      ) : (
        <AbsoluteFill style={{ flexDirection: "row", alignItems: "center", padding: "0 60px" }}>
          <div style={{ width: "60%", display: "flex", flexDirection: "column", gap: 34 }}>
            {badge}
            {title}
            {chipRow}
          </div>
          <div style={{ width: "40%", display: "flex", justifyContent: "center", marginTop: -70 }}>{faces}</div>
        </AbsoluteFill>
      )}
    </AbsoluteFill>
  );
};
