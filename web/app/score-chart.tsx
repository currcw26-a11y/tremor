"use client";
// Score history: a step line (the score holds until the next change) over Calm/Shaky/Tremor bands.
// Sized to its container in real pixels so text stays readable on phones.
import { useEffect, useRef, useState, useSyncExternalStore } from "react";
import type { ScoreLabel, ScorePoint } from "@/lib/db";
import { BANDS } from "@/lib/score";
import { niceDate } from "@/lib/words";

const H = 180;
const PAD = { top: 10, right: 12, bottom: 24, left: 30 };
// Band edges match config/tremor.yaml (Calm 0-39, Shaky 40-69, Tremor 70-100)
const BAND_ROWS: { label: ScoreLabel; from: number; to: number }[] = [
  { label: "calm", from: 0, to: 40 },
  { label: "shaky", from: 40, to: 70 },
  { label: "tremor", from: 70, to: 100 },
];
// "Now" is read once in the browser. While the page is pre-built on the server it is null.
let clientNow: number | null = null;
const getNow = () => (clientNow ??= Date.now());
const noSubscribe = () => () => {};

const FILL: Record<ScoreLabel, string> = { calm: "var(--calm)", shaky: "var(--shaky)", tremor: "var(--tremor)" };

export function ScoreChart(props: { points: ScorePoint[]; current: number; currentLabel: ScoreLabel }) {
  const ref = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(0);
  const now = useSyncExternalStore(noSubscribe, getNow, () => null);

  useEffect(() => {
    if (!ref.current) return;
    const ro = new ResizeObserver(([e]) => setWidth(e.contentRect.width));
    ro.observe(ref.current);
    return () => ro.disconnect();
  }, []);

  // One container that's always there, so the size tracker never loses it
  return <div ref={ref}>{now !== null && <Chart {...props} now={now} width={width} />}</div>;
}

function Chart({ points, current, currentLabel, now, width }: { points: ScorePoint[]; current: number; currentLabel: ScoreLabel; now: number; width: number }) {
  const [hover, setHover] = useState<number | null>(null);
  const data = points.map((p) => ({ t: new Date(p.computed_at).getTime(), score: p.new_score, label: p.new_label }));
  const first = data[0]?.t ?? now;
  const spanDays = (now - first) / 86_400_000;

  if (data.length < 2 && spanDays < 2) {
    return (
      <p className="rounded-xl border border-dashed border-line p-4 text-sm text-muted">
        Tremor started scoring this trial {data.length ? `on ${niceDate(points[0].computed_at)}` : "recently"}. This
        chart fills in as the score changes over time.
      </p>
    );
  }

  const end = { t: now, score: current, label: currentLabel };
  const all = [...data, end];
  const innerW = Math.max(0, width - PAD.left - PAD.right);
  const innerH = H - PAD.top - PAD.bottom;
  const x = (t: number) => PAD.left + ((t - first) / Math.max(1, now - first)) * innerW;
  const y = (s: number) => PAD.top + innerH - (s / 100) * innerH;

  // Step path: horizontal until the next change, then vertical
  let d = `M ${x(all[0].t)} ${y(all[0].score)}`;
  for (let i = 1; i < all.length; i++) d += ` H ${x(all[i].t)} V ${y(all[i].score)}`;

  const h = hover != null ? data[hover] : null;

  return (
    <figure>
      <div className="relative" onMouseLeave={() => setHover(null)}>
        {width > 0 && (
          <svg width={width} height={H} role="img" aria-label="Worry score over time">
            {BAND_ROWS.map((b) => (
              <g key={b.label}>
                <rect x={PAD.left} width={innerW} y={y(b.to)} height={y(b.from) - y(b.to)} fill={FILL[b.label]} opacity={0.07} />
                <text x={PAD.left + innerW - 4} y={y(b.to) + 13} textAnchor="end" className="fill-muted text-[11px]">
                  {BANDS[b.label].name}
                </text>
              </g>
            ))}
            {[0, 40, 70, 100].map((v) => (
              <g key={v}>
                <line x1={PAD.left} x2={PAD.left + innerW} y1={y(v)} y2={y(v)} stroke="var(--line)" strokeWidth={1} />
                <text x={PAD.left - 6} y={y(v) + 4} textAnchor="end" className="fill-muted text-[11px] tabular-nums">
                  {v}
                </text>
              </g>
            ))}
            <text x={PAD.left} y={H - 6} className="fill-muted text-[11px]">{niceDate(new Date(first).toISOString())}</text>
            <text x={PAD.left + innerW} y={H - 6} textAnchor="end" className="fill-muted text-[11px]">Today</text>
            <path d={d} fill="none" stroke="var(--foreground)" strokeWidth={2} strokeLinejoin="round" />
            {data.map((p, i) => (
              <g key={i} onMouseEnter={() => setHover(i)} onClick={() => setHover(i)} className="cursor-pointer">
                <circle cx={x(p.t)} cy={y(p.score)} r={14} fill="transparent" />
                <circle cx={x(p.t)} cy={y(p.score)} r={hover === i ? 6 : 4.5} fill={FILL[p.label]} stroke="var(--surface)" strokeWidth={2} />
              </g>
            ))}
          </svg>
        )}
        {h && (
          <div
            className="pointer-events-none absolute -translate-x-1/2 rounded-lg bg-foreground px-2 py-1 text-xs text-background shadow"
            style={{ left: Math.min(Math.max(x(h.t), 60), width - 60), top: Math.max(0, y(h.score) - 44) }}
          >
            <span className="font-bold tabular-nums">{h.score}</span> {BANDS[h.label].name} · {niceDate(new Date(h.t).toISOString().slice(0, 10))}
          </div>
        )}
      </div>
      <details className="mt-2 text-sm">
        <summary className="cursor-pointer text-muted">See as a table</summary>
        <table className="mt-2 w-full text-left">
          <thead className="text-muted">
            <tr><th className="py-1 font-medium">Date</th><th className="font-medium">Score</th></tr>
          </thead>
          <tbody>
            {data.map((p, i) => (
              <tr key={i} className="border-t border-line">
                <td className="py-1">{niceDate(new Date(p.t).toISOString().slice(0, 10))}</td>
                <td className="tabular-nums">{p.score} ({BANDS[p.label].name})</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </figure>
  );
}
