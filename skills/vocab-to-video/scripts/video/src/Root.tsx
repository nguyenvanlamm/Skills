import { CalculateMetadataFunction, Composition } from "remotion";
import { Thumbnail, ThumbnailProps } from "./Thumbnail";
import { Toon } from "./Toon";
import { Sheet } from "./toon/Sheet";
import { Episode } from "./types";

// Real episodes come in through --props=<episode.json> and --public-dir=<episode>/public.
const placeholder: Episode = {
  title: "Titre de l'épisode",
  level: "A2",
  fps: 60,
  durationMs: 6000,
  audio: "",
  speakers: [
    { id: "lea", name: "Léa", color: "#FF8A5B", side: "left" },
    { id: "hugo", name: "Hugo", color: "#4FC3F7", side: "right" },
  ],
  cast: {
    lea: { skin: "fair", outfit: "sweater", color: "#E0A22B", hair: "long", hair_col: "#6B3F22" },
    hugo: { skin: "tan", outfit: "hoodie", color: "#2F4A7A", hair: "short", glasses: true },
  },
  vocab: ["bonjour"],
  lines: [
    {
      speaker: "lea",
      text: "Bonjour Hugo !",
      startMs: 1200,
      endMs: 2600,
      words: [
        { text: "Bonjour", startMs: 1200, endMs: 1800, isVocab: true },
        { text: "Hugo !", startMs: 1800, endMs: 2600, isVocab: false },
      ],
    },
  ],
  shots: [
    {
      kind: "wide",
      startMs: 0,
      endMs: 3200,
      set: "street",
      time: "day",
      tag: "PARIS",
      chars: [{ id: "lea", enter: "left" }, { id: "hugo" }],
      beats: [{ atMs: 1200, who: "lea", pose: "wave", emotion: "happy" }],
      labels: [{ text: "bonjour", atMs: 1300 }],
    },
    { kind: "closeup", startMs: 3200, endMs: 6000, set: "home", time: "night", chars: [{ id: "hugo" }], beats: [], labels: [] },
  ],
  mouth: "",
};

const thumbPlaceholder: ThumbnailProps = {
  text: "BONJOUR · Dialogue A2",
  level: "A2",
  vocab: ["bonjour"],
  speakers: placeholder.speakers,
  cast: placeholder.cast,
};

const calculateMetadata: CalculateMetadataFunction<Episode> = ({ props }) => ({
  fps: props.fps,
  durationInFrames: Math.max(1, Math.ceil((props.durationMs / 1000) * props.fps)),
});

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="Toon16x9"
        component={Toon}
        width={1920}
        height={1080}
        fps={60}
        durationInFrames={120}
        defaultProps={placeholder}
        calculateMetadata={calculateMetadata}
      />
      <Composition
        id="Toon9x16"
        component={Toon}
        width={1080}
        height={1920}
        fps={60}
        durationInFrames={120}
        defaultProps={placeholder}
        calculateMetadata={calculateMetadata}
      />
      <Composition
        id="Thumbnail16x9"
        component={Thumbnail}
        width={1280}
        height={720}
        fps={60}
        durationInFrames={1}
        defaultProps={thumbPlaceholder}
      />
      <Composition
        id="Cover9x16"
        component={Thumbnail}
        width={1080}
        height={1920}
        fps={60}
        durationInFrames={1}
        defaultProps={thumbPlaceholder}
      />
      {/* Every pose and emotion on one page, to check the puppet after changing it. */}
      <Composition id="PuppetSheet" component={Sheet} width={1800} height={1000} fps={60} durationInFrames={1} />
    </>
  );
};
