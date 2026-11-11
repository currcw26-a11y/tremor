import type { Reason, ScoreLabel } from "@/lib/db";
import { BANDS } from "@/lib/score";
import { niceDate } from "@/lib/words";

export function Shape({ label, size = 10 }: { label: ScoreLabel; size?: number }) {
  const shape = BANDS[label]?.shape ?? "circle";
  return (
    <svg width={size} height={size} viewBox="0 0 10 10" aria-hidden className="shrink-0 fill-current">
      {shape === "circle" && <circle cx="5" cy="5" r="4.5" />}
      {shape === "triangle" && <path d="M5 0.5 L9.7 9.3 H0.3 Z" />}
      {shape === "diamond" && <path d="M5 0 L10 5 L5 10 L0 5 Z" />}
    </svg>
  );
}

/** The worry score, small: shape + number + word. Color is never the only cue. */
export function ScoreBadge({ score, label }: { score: number; label: ScoreLabel; size?: "sm" }) {
  const band = BANDS[label] ?? BANDS.calm;
  return (
    <span className="inline-flex shrink-0 items-center gap-1.5 text-sm" title={`Worry score ${score} out of 100: ${band.name}`}>
      <span className={band.mark}>
        <Shape label={label} size={9} />
      </span>
      <span className="font-mono font-semibold tabular-nums text-foreground">{score}</span>
      <span className={`font-medium ${band.color}`}>{band.name}</span>
    </span>
  );
}

const EDGES = [
  { label: "calm" as const, from: 0, to: 40 },
  { label: "shaky" as const, from: 40, to: 70 },
  { label: "tremor" as const, from: 70, to: 100 },
];

/** The worry score, big: the number, its band, and where it sits on the 0-100 scale. */
export function ScoreHero({ score, label }: { score: number; label: ScoreLabel }) {
  const band = BANDS[label] ?? BANDS.calm;
  return (
    <div>
      <div className="flex items-end gap-4">
        <span className="font-serif text-7xl font-medium leading-[0.8] tabular-nums tracking-tight">{score}</span>
        <span className="pb-1">
          <span className={`flex items-center gap-1.5 text-lg font-semibold ${band.color}`}>
            <span className={band.mark}>
              <Shape label={label} size={12} />
            </span>
            {band.name}
          </span>
          <span className="block text-sm text-muted">worry score, out of 100</span>
        </span>
      </div>
      {/* The scale: three bands, with a marker that slides to this trial's score */}
      <div className="relative mt-6 max-w-md" role="img" aria-label={`${score} on a scale from 0 to 100`}>
        <div className="flex h-2 gap-[3px]">
          {EDGES.map((e) => (
            <span
              key={e.label}
              style={{ flexGrow: e.to - e.from, transformOrigin: "left", animation: "grow-x .6s cubic-bezier(.2,.7,.2,1) both" }}
              className={`rounded-full ${e.label === label ? BANDS[e.label].mark.replace("text-", "bg-") : "bg-line"}`}
            />
          ))}
        </div>
        <span
          className="absolute -top-1.5 h-5 w-[3px] -translate-x-1/2 rounded-full bg-foreground"
          style={{ left: `${Math.min(100, Math.max(0, score))}%`, animation: "slide-in .8s cubic-bezier(.2,.7,.2,1) .15s both" }}
          aria-hidden
        />
        <div className="relative mt-2 h-4 font-mono text-[11px] text-muted">
          {[0, 40, 70, 100].map((v) => (
            <span key={v} className="absolute -translate-x-1/2 first:translate-x-0 last:-translate-x-full" style={{ left: `${v}%` }}>
              {v}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}

/** "Why this score": every reason with its points, adding up to the total. */
export function Reasons({ reasons, score }: { reasons: Reason[]; score: number }) {
  if (!reasons.length)
    return <p className="text-muted">No warning signs right now. That&apos;s why the score is 0.</p>;
  const total = reasons.reduce((sum, r) => sum + r.points, 0);
  return (
    <div>
      <ul className="divide-y divide-line border-y border-line">
        {reasons.map((r, i) => (
          <li key={i} className="flex items-start justify-between gap-4 py-3">
            <div>
              <p className="font-medium">{r.label}</p>
              <p className="mt-0.5 text-xs text-muted">
                {r.type === "trial_stopped"
                  ? "Stopped trials go straight to red"
                  : r.fades
                    ? `Since ${niceDate(r.occurred)} · was worth ${round(r.base_points)}, fading over time`
                    : "Counts until it's fixed"}
              </p>
            </div>
            <span className="shrink-0 font-mono font-semibold tabular-nums">+{round(r.points)}</span>
          </li>
        ))}
      </ul>
      <div className="flex justify-between py-3 text-sm font-semibold">
        <span>Worry score</span>
        <span className="font-mono tabular-nums">
          {Math.min(100, Math.round(total))}
          {Math.round(total) !== score && <span className="font-normal text-muted"> (capped at {score})</span>}
        </span>
      </div>
    </div>
  );
}

const round = (n: number) => Math.round(n * 10) / 10;
