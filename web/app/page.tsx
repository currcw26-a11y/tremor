import Link from "next/link";
import { Suspense } from "react";
import { getRecentChanges, getStats, getTopWorries, getUpcoming } from "@/lib/db";
import { companyName } from "@/lib/words";
import { BANDS } from "@/lib/score";
import { ChangeRow, Empty, Ticker } from "./components";
import { Shape } from "./score";
import { SectionHead } from "./ui";
import { TimeAgo } from "./time-ago";

export const metadata = { alternates: { canonical: "/" } };

async function Facts() {
  const s = await getStats();
  return (
    <p className="mt-10 font-mono text-xs uppercase tracking-[0.12em] text-muted">
      {s.trials.toLocaleString()} trials · {s.companies.toLocaleString()} companies · checked <TimeAgo iso={s.lastRun} />
    </p>
  );
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

async function NextUp() {
  const events = await getUpcoming();
  const decisions = events.filter((e) => e.kind === "fda_decision").slice(0, 4);
  const list = decisions.length ? decisions : events.filter((e) => e.kind === "results_due").slice(0, 4);
  return (
    <div>
      <SectionHead title="Next on the calendar" href="/upcoming" linkText="See all" />
      {list.length ? (
        <ul className="mt-2">
          {list.map((e) => {
            const [y, m, d] = e.event_date.split("-");
            return (
              <li key={e.id} className="border-b border-line last:border-b-0">
                <Link
                  href={e.nct_id ? `/trials/${e.nct_id}` : `/companies/${e.ticker}`}
                  className="group -mx-3 flex items-start gap-4 rounded-md px-3 py-3.5 transition-colors hover:bg-surface"
                >
                  <span className="w-14 shrink-0 text-center">
                    <span className="block font-serif text-3xl font-medium leading-none">
                      {e.date_precision === "day" ? Number(d) : "—"}
                    </span>
                    <span className="mt-1 block font-mono text-[11px] uppercase tracking-wider text-muted">
                      {MONTHS[Number(m) - 1]} {y.slice(2)}
                    </span>
                  </span>
                  <span className="min-w-0 pt-0.5">
                    <span className="flex items-center gap-2">
                      <Ticker symbol={e.ticker} />
                      <span className="truncate text-sm text-ink-2">{companyName(e.companies?.name, e.ticker)}</span>
                    </span>
                    <span className="mt-1 block font-medium">
                      {e.kind === "fda_decision" ? "FDA decision expected" : "Main trial results expected"}{" "}
                      <span className="nudge text-muted">→</span>
                    </span>
                  </span>
                </Link>
              </li>
            );
          })}
        </ul>
      ) : (
        <Empty>No dates announced right now.</Empty>
      )}
    </div>
  );
}

async function TopWorries() {
  const trials = await getTopWorries(6);
  if (!trials.length) return <Empty>No warning signs on any tracked trial right now.</Empty>;
  return (
    <ol className="mt-2">
      {trials.map((t) => {
        const band = BANDS[t.score_label];
        const [first, ...rest] = t.score_breakdown ?? [];
        return (
          <li key={t.nct_id} className="border-b border-line last:border-b-0">
            <Link
              href={`/trials/${t.nct_id}`}
              className="group -mx-3 grid grid-cols-[4.5rem_minmax(0,1fr)] gap-4 rounded-md px-3 py-4 transition-colors hover:bg-surface"
            >
              <span>
                <span className="block font-serif text-4xl font-medium leading-none tabular-nums">{t.score}</span>
                <span className={`mt-1.5 flex items-center gap-1 text-xs font-medium ${band.color}`}>
                  <span className={band.mark}>
                    <Shape label={t.score_label} size={8} />
                  </span>
                  {band.name}
                </span>
              </span>
              <span className="min-w-0">
                <span className="flex items-center gap-2">
                  <Ticker symbol={t.ticker} />
                  <span className="truncate text-sm text-ink-2">{t.sponsor_name}</span>
                </span>
                <span className="mt-1 line-clamp-2 font-medium leading-snug">{t.title}</span>
                {first && (
                  <span className="mt-1 block text-sm text-ink-2">
                    {first.label}
                    {rest.length > 0 && (
                      // a tiny hover popup listing the other reasons
                      <span className="group/more relative ml-1 text-muted underline decoration-dotted underline-offset-2">
                        +{rest.length} more
                        <span className="pointer-events-none invisible absolute bottom-full left-0 z-20 mb-2 hidden w-64 md:block rounded-md bg-navy p-3 text-xs leading-relaxed text-white no-underline opacity-0 shadow-lg transition-all duration-150 group-hover/more:visible group-hover/more:opacity-100">
                          {rest.map((r, i) => (
                            <span key={i} className="block">
                              {r.label}
                            </span>
                          ))}
                        </span>
                      </span>
                    )}
                  </span>
                )}
              </span>
            </Link>
          </li>
        );
      })}
    </ol>
  );
}

async function LatestChanges({ searchParams }: { searchParams: PageProps<"/">["searchParams"] }) {
  const showMinor = (await searchParams).minor === "1";
  const changes = await getRecentChanges(12, showMinor);
  return (
    <>
      <SectionHead title="Latest changes" />
      {changes.length ? (
        <ul className="mt-1">
          {changes.map((c) => (
            <ChangeRow key={c.id} c={c} />
          ))}
        </ul>
      ) : (
        <Empty>No important changes spotted yet. Tremor checks every trial every 4 hours.</Empty>
      )}
      <p className="mt-3 text-sm text-muted">
        {showMinor ? "Showing routine edits too. " : "Routine edits, like a trial starting to sign up patients, are hidden. "}
        <Link
          href={showMinor ? "/" : "/?minor=1"}
          scroll={false}
          className="text-ink-2 underline underline-offset-2 hover:text-foreground"
        >
          {showMinor ? "Hide them" : "Show them"}
        </Link>
      </p>
    </>
  );
}

export default function Home(props: PageProps<"/">) {
  return (
    <div className="space-y-16 lg:space-y-20">
      <section className="grid grid-cols-1 gap-12 lg:grid-cols-12">
        <div className="rise lg:col-span-7 lg:pt-4">
          <h1 className="max-w-2xl font-serif text-[2.75rem] font-medium leading-[1.04] tracking-tight sm:text-6xl">
            Early warnings for cancer drug trials
          </h1>
          <p className="mt-6 max-w-xl text-[17px] leading-relaxed text-ink-2 sm:text-lg">
            When a drug trial is in trouble, the company rarely says so right away. The clues tend to show up first, in
            public records. Tremor reads those records every four hours, gives each trial a worry score, and explains every
            change in plain English.
          </p>
          <div className="mt-8 flex flex-wrap gap-x-8 gap-y-3 text-[15px] font-medium">
            <Link href="/learn">
              <span className="link-grow">How biotech stocks move</span> <span className="nudge">→</span>
            </Link>
            <Link href="/how-it-works">
              <span className="link-grow">How the score works</span> <span className="nudge">→</span>
            </Link>
          </div>
          <Suspense fallback={<p className="mt-10 h-4" />}>
            <Facts />
          </Suspense>
        </div>
        <aside className="rise rise-2 lg:col-span-5">
          <Suspense fallback={<div className="h-72" />}>
            <NextUp />
          </Suspense>
        </aside>
      </section>

      <section className="grid grid-cols-1 gap-16 lg:grid-cols-12 lg:gap-12">
        <div className="lg:col-span-7">
          <SectionHead title="Biggest worries right now" href="/trials" linkText="All trials" />
          <Suspense fallback={<div className="h-96" />}>
            <TopWorries />
          </Suspense>
          <p className="mt-3 text-sm text-muted">
            The score counts warning signs in public records. A high score is not a prediction.
          </p>
        </div>
        <div className="lg:col-span-5">
          <Suspense fallback={<div className="h-96" />}>
            <LatestChanges searchParams={props.searchParams} />
          </Suspense>
        </div>
      </section>
    </div>
  );
}
