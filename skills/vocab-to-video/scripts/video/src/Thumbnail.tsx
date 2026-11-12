import { loadFont } from "@remotion/fonts";
import { AbsoluteFill, Img, staticFile, useVideoConfig } from "remotion";
import { Speaker } from "./types";

export type ThumbnailProps = {
  text: string;
  level: string;
  vocab: string[];
  speakers: Speaker[];
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

const Face: React.FC<{ speaker: Speaker; size: number }> = ({ speaker, size }) => (
  <div
    style={{
      width: size,
      height: size,
      borderRadius: "50%",
      overflow: "hidden",
      border: `${Math.round(size * 0.03)}px solid ${speaker.color}`,
      boxShadow: `0 0 ${size * 0.25}px ${speaker.color}77`,
      backgroundColor: "#1b2340",
      flexShrink: 0,
    }}
  >
    {speaker.image ? (
      <Img src={staticFile(speaker.image)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
    ) : null}
  </div>
);

/** One still image: YouTube thumbnail (landscape) or Shorts/TikTok cover (portrait). */
export const Thumbnail: React.FC<ThumbnailProps> = ({ text, level, vocab, speakers }) => {
  const { width, height } = useVideoConfig();
  const vertical = height > width;
  ensureFonts(speakers.some((s) => s.image));

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
  const chips = vocab.slice(0, 3);
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
      <Face speaker={speakers[0]} size={face} />
      <div style={{ marginLeft: vertical ? 40 : -70, marginTop: vertical ? 0 : 130 }}>
        <Face speaker={speakers[1]} size={face} />
      </div>
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
      {vertical ? (
        <AbsoluteFill
          style={{ padding: "300px 70px 380px", display: "flex", flexDirection: "column", justifyContent: "space-between", alignItems: "center" }}
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
