import type { Metadata } from "next";
import Link from "next/link";
import { getUpcoming, type UpcomingEvent } from "@/lib/db";
import { companyName, niceDate } from "@/lib/words";
import { Ticker } from "../components";
import { ScoreBadge } from "../score";
import { Term } from "../term";

export const metadata: Metadata = {
  title: "Calendar",
  alternates: { canonical: "/upcoming" },
  description:
    "FDA decisions and cancer-trial results expected soon, from companies' own filings and trial records.",
};

const MONTH_NAMES = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
];

function when(e: UpcomingEvent) {
  const [y, m, d] = e.event_date.split("-").map(Number);
  return e.date_precision === "day"
    ? { big: String(d), small: MONTH_NAMES[m - 1].slice(0, 3) + " " + y }
    : { big: MONTH_NAMES[m - 1].slice(0, 3), small: `${y}, no exact day` };
}

function DateBox({ e }: { e: UpcomingEvent }) {
  const w = when(e);
  return (
    <div className="w-16 shrink-0 text-center">
      <div className="font-serif text-3xl font-medium leading-none">
        {w.big}
      </div>
      <div className="mt-1 text-xs leading-tight text-muted">
        {w.small}
      </div>
    </div>
  );
}

function shortName(e: UpcomingEvent) {
  return companyName(e.companies?.name, e.ticker);
}

function FdaDecision({ e }: { e: UpcomingEvent }) {
  return (
    <li className="flex gap-4 border-b border-line py-5">
      <DateBox e={e} />
      <div className="min-w-0">
        <Link
          href={`/companies/${e.ticker}`}
          className="group flex flex-wrap items-center gap-2"
        >
          <Ticker symbol={e.ticker} />
          <span className="text-sm text-ink-2 group-hover:text-foreground">
            {shortName(e)}
          </span>
        </Link>
        <p className="mt-1.5 font-medium">FDA decision expected</p>
        {e.quote && (
          <blockquote className="mt-2 border-l-2 border-line pl-3 font-serif text-[15px] italic leading-relaxed text-ink-2">
            &ldquo;{e.quote}&rdquo;
          </blockquote>
        )}
        {e.source_url && (
          <a
            href={e.source_url}
            target="_blank"
            rel="noreferrer"
            className="tap mt-1 inline-block text-xs underline"
          >
            From its {e.source_form} filed {niceDate(e.filed_at)} ↗
          </a>
        )}
      </div>
    </li>
  );
}

function FdaMeeting({ e }: { e: UpcomingEvent }) {
  return (
    <li className="flex gap-4 border-b border-line py-5">
      <DateBox e={e} />
      <div className="min-w-0">
        <Link
          href={`/companies/${e.ticker}`}
          className="group flex flex-wrap items-center gap-2"
        >
          <Ticker symbol={e.ticker} />
          <span className="text-sm text-ink-2 group-hover:text-foreground">
            {shortName(e)}
          </span>
        </Link>
        <p className="mt-1.5 font-medium">FDA advisory meeting</p>
        <p className="mt-3 text-sm text-muted">{e.title}</p>
        {e.source_url && (
          <a
            href={e.source_url}
            target="_blank"
            rel="noreferrer"
            className="tap mt-1 inline-block text-xs underline"
          >
            FDA notice ↗
          </a>
        )}
      </div>
    </li>
  );
}

function Conference({ e }: { e: UpcomingEvent }) {
  const [, m1, d1] = e.event_date.split("-").map(Number);
  const [, m2, d2] = (e.end_date ?? e.event_date).split("-").map(Number);
  const month = (m: number) => MONTH_NAMES[m - 1].slice(0, 3);
  const range = m1 === m2 ? `${month(m1)} ${d1}–${d2}` : `${month(m1)} ${d1} – ${month(m2)} ${d2}`;
  return (
    <li className="flex gap-4 border-b border-line py-5">
      <DateBox e={e} />
      <div className="min-w-0">
        <p className="font-medium">{e.title}</p>
        <p className="mt-0.5 text-sm text-ink-2">
          {range}
          {e.source_form ? ` · ${e.source_form}` : ""}
        </p>
        {e.quote && <p className="mt-1.5 text-sm text-muted">{e.quote}</p>}
        {e.source_url && (
          <a
            href={e.source_url}
            target="_blank"
            rel="noreferrer"
            className="tap mt-1 inline-block text-xs underline"
          >
            Conference website ↗
          </a>
        )}
      </div>
    </li>
  );
}

function ResultsRow({ e }: { e: UpcomingEvent }) {
  return (
    <li className="flex items-start gap-3 border-t border-line py-2.5 first:border-t-0">
      {e.date_precision === "day" ? (
        <span className="w-16 shrink-0 pt-0.5 text-sm font-semibold tabular-nums">
          {niceDate(e.event_date).split(",")[0]}
        </span>
      ) : (
        <span className="w-16 shrink-0 pt-0.5 text-xs leading-tight text-muted">
          No exact day
        </span>
      )}
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <Ticker symbol={e.ticker} />
          {e.trials && e.trials.score > 0 && (
            <ScoreBadge score={e.trials.score} label={e.trials.score_label} />
          )}
        </div>
        <Link
          href={`/trials/${e.nct_id}`}
          className="mt-1 line-clamp-2 text-sm hover:underline"
        >
          {e.title}
        </Link>
      </div>
    </li>
  );
}

