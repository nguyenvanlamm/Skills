import { CalculateMetadataFunction, Composition } from "remotion";
import { Dialogue } from "./Dialogue";
import { Thumbnail, ThumbnailProps } from "./Thumbnail";
import { Episode } from "./types";

// Real episodes come in through --props=<episode.json> and --public-dir=<episode>/public.
const placeholder: Episode = {
  title: "Titre de l'épisode",
  level: "A2",
  fps: 60,
  durationMs: 4000,
  audio: "",
  speakers: [
    { id: "lea", name: "Léa", image: "", color: "#FF8A5B", side: "left" },
    { id: "hugo", name: "Hugo", image: "", color: "#4FC3F7", side: "right" },
  ],
  vocab: ["bonjour"],
  lines: [
    {
      speaker: "lea",
      text: "Bonjour Hugo !",
      startMs: 1200,
      endMs: 2600,
      words: [
        { text: "Bonjour", startMs: 1200, endMs: 1800, isVocab: true },
        { text: "Hugo !", startMs: 1800, endMs: 2600, isVocab: false },
      ],
    },
  ],
};

const thumbPlaceholder: ThumbnailProps = {
  text: "BONJOUR · Dialogue A2",
  level: "A2",
  vocab: ["bonjour"],
  speakers: placeholder.speakers,
};

const calculateMetadata: CalculateMetadataFunction<Episode> = ({ props }) => ({
  fps: props.fps,
  durationInFrames: Math.max(1, Math.ceil((props.durationMs / 1000) * props.fps)),
});

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="Dialogue16x9"
        component={Dialogue}
        width={1920}
        height={1080}
        fps={60}
        durationInFrames={120}
        defaultProps={placeholder}
        calculateMetadata={calculateMetadata}
      />
      <Composition
        id="Dialogue9x16"
        component={Dialogue}
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
    </>
  );
};
