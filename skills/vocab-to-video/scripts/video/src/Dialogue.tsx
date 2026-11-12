import { loadFont } from "@remotion/fonts";
import { Audio } from "@remotion/media";
import { useWindowedAudioData, visualizeAudio } from "@remotion/media-utils";
import {
  AbsoluteFill,
  Img,
  interpolate,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { Episode, Line, Speaker } from "./types";

const FONT = "Be Vietnam Pro";
const VOCAB = "#FFD54A";
const BG = "#0D1326";

const weights: [string, string][] = [
  ["500", "BeVietnamPro-Medium.ttf"],
  ["600", "BeVietnamPro-SemiBold.ttf"],
  ["800", "BeVietnamPro-ExtraBold.ttf"],
];

let fontsRequested = false;
/** Fonts ship in the episode's public folder, so they are only requested for a real episode. */
const ensureFonts = (available: boolean) => {
  if (fontsRequested || !available) return;
  fontsRequested = true;
  weights.forEach(([weight, file]) =>
    loadFont({ family: FONT, url: staticFile(`fonts/${file}`), weight }),
  );
};

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

/** 0..1: how much this speaker "has the floor" at time t (soft edges around their lines). */
const presence = (lines: Line[], speaker: string, t: number) => {
  let best = 0;
  for (const l of lines) {
    if (l.speaker !== speaker) continue;
    if (t < l.startMs - 250 || t > l.endMs + 350) continue;
    best = Math.max(
      best,
      interpolate(t, [l.startMs - 250, l.startMs, l.endMs, l.endMs + 350], [0, 1, 1, 0], clamp),
    );
  }
  return best;
};

const Portrait: React.FC<{
  speaker: Speaker;
  size: number;
  active: number;
  amp: number;
}> = ({ speaker, size, active, amp }) => {
  const scale = 0.94 + 0.06 * active + 0.035 * active * amp;
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", width: size }}>
      <div
        style={{
          width: size,
          height: size,
          borderRadius: "50%",
          overflow: "hidden",
          transform: `scale(${scale})`,
          border: `${Math.round(size * 0.022)}px solid ${speaker.color}`,
          borderColor: active > 0.05 ? speaker.color : "rgba(255,255,255,0.18)",
          boxShadow: `0 0 ${60 * active + 40 * active * amp}px ${speaker.color}${active > 0.05 ? "88" : "00"}`,
          opacity: 0.45 + 0.55 * active,
          filter: `saturate(${0.35 + 0.65 * active})`,
          backgroundColor: "#1b2340",
        }}
      >
        {speaker.image ? (
          <Img src={staticFile(speaker.image)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
        ) : null}
      </div>
      <div
        style={{
          marginTop: size * 0.07,
          fontFamily: FONT,
          fontWeight: 600,
          fontSize: size * 0.105,
          color: speaker.color,
          opacity: 0.55 + 0.45 * active,
        }}
      >
        {speaker.name}
      </div>
    </div>
  );
};

const Bars: React.FC<{
  values: number[];
  width: number;
  height: number;
  color: string;
}> = ({ values, width, height, color }) => {
  const gap = Math.max(4, Math.round(width / values.length / 3));
  const barW = (width - gap * (values.length - 1)) / values.length;
  return (
    <div style={{ width, height, display: "flex", alignItems: "center", gap }}>
      {values.map((v, i) => (
        <div
          key={i}
          style={{
            width: barW,
            height: Math.max(barW, v * height),
            borderRadius: barW,
            backgroundColor: color,
            opacity: 0.55 + 0.45 * v,
          }}
        />
      ))}
    </div>
  );
};

const Caption: React.FC<{
  line: Line;
  speaker: Speaker;
  t: number;
  vertical: boolean;
}> = ({ line, speaker, t, vertical }) => {
  const chars = line.text.length;
  const hook = line.kind === "hook";
  const base = vertical
    ? chars <= 40 ? 74 : chars <= 80 ? 62 : 52
    : chars <= 55 ? 78 : chars <= 95 ? 66 : 56;
  // The opening hook is a headline: bigger and bolder than a normal line.
  const fontSize = hook ? Math.round(base * (vertical ? 1.3 : 1.35)) : base;
  const enter = interpolate(t, [line.startMs - 250, line.startMs], [hook ? 1 : 0, 1], clamp);
  return (
    <div
      style={{
        opacity: enter,
        transform: `translateY(${(1 - enter) * 18}px)`,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
      }}
    >
      <div
        style={{
          fontFamily: FONT,
          fontWeight: 600,
          fontSize: fontSize * 0.46,
          color: BG,
          backgroundColor: speaker.color,
          padding: `${fontSize * 0.1}px ${fontSize * 0.36}px`,
          borderRadius: fontSize,
          marginBottom: fontSize * 0.42,
          display: hook ? "none" : undefined,
        }}
      >
        {speaker.name}
      </div>
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          justifyContent: "center",
          columnGap: fontSize * 0.36,
          rowGap: fontSize * 0.14,
          fontFamily: FONT,
          fontSize,
          lineHeight: 1.22,
        }}
      >
        {line.words.map((w, i) => {
          const said = interpolate(t, [w.startMs - 50, w.startMs + 70], [0, 1], clamp);
          const speaking = t >= w.startMs - 30 && t < w.endMs ? 1 : 0;
          const base = w.isVocab ? VOCAB : "#FFFFFF";
          return (
            <span
              key={i}
              style={{
                display: "inline-block",
                fontWeight: w.isVocab || hook ? 800 : 500,
                color: base,
                // Words not yet spoken are dimmed; the hook stays readable from the first frame.
                opacity: hook ? 0.72 + 0.28 * said : (w.isVocab ? 0.55 : 0.34) + (w.isVocab ? 0.45 : 0.66) * said,
                transform: `scale(${1 + 0.06 * speaking})`,
                borderBottom: w.isVocab ? `${Math.round(fontSize * 0.07)}px solid ${VOCAB}` : undefined,
                textShadow: speaking ? `0 0 ${fontSize * 0.5}px ${speaker.color}` : undefined,
                whiteSpace: "nowrap",
              }}
            >
              {w.text}
            </span>
          );
        })}
      </div>
    </div>
  );
};

