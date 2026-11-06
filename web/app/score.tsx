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

/** The worry score badge: number + word + shape + color. */
export function ScoreBadge({ score, label, size = "sm" }: { score: number; label: ScoreLabel; size?: "sm" | "lg" }) {
  const band = BANDS[label] ?? BANDS.calm;
  if (size === "lg") {
    return (
      <div className={`inline-flex items-center gap-4 rounded-2xl ${band.tint} px-5 py-4`}>
        <span className={`text-5xl font-black tabular-nums leading-none ${band.color}`}>{score}</span>
        <span>
          <span className={`flex items-center gap-1.5 text-lg font-bold ${band.color}`}>
            <Shape label={label} size={12} />
            {band.name}
          </span>
          <span className="block text-sm text-muted">worry score, out of 100</span>
        </span>
      </div>
    );
  }
  return (
    <span
      className={`inline-flex shrink-0 items-center gap-1.5 rounded-full ${band.tint} px-2 py-0.5 text-xs font-bold ${band.color}`}
      title={`Worry score ${score} out of 100: ${band.name}`}
    >
      <Shape label={label} size={9} />
      <span className="tabular-nums">{score}</span>
      <span className="font-semibold">{band.name}</span>
    </span>
  );
}

/** "Why this score": every reason with its points, adding up to the total. */
export function Reasons({ reasons, score }: { reasons: Reason[]; score: number }) {
  if (!reasons.length)
    return <p className="text-muted">No warning signs right now. That&apos;s why the score is 0.</p>;
  const total = reasons.reduce((sum, r) => sum + r.points, 0);
  return (
    <div className="overflow-hidden rounded-xl border border-line bg-surface">
      <ul className="divide-y divide-line">
        {reasons.map((r, i) => (
          <li key={i} className="flex items-start justify-between gap-4 p-3">
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
            <span className="shrink-0 font-bold tabular-nums">+{round(r.points)}</span>
          </li>
        ))}
      </ul>
      <div className="flex justify-between border-t border-line bg-background px-3 py-2 text-sm font-bold">
        <span>Worry score</span>
        <span className="tabular-nums">
          {Math.min(100, Math.round(total))}
          {Math.round(total) !== score && <span className="font-normal text-muted"> (capped at {score})</span>}
        </span>
      </div>
    </div>
  );
}

const round = (n: number) => Math.round(n * 10) / 10;
