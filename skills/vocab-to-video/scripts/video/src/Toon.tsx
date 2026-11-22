import { loadFont } from "@remotion/fonts";
import { Audio } from "@remotion/media";
import { AbsoluteFill, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { BG, FONT, VOCAB } from "./toon/Bubble";
import { Stage } from "./toon/Stage";
import { Episode } from "./types";

const FILES: [family: string, weight: string, file: string][] = [
  [FONT, "600", "BeVietnamPro-SemiBold.ttf"],
  [FONT, "800", "BeVietnamPro-ExtraBold.ttf"],
  ["Kalam", "700", "Kalam-Bold.ttf"],
];

let fontsRequested = false;
/** Fonts ship in the episode's public folder, so they are only requested for a real episode. */
export const ensureFonts = (available: boolean) => {
  if (fontsRequested || !available) return;
  fontsRequested = true;
  FILES.forEach(([family, weight, file]) => loadFont({ family, url: staticFile(`fonts/${file}`), weight }));
};

/** One episode as a 2D cartoon filling the frame; the lines are shown in speech bubbles. */
export const Toon: React.FC<Episode> = (episode) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const vertical = height > width;
  const t = (frame / fps) * 1000;

  ensureFonts(Boolean(episode.audio));
  const titleIn = interpolate(t, [0, 400], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ backgroundColor: BG, fontFamily: FONT }}>
      {episode.audio ? <Audio src={staticFile(episode.audio)} /> : null}
      <Stage episode={episode} width={width} height={height} vertical={vertical} />
      <div
        style={{
          position: "absolute",
          top: vertical ? 120 : 26,
          left: vertical ? 0 : undefined,
          right: vertical ? 0 : 36,
          display: "flex",
          justifyContent: "center",
          opacity: titleIn,
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 16,
            backgroundColor: "rgba(13,19,38,0.82)",
            borderRadius: 16,
            padding: "8px 18px 8px 8px",
            maxWidth: vertical ? 960 : 900,
          }}
        >
          <div
            style={{
              fontWeight: 800,
              fontSize: vertical ? 32 : 26,
              color: BG,
              backgroundColor: VOCAB,
              borderRadius: 10,
              padding: "4px 14px",
            }}
          >
            {episode.level}
          </div>
          <div style={{ fontWeight: 600, fontSize: vertical ? 34 : 28, color: "rgba(255,255,255,0.9)" }}>
            {episode.title}
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};
