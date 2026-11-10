import type { Metadata } from "next";
import Link from "next/link";
import { getTrackRecord, type BacktestCase, type BacktestSummary } from "@/lib/db";
import { niceDate } from "@/lib/words";
import { Dots } from "../past-cases";
import { Ticker } from "../components";

export const metadata: Metadata = {
  title: "Track record · Tremor",
  description: "Every warning sign Tremor can check, and what happened next: hits and misses.",
};

const STARTED = "Nov 6, 2026";
const TITLES: Record<string, string> = {
  layoffs: "Layoffs",
  key_exec_departure: "A key executive left",
  trial_stopped: "A trial was stopped early",
};

function move(m: number | null) {
  if (m == null) return "—";
  return `${m > 0 ? "+" : ""}${Math.round(m)}%`;
}

function short(name: string | undefined, ticker: string) {
  return (name ?? ticker).split(",")[0].replace(/\b(Inc|Corp|Corporation|Ltd|plc|N\.V|S\.A)\.?$/i, "").trim();
}

function SignalHistory({ s, cases, names }: { s: BacktestSummary; cases: BacktestCase[]; names: Record<string, string> }) {
  const resolved = cases.filter((c) => c.outcome !== "unknown");
  const sorted = [...resolved].sort((a, b) => (a.outcome === b.outcome ? 0 : a.outcome === "bad" ? -1 : 1));
  const tooEarly = cases.length - resolved.length;
  const isStop = s.signal_type === "trial_stopped";
  const tableRows = isStop ? resolved.filter((c) => c.move_pct != null) : sorted;

  return (
    <li className="rounded-xl border border-line bg-surface p-4">
      <h3 className="text-lg font-bold">{TITLES[s.signal_type]}</h3>
      {(s.extra?.plain ?? []).map((t, i) => (
        <p key={i} className="mt-2 text-sm leading-relaxed">{t}</p>
      ))}
      {!isStop && (
        <div className="mt-3">
          <Dots
            bad={s.bad}
            fine={s.fine}
            cases={sorted.map((c) => ({
              outcome: c.outcome as "bad" | "fine",
              title: `${short(names[c.ticker], c.ticker)}, ${niceDate(c.signal_day)}: ${
                c.outcome === "bad" ? "a trial was stopped within a year" : "no trial stopped within a year"
              }`,
            }))}
          />
        </div>
      )}
      <p className="mt-3 text-sm">
        <span className="font-semibold">How sure are we: </span>
        {s.confidence === "high" ? "High" : s.confidence === "medium" ? "Medium" : "Low"}, based on {s.cases} past cases.
        {tooEarly > 0 && ` ${tooEarly} more are less than a year old, so it's too early to tell.`}
      </p>
      <details className="mt-3">
        <summary className="cursor-pointer text-sm font-semibold">
          {isStop ? `See the ${tableRows.length} cases with a clear announcement day` : `See all ${resolved.length} cases`}
        </summary>
        <div className="mt-2 overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="text-xs text-muted">
              <tr>
                <th className="py-1 pr-3 font-medium">Company</th>
                <th className="py-1 pr-3 font-medium">{isStop ? "Stopped" : "Sign"}</th>
                <th className="py-1 pr-3 font-medium">What happened next</th>
                <th className="py-1 text-right font-medium">Stock on the news</th>
              </tr>
            </thead>
            <tbody>
              {tableRows.map((c) => (
                <tr key={`${c.ticker}-${c.signal_day}`} className="border-t border-line align-top">
                  <td className="py-1.5 pr-3">
                    <Link href={`/companies/${c.ticker}`} className="hover:underline">
                      <Ticker symbol={c.ticker} />
                    </Link>
                  </td>
                  <td className="whitespace-nowrap py-1.5 pr-3">{niceDate(c.signal_day)}</td>
                  <td className="py-1.5 pr-3">
                    {isStop
                      ? `Announced ${niceDate(c.news_day)}`
                      : c.outcome === "bad"
                        ? `Trial stopped ${niceDate(c.detail)}`
                        : "No trial stopped within a year"}
                  </td>
                  <td className="py-1.5 text-right tabular-nums">{move(c.move_pct)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="mt-2 text-xs text-muted">
            Stock on the news = close the day before the company&apos;s announcement to the close the day after. A dash
            means we couldn&apos;t find a clear announcement day or price data.
          </p>
        </div>
      </details>
    </li>
  );
}

export default async function TrackRecordPage() {
  const { summaries, cases, alerts, alertCount, names } = await getTrackRecord();
  const order = ["layoffs", "key_exec_departure", "trial_stopped"];
  const shown = order.map((t) => summaries.find((s) => s.signal_type === t)).filter((s): s is BacktestSummary => !!s);
  const baseline = summaries.find((s) => s.baseline_bad_share)?.baseline_bad_share;

  return (
    <article>
      <h1 className="text-3xl font-black tracking-tight">Track record</h1>
      <p className="mt-2 text-muted">
        Every warning sign we can check, and what happened next. Hits and misses, so you can judge for yourself.
      </p>

      <section className="mt-8">
        <h2 className="text-xl font-bold">Tremor&apos;s own alerts</h2>
        <p className="mt-1 text-sm leading-relaxed">
          Tremor started watching on {STARTED}. We check what happened in the 12 months after each alert, so the first
          real results arrive in November 2027. Until then, every alert below is &ldquo;too early to tell.&rdquo;
        </p>
        <p className="mt-2 text-sm text-muted">{alertCount} serious alerts so far. The latest:</p>
        <ul className="mt-3 space-y-2">
          {alerts.map((a) => (
            <li key={a.id} className="rounded-xl border border-line bg-surface p-3 text-sm">
              <div className="flex flex-wrap items-center gap-2">
                {a.ticker && <Ticker symbol={a.ticker} />}
                <span className="text-xs text-muted">{niceDate(a.detected_at.slice(0, 10))}</span>
                <span className="rounded-full bg-line px-2 py-0.5 text-xs font-semibold">Too early to tell</span>
              </div>
              <p className="mt-1">
                {a.nct_id ? (
                  <Link href={`/trials/${a.nct_id}`} className="hover:underline">
                    {a.headline}
                  </Link>
                ) : (
                  a.headline
                )}
              </p>
            </li>
          ))}
        </ul>
      </section>

      <section className="mt-10">
        <h2 className="text-xl font-bold">If Tremor had existed: 2016 to today</h2>
        <p className="mt-1 text-sm leading-relaxed">
          We went back through public records for smaller cancer-drug companies (fewer than 15 late-stage cancer trials)
          and checked what happened in the year after each warning sign. &ldquo;Went badly&rdquo; means one of the
          company&apos;s trials was stopped early within a year.
          {baseline != null &&
            ` For comparison, starting from a random day, that happened about 1 in ${Math.round(1 / baseline)} times.`}
        </p>
        {shown.length === 0 ? (
          <p className="mt-3 rounded-xl border border-line bg-surface p-4 text-sm">The past cases are still being counted.</p>
        ) : (
          <ul className="mt-4 space-y-4">
            {shown.map((s) => (
              <SignalHistory key={s.signal_type} s={s} cases={cases.filter((c) => c.signal_type === s.signal_type)} names={names} />
            ))}
          </ul>
        )}
      </section>

      <section className="mt-10 rounded-xl border border-line bg-surface p-4 text-sm leading-relaxed">
        <h2 className="text-lg font-bold">What this doesn&apos;t show</h2>
        <ul className="mt-2 list-disc space-y-1.5 pl-5">
          <li>
            Only companies still listed today. Companies that went out of business aren&apos;t included, which may make
            the past look a little better than it was.
          </li>
          <li>
            Quiet edits to trial records (like changing the main goal) aren&apos;t here. There&apos;s no free archive of
            old versions, so Tremor builds that history itself, starting {STARTED}.
          </li>
          <li>
            Many trial stops are business decisions, not bad results. A stopped trial isn&apos;t always bad news for the
            stock.
          </li>
          <li>
            Most past cases had no clear announcement day we could find, so stock moves are only shown when we have at least
            10 of them.
          </li>
          <li>This is history, not a prediction, and it isn&apos;t advice to buy or sell anything.</li>
        </ul>
        {summaries[0]?.computed_at && (
          <p className="mt-3 text-xs text-muted">Last counted {niceDate(summaries[0].computed_at.slice(0, 10))}.</p>
        )}
      </section>
    </article>
  );
}
