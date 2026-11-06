import Link from "next/link";
import type { Change, Trial } from "@/lib/db";
import { STATUS, describeChange, niceDate, phaseLabel, statusLabel } from "@/lib/words";
import { TimeAgo } from "./time-ago";
import { ScoreBadge } from "./score";

const TONE = { good: "bg-calm/10 text-calm", neutral: "bg-line text-muted", bad: "bg-tremor/10 text-tremor" };
const SEVERITY = { high: "bg-tremor", medium: "bg-shaky", low: "bg-line" };

export function Ticker({ symbol }: { symbol: string }) {
  return (
    <span className="rounded-md bg-foreground px-1.5 py-0.5 font-mono text-xs font-bold text-background">
      {symbol}
    </span>
  );
}

export function StatusPill({ status }: { status: string }) {
  const tone = STATUS[status]?.tone ?? "neutral";
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${TONE[tone]}`}>{statusLabel(status)}</span>
  );
}

export function TrialRow({ t }: { t: Trial }) {
  return (
    <li>
      <Link
        href={`/trials/${t.nct_id}`}
        className="block rounded-xl border border-line bg-surface p-4 transition hover:border-foreground/30"
      >
        <div className="flex items-start justify-between gap-2">
          <div className="flex min-w-0 flex-wrap items-center gap-2">
            <Ticker symbol={t.ticker} />
            <span className="text-sm font-medium text-muted">{t.sponsor_name}</span>
          </div>
          <ScoreBadge score={t.score} label={t.score_label} />
        </div>
        <p className="mt-2 font-semibold leading-snug">{t.title}</p>
        <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted">
          <StatusPill status={t.overall_status} />
          <span>{phaseLabel(t.phases)}</span>
          {t.enrollment != null && <span>{t.enrollment.toLocaleString()} patients</span>}
          <span>Main results: {niceDate(t.primary_completion_date)}</span>
        </div>
      </Link>
    </li>
  );
}

export function ChangeRow({ c, showTrial = true }: { c: Change; showTrial?: boolean }) {
  // In feeds (showTrial) the explanation is trimmed to 2 lines; the trial page shows it all.
  const { text, severity } = describeChange(c);
  return (
    <li className="flex gap-3 rounded-xl border border-line bg-surface p-4">
      <span className={`mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full ${SEVERITY[severity]}`} aria-hidden />
      <div className="min-w-0">
        {showTrial && c.trials && (
          <Link href={`/trials/${c.nct_id}`} className="flex items-center gap-2 hover:underline">
            <Ticker symbol={c.trials.ticker} />
            <span className="min-w-0 flex-1 truncate text-sm font-semibold">{c.trials.title}</span>
            <ScoreBadge score={c.trials.score} label={c.trials.score_label} />
          </Link>
        )}
        <p className={`font-medium ${showTrial ? "mt-1.5" : ""}`}>{text}</p>
        {c.explanation && (
          <>
            <p className={`mt-1.5 text-sm leading-relaxed text-muted ${showTrial ? "line-clamp-2" : ""}`}>
              {c.explanation}
            </p>
            <p className="mt-0.5 text-xs text-muted opacity-70">
              AI-written from the facts above{showTrial && " · tap the trial to read more"}
            </p>
          </>
        )}
        <p className="mt-1 text-xs text-muted">
          Spotted <TimeAgo iso={c.detected_at} />
        </p>
      </div>
    </li>
  );
}

export function Empty({ children }: { children: React.ReactNode }) {
  return <div className="rounded-xl border border-dashed border-line p-6 text-center text-muted">{children}</div>;
}
