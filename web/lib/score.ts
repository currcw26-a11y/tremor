import type { ScoreLabel } from "./db";

// How each score band looks. Color is never the only cue: each has a word and a shape.
export const BANDS: Record<ScoreLabel, { name: string; shape: "circle" | "triangle" | "diamond"; color: string; tint: string; meaning: string }> = {
  calm: { name: "Calm", shape: "circle", color: "text-calm", tint: "bg-calm/10", meaning: "No strong warning signs right now." },
  shaky: { name: "Shaky", shape: "triangle", color: "text-shaky", tint: "bg-shaky/10", meaning: "Some warning signs worth watching." },
  tremor: { name: "Tremor", shape: "diamond", color: "text-tremor", tint: "bg-tremor/10", meaning: "Several warning signs, or the trial stopped." },
};