export default async function UpcomingPage() {
  const events = await getUpcoming();
  const decisions = events.filter((e) => e.kind === "fda_decision");
  const meetings = events.filter((e) => e.kind === "fda_meeting");
  const results = events.filter((e) => e.kind === "results_due");
  const confs = events.filter((e) => e.kind === "conference");
  const byMonth = new Map<string, UpcomingEvent[]>();
  // Exact days first, then the trials that only gave a month
  const ordered = [...results].sort(
    (a, b) =>
      a.event_date.slice(0, 7).localeCompare(b.event_date.slice(0, 7)) ||
      Number(a.date_precision === "month") -
        Number(b.date_precision === "month") ||
      a.event_date.localeCompare(b.event_date),
  );
  for (const e of ordered) {
    const key = e.event_date.slice(0, 7);
    byMonth.set(key, [...(byMonth.get(key) ?? []), e]);
  }
  const updated = events[0]?.updated_at;

  return (
    <article className="rise">
      <h1 className="font-serif text-4xl font-medium tracking-tight sm:text-5xl">
        Calendar
      </h1>
      <p className="mt-4 max-w-2xl text-ink-2">
        When big news is expected. Stocks of small drug companies often move a
        lot on these days, in either direction.
      </p>

      <div className="mt-10 grid grid-cols-1 gap-x-12 gap-y-14 lg:grid-cols-12">
        <div className="min-w-0 space-y-14 lg:col-span-7">
          <section>
            <h2 className="border-t border-foreground pt-3 font-serif text-2xl font-medium tracking-tight">
              FDA decisions
            </h2>
            <p className="mt-3 text-sm leading-relaxed text-ink-2">
              The FDA decides whether a new drug can be sold in the US, and it
              sets itself a deadline (called a{" "}
              <Term id="pdufa">PDUFA date</Term>). Companies announce these in
              their SEC filings; below are their own words. The FDA can decide
              early or extend the deadline by 3 months, so check the
              company&apos;s latest news.
            </p>
            {decisions.length ? (
              <ul className="mt-2">
                {decisions.map((e) => (
                  <FdaDecision key={e.id} e={e} />
                ))}
              </ul>
            ) : (
              <p className="mt-3 border-y border-line py-5 text-sm text-muted">
                No FDA decision dates found right now.
              </p>
            )}
            <p className="mt-2 text-xs text-muted">
              Includes all drugs from the companies Tremor tracks, not just
              cancer drugs.
            </p>
          </section>

          {meetings.length > 0 && (
            <section>
              <h2 className="border-t border-foreground pt-3 font-serif text-2xl font-medium tracking-tight">
                <Term id="fda_advisory">FDA advisory meetings</Term>
              </h2>
              <p className="mt-3 text-sm text-ink-2">
                Outside experts meet in public to advise the FDA on a drug. The
                FDA usually, but not always, follows their vote.
              </p>
              <ul className="mt-2">
                {meetings.map((e) => (
                  <FdaMeeting key={e.id} e={e} />
                ))}
              </ul>
            </section>
          )}

          {confs.length > 0 && (
            <section>
              <h2 className="border-t border-foreground pt-3 font-serif text-2xl font-medium tracking-tight">
                Big cancer conferences
              </h2>
              <p className="mt-3 text-sm leading-relaxed text-ink-2">
                Companies often share trial results at these meetings, so
                stocks of small drug companies can move during them. Dates come
                from each conference&apos;s website.
              </p>
              <ul className="mt-2">
                {confs.map((e) => (
                  <Conference key={e.id} e={e} />
                ))}
              </ul>
            </section>
          )}
        </div>
        <section className="min-w-0 lg:col-span-5">
          <h2 className="border-t border-foreground pt-3 font-serif text-2xl font-medium tracking-tight">
            Trial results expected
          </h2>
          <p className="mt-3 text-sm leading-relaxed text-ink-2">
            When companies say a trial&apos;s main part will finish, from its
            official record. These are the companies&apos; own estimates.
            Results often come out weeks or months later (sometimes at a medical
            conference), and dates slip often.
          </p>
          {[...byMonth.entries()].map(([month, list], i) => {
            const [y, m] = month.split("-").map(Number);
            return (
              <details
                key={month}
                open={i < 2}
                className="group/m border-b border-line py-2"
              >
                <summary className="flex cursor-pointer list-none items-baseline justify-between py-2 font-medium">
                  <span>
                    <span className="mr-2 inline-block text-muted transition-transform group-open/m:rotate-90">
                      ›
                    </span>
                    {MONTH_NAMES[m - 1]} {y}
                  </span>
                  <span className="font-mono text-xs font-normal text-muted">
                    {list.length} trials
                  </span>
                </summary>
                <ul>
                  {list.map((e) => (
                    <ResultsRow key={e.id} e={e} />
                  ))}
                </ul>
              </details>
            );
          })}
          {!results.length && (
            <p className="mt-3 border-y border-line py-5 text-sm text-muted">
              Nothing expected in the next 6 months.
            </p>
          )}
        </section>
      </div>
      {updated && (
        <p className="mt-10 font-mono text-xs text-muted">
          Updated {niceDate(updated.slice(0, 10))}
        </p>
      )}
    </article>
  );
}
