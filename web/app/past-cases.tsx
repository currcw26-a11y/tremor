// "Upside and downside": what happened after similar warning signs in the past.
// Every number and sentence comes from the pipeline (pipeline/tremor/outlook.py); this file only lays it out.
import Link from "next/link";
import type { Company, Outlook, PastCases } from "@/lib/db";
import { niceDate } from "@/lib/words";
import { Shape } from "./score";

const TITLES: Record<string, string> = {
  layoffs: "Layoffs",
  key_exec_departure: "A key executive left",
  repeat_exec_departure: "A second key executive left within 6 months",
  trial_stopped: "A trial was stopped early",
  primary_outcome_changed: "Main goal changed",
  enrollment_cut: "Fewer patients",
  date_delayed: "Dates pushed back",
  results_overdue: "Results overdue",
  insider_selling_cluster: "Several insiders sold shares",
  fda_advisory_meeting: "FDA advisory meeting",
  job_postings_drop: "Fewer clinical job postings",
  rival_trial_failed: "A rival drug's trial failed",
};

const SURE: Record<string, string> = { low: "Low", medium: "Medium", high: "High" };

/** One mark per past case: red diamond = a trial was stopped within a year, green circle = none was. */
export function Dots({
  bad,
  fine,
  cases,
}: {
  bad: number;
  fine: number;
  cases?: { outcome: "bad" | "fine"; title: string }[];
}) {
  const marks = cases ?? [
    ...Array.from({ length: bad }, () => ({ outcome: "bad" as const, title: "A trial was stopped within a year" })),
    ...Array.from({ length: fine }, () => ({ outcome: "fine" as const, title: "No trial stopped within a year" })),
  ];
  return (
    <div>
      <div
        role="img"
        aria-label={`${bad} went badly, ${fine} were fine`}
        className="flex flex-wrap gap-[3px]"
      >
        {marks.map((m, i) => (
          <span key={i} title={m.title} className={m.outcome === "bad" ? "text-tremor" : "text-calm"}>
            <Shape label={m.outcome === "bad" ? "tremor" : "calm"} size={9} />
          </span>
        ))}
      </div>
      <p className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted">
        <span className="flex items-center gap-1">
          <span className="text-tremor"><Shape label="tremor" size={9} /></span>
          Went badly: a trial was stopped within a year ({bad})
        </span>
        <span className="flex items-center gap-1">
          <span className="text-calm"><Shape label="calm" size={9} /></span>
          Fine: no trial stopped ({fine})
        </span>
      </p>
    </div>
  );
}

function SignalCard({ s }: { s: PastCases }) {
  const showDots = s.has_history && (s.fine ?? 0) > 0;
  return (
    <li className="rounded-xl border border-line bg-surface p-4">
      <h3 className="font-bold">{TITLES[s.type] ?? s.type}</h3>
      {s.sentences.map((t, i) => (
        <p key={i} className="mt-2 text-sm leading-relaxed">{t}</p>
      ))}
      {showDots && (
        <div className="mt-3">
          <Dots bad={s.bad ?? 0} fine={s.fine ?? 0} />
        </div>
      )}
      {s.has_history && s.confidence && (
        <p className="mt-3 text-sm">
          <span className="font-semibold">How sure are we: </span>
          {SURE[s.confidence]}, based on {s.cases} past cases.
        </p>
      )}
    </li>
  );
}

export function OutlookSection({ outlook, company }: { outlook: Outlook | null | undefined; company: Company | null }) {
  if (!outlook) return null;
  const withHistory = outlook.signals.filter((s) => s.has_history);
  const without = outlook.signals.filter((s) => !s.has_history);
  const months = company?.runway_months == null ? null : Math.round(company.runway_months);
  const ne = outlook.next_event;

  return (
    <section className="mt-8">
      <h2 className="text-lg font-bold">Upside and downside</h2>
      <p className="text-sm text-muted">
        What happened after similar warning signs in the past. This is history, not a prediction.
      </p>

      {outlook.signals.length === 0 && (
        <p className="mt-3 rounded-xl border border-line bg-surface p-4 text-sm">
          No warning signs right now, so there are no past cases to compare.
        </p>
      )}
      {withHistory.length > 0 && (
        <ul className="mt-3 space-y-3">
          {withHistory.map((s) => (
            <SignalCard key={s.type} s={s} />
          ))}
        </ul>
      )}
      {without.length > 0 && (
        <ul className="mt-3 space-y-3">
          {without.map((s) => (
            <SignalCard key={s.type} s={s} />
          ))}
        </ul>
      )}

      <dl className="mt-3 grid gap-2 sm:grid-cols-3">
        <div className="rounded-xl border border-line bg-surface p-3">
          <dt className="text-xs text-muted">How big a deal for them</dt>
          <dd className="mt-1 text-sm">{outlook.stakes.text}</dd>
        </div>
        <div className="rounded-xl border border-line bg-surface p-3">
          <dt className="text-xs text-muted">Money left</dt>
          <dd className="mt-1 text-sm">
            {months != null ? (
              <>
                About {months < 1 ? "under 1" : months} month{months === 1 ? "" : "s"} at its recent spending rate.{" "}
                {months < 18 && "If this goes badly, it may need to sell new shares, which usually makes each share worth less. "}
              </>
            ) : company?.finances_as_of ? (
              "It isn't burning cash right now. "
            ) : (
              "We couldn't find recent cash numbers. "
            )}
            {company && (
              <Link href={`/companies/${company.ticker}`} className="underline">
                Details
              </Link>
            )}
          </dd>
        </div>
        <div className="rounded-xl border border-line bg-surface p-3">
          <dt className="text-xs text-muted">When we&apos;ll find out</dt>
          <dd className="mt-1 text-sm">
            {!ne
              ? "No upcoming results date listed."
              : ne.passed
                ? `Main results were due around ${niceDate(ne.date)}. That date has passed and no results are posted yet.`
                : `Main results are expected around ${niceDate(ne.date)}.`}
          </dd>
        </div>
      </dl>
      {outlook.notes.map((n, i) => (
        <p key={i} className="mt-2 text-xs text-muted">{n}</p>
      ))}
      <p className="mt-2 text-xs">
        <Link href="/track-record" className="underline">
          See every past case on the track record page
        </Link>
      </p>
    </section>
  );
}
