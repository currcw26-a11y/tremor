import Link from "next/link";
import type { Change, Trial } from "@/lib/db";
import { STATUS, describeChange, niceDate, phaseLabel, statusLabel } from "@/lib/words";
import { TimeAgo } from "./time-ago";
import { ScoreBadge } from "./score";
import { ChangeDiff } from "./change-diff";

const TONE = { good: "bg-calm", neutral: "bg-muted/50", bad: "bg-tremor" };
const SEVERITY = { high: "bg-tremor", medium: "bg-shaky", low: "bg-line" };

export function Ticker({ symbol }: { symbol: string }) {
  return (
    <span className="inline-block rounded-[3px] border border-line bg-background px-1.5 py-px font-mono text-[11.5px] font-semibold leading-5 tracking-wider text-foreground">
      {symbol}
    </span>
  );
}

export function StatusPill({ status }: { status: string }) {
  const tone = STATUS[status]?.tone ?? "neutral";
  return (
    <span className="inline-flex items-center gap-1.5 text-xs text-ink-2">
      <span className={`h-1.5 w-1.5 rounded-full ${TONE[tone]}`} aria-hidden />
      {statusLabel(status)}
    </span>
  );
}

export function TrialRow({ t }: { t: Trial }) {
  return (
    <li className="border-b border-line last:border-b-0">
      <Link
        href={`/trials/${t.nct_id}`}
        className="group -mx-3 grid grid-cols-[minmax(0,1fr)_auto] items-start gap-x-4 gap-y-1 rounded-md px-3 py-4 transition-colors hover:bg-surface"
      >
        <div className="flex min-w-0 flex-wrap items-center gap-2 text-sm text-ink-2">
          <Ticker symbol={t.ticker} />
          <span className="truncate">{t.sponsor_name}</span>
        </div>
        <ScoreBadge score={t.score} label={t.score_label} />
        <p className="col-span-2 font-medium leading-snug text-foreground">
          {t.title} <span className="nudge text-muted opacity-0 transition-opacity group-hover:opacity-100">→</span>
        </p>
        <div className="col-span-2 mt-1 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted">
          <StatusPill status={t.overall_status} />
          <span>{phaseLabel(t.phases)}</span>
          {t.enrollment != null && <span>{t.enrollment.toLocaleString()} patients</span>}
          <span>Main results {niceDate(t.primary_completion_date)}</span>
        </div>
      </Link>
    </li>
  );
}

export function ChangeRow({ c, showTrial = true }: { c: Change; showTrial?: boolean }) {
  // In feeds (showTrial) the explanation is trimmed to 2 lines; the trial page shows it all.
  const { text, severity } = describeChange(c);
  return (
    <li className="flex gap-3 border-b border-line py-4 last:border-b-0">
      <span className={`mt-[7px] h-2 w-2 shrink-0 rounded-full ${SEVERITY[severity]}`} aria-hidden />
      <div className="min-w-0">
        {showTrial && c.trials && (
          <Link href={`/trials/${c.nct_id}`} className="group flex items-center gap-2">
            <Ticker symbol={c.trials.ticker} />
            <span className="min-w-0 flex-1 truncate text-sm text-ink-2 group-hover:text-foreground">{c.trials.title}</span>
          </Link>
        )}
        <p className={`font-medium leading-snug ${showTrial ? "mt-1.5" : ""}`}>{text}</p>
        {c.explanation && (
          <p className={`mt-1.5 text-sm leading-relaxed text-ink-2 ${showTrial ? "line-clamp-2" : ""}`}>{c.explanation}</p>
        )}
        <p className="mt-1.5 text-xs text-muted">
          Spotted <TimeAgo iso={c.detected_at} />
          {c.explanation && <span title="Written by AI from the facts above, then checked by code"> · AI-written summary</span>}
        </p>
        {!showTrial && <ChangeDiff c={c} />}
      </div>
    </li>
  );
}

export function Empty({ children }: { children: React.ReactNode }) {
  return <div className="border-y border-line py-6 text-sm text-muted">{children}</div>;
}