export const Dialogue: React.FC<Episode> = (episode) => {
  const frame = useCurrentFrame();
  const { fps, width, height, durationInFrames } = useVideoConfig();
  const vertical = height > width;
  const t = (frame / fps) * 1000;

  ensureFonts(Boolean(episode.audio));

  const { lines, speakers } = episode;
  const left = speakers.find((s) => s.side === "left") ?? speakers[0];
  const right = speakers.find((s) => s.side === "right") ?? speakers[1];

  // The caption shows a line from just before it starts until the next one takes over.
  let current: Line | null = null;
  for (const l of lines) {
    if (t >= l.startMs - 250) current = l;
  }
  const currentSpeaker = current ? speakers.find((s) => s.id === current!.speaker) ?? left : left;
  const aLeft = presence(lines, left.id, t);
  const aRight = presence(lines, right.id, t);
  const barColor = aRight > aLeft ? right.color : aLeft > 0 ? left.color : "rgba(255,255,255,0.35)";

  const barCount = vertical ? 18 : 44;
  const values = useSpectrum(episode.audio, frame, fps, barCount);
  const amp = values.length ? Math.max(...values) : 0;

  const portrait = vertical ? 310 : 380;
  const stageY = vertical ? 1330 : 770;
  const sideX = vertical ? 50 : 150;
  const waveW = width - 2 * (sideX + portrait) - (vertical ? 60 : 160);
  const titleIn = interpolate(t, [0, 400], [0, 1], clamp);
  const progress = frame / Math.max(1, durationInFrames - 1);

  return (
    <AbsoluteFill
      style={{
        backgroundColor: BG,
        backgroundImage: `radial-gradient(circle at ${vertical ? "22% 70%" : "17% 72%"}, ${left.color}${hex(0.2 * aLeft)} 0%, transparent 42%), radial-gradient(circle at ${vertical ? "78% 70%" : "83% 72%"}, ${right.color}${hex(0.2 * aRight)} 0%, transparent 42%), linear-gradient(180deg, #111936 0%, ${BG} 60%)`,
        fontFamily: FONT,
      }}
    >
      {episode.audio ? <Audio src={staticFile(episode.audio)} /> : null}

      <div
        style={{
          position: "absolute",
          top: vertical ? 120 : 44,
          left: 0,
          right: 0,
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          gap: 22,
          opacity: titleIn,
          padding: "0 60px",
        }}
      >
        <div
          style={{
            fontWeight: 800,
            fontSize: vertical ? 34 : 30,
            color: BG,
            backgroundColor: VOCAB,
            borderRadius: 12,
            padding: "6px 18px",
          }}
        >
          {episode.level}
        </div>
        <div style={{ fontWeight: 600, fontSize: vertical ? 38 : 34, color: "rgba(255,255,255,0.82)" }}>
          {episode.title}
        </div>
      </div>

      <div
        style={{
          position: "absolute",
          top: vertical ? 240 : 120,
          height: vertical ? 780 : 420,
          left: vertical ? 60 : 170,
          right: vertical ? 60 : 170,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        {current ? <Caption line={current} speaker={currentSpeaker} t={t} vertical={vertical} /> : null}
      </div>

      <div style={{ position: "absolute", left: sideX, top: stageY - portrait / 2 }}>
        <Portrait speaker={left} size={portrait} active={aLeft} amp={amp} />
      </div>
      <div style={{ position: "absolute", right: sideX, top: stageY - portrait / 2 }}>
        <Portrait speaker={right} size={portrait} active={aRight} amp={amp} />
      </div>
      <div
        style={{
          position: "absolute",
          left: (width - waveW) / 2,
          top: stageY - (vertical ? 120 : 140),
        }}
      >
        <Bars values={values} width={waveW} height={vertical ? 240 : 280} color={barColor} />
      </div>

      <div style={{ position: "absolute", left: 0, bottom: 0, height: 8, width: "100%", backgroundColor: "rgba(255,255,255,0.08)" }}>
        <div style={{ height: "100%", width: `${progress * 100}%`, backgroundColor: VOCAB }} />
      </div>
    </AbsoluteFill>
  );
};

const hex = (alpha: number) =>
  Math.round(Math.min(1, Math.max(0, alpha)) * 255)
    .toString(16)
    .padStart(2, "0");

/** Mirrored voice spectrum (lows in the middle), 0..1 per bar. Empty until the audio has loaded. */
const useSpectrum = (audio: string, frame: number, fps: number, bars: number): number[] => {
  const { audioData, dataOffsetInSeconds } = useWindowedAudioData({
    src: audio ? staticFile(audio) : staticFile("audio.wav"),
    frame,
    fps,
    windowInSeconds: 30,
  });
  const half = Math.ceil(bars / 2);
  if (!audio || !audioData) {
    return new Array(half * 2).fill(0);
  }
  const bins = visualizeAudio({
    fps,
    frame,
    audioData,
    numberOfSamples: 256,
    optimizeFor: "speed",
    dataOffsetInSeconds,
  });
  // Speech lives below ~5 kHz: at 48 kHz that is roughly the first 52 of 256 bins.
  const used = 52;
  const per = used / half;
  const side: number[] = [];
  for (let i = 0; i < half; i++) {
    const from = Math.floor(i * per);
    const to = Math.max(from + 1, Math.floor((i + 1) * per));
    let peak = 0;
    for (let b = from; b < to; b++) peak = Math.max(peak, bins[b] ?? 0);
    const db = Math.log10(peak + 1e-6);
    side.push(Math.min(1, Math.max(0, (db + 3.1) / 2.5)));
  }
  return [...side.slice().reverse(), ...side];
};
