export type Word = {
  text: string;
  startMs: number;
  endMs: number;
  isVocab: boolean;
};

export type Line = {
  speaker: string;
  text: string;
  startMs: number;
  endMs: number;
  words: Word[];
  kind?: "hook";
};

export type Speaker = {
  id: string;
  name: string;
  image: string;
  color: string;
  side: "left" | "right";
};

export type Episode = {
  title: string;
  level: string;
  fps: number;
  durationMs: number;
  audio: string;
  speakers: Speaker[];
  vocab: string[];
  lines: Line[];
};
