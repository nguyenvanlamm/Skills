import type { Look } from "./toon/rig";

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
  color: string;
  side: "left" | "right";
};

/** A change of pose, emotion or head direction at a moment of the audio. */
export type Beat = {
  atMs: number;
  who: string;
  pose?: string;
  emotion?: string;
  face?: number;
};

export type ShotChar = {
  id: string;
  x?: number;
  y?: number;
  s?: number;
  face?: number;
  pose?: string;
  emotion?: string;
  enter?: "left" | "right";
  exit?: "left" | "right";
  walk?: [number, number];
};

export type ShotLabel = { text: string; atMs: number; color?: string };

export type Shot = {
  kind: string;
  startMs: number;
  endMs: number;
  set?: string;
  time?: "day" | "dusk" | "night";
  wall?: string;
  shop?: string;
  tag?: string;
  side?: "left" | "right";
  zoom?: [number, number];
  chars: ShotChar[];
  beats: Beat[];
  labels: ShotLabel[];
};

export type Episode = {
  title: string;
  level: string;
  fps: number;
  durationMs: number;
  audio: string;
  speakers: Speaker[];
  cast: Record<string, Look>;
  vocab: string[];
  lines: Line[];
  shots: Shot[];
  /** One character per frame: 0 closed, 1 half open, 2 open (from the loudness of the voice). */
  mouth: string;
};
