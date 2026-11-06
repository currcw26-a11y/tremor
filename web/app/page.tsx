import Link from "next/link";
import { Suspense } from "react";
import { getRecentChanges, getStats, getTopWorries } from "@/lib/db";
import { ChangeRow, Empty, Ticker } from "./components";
import { ScoreBadge } from "./score";
import { TimeAgo } from "./time-ago";

async function Stats() {
  const s = await getStats();
  const items = [
    { value: s.trials.toLocaleString(), label: "cancer trials watched" },
    { value: s.companies.toLocaleString(), label: "public companies" },
    { value: <TimeAgo iso={s.lastRun} />, label: "last checked" },
  ];
  return (
    <dl className="grid grid-cols-3 gap-2">
      {items.map((i) => (
        <div key={i.label} className="rounded-xl border border-line bg-surface p-3">
          <dt className="text-xs text-muted">{i.label}</dt>
          <dd className="mt-1 text-base font-bold leading-tight sm:text-2xl">{i.value}</dd>
        </div>
      ))}
    </dl>
  );
}

async function TopWorries() {
  const trials = await getTopWorries(8);
  if (!trials.length) return <Empty>No warning signs on any tracked trial right now.</Empty>;
  return (
    <ol className="space-y-2">
      {trials.map((t) => (
        <li key={t.nct_id}>
          <Link
            href={`/trials/${t.nct_id}`}
            className="flex items-center gap-3 rounded-xl border border-line bg-surface p-3 transition hover:border-foreground/30"
          >
            <ScoreBadge score={t.score} label={t.score_label} />
            <div className="min-w-0 flex-1">
              <p className="flex items-center gap-2">
                <Ticker symbol={t.ticker} />
                <span className="truncate text-sm font-semibold">{t.title}</span>
              </p>
              {t.score_breakdown?.[0] && (
                <p className="mt-1 truncate text-sm text-muted">
                  {t.score_breakdown[0].label}
                  {t.score_breakdown.length > 1 && ` + ${t.score_breakdown.length - 1} more`}
                </p>
              )}
            </div>
          </Link>
        </li>
      ))}
    </ol>
  );
}

async function LatestChanges({ searchParams }: { searchParams: PageProps<"/">["searchParams"] }) {
  const showMinor = (await searchParams).minor === "1";
  const changes = await getRecentChanges(30, showMinor);
  return (
    <>
      <div className="mb-3 flex items-baseline justify-between gap-2">
        <h2 className="text-xl font-bold">Latest changes</h2>
        <Link
          href={showMinor ? "/" : "/?minor=1"}
          scroll={false}
          className="text-sm font-semibold text-muted hover:text-foreground"
        >
          {showMinor ? "Hide minor changes" : "Show minor changes too"}
        </Link>
      </div>
      {changes.length ? (
        <ul className="space-y-2">
          {changes.map((c) => (
            <ChangeRow key={c.id} c={c} />
          ))}
        </ul>
      ) : (
        <Empty>
          No important changes spotted yet. Tremor checks every trial every 4 hours. Companies edit trial records
          every few weeks or months, so changes will show up here soon.
        </Empty>
      )}
      {!showMinor && (
        <p className="mt-3 text-sm text-muted">
          Hiding routine edits like &ldquo;started signing up patients&rdquo; and small date tweaks.
        </p>
      )}
    </>
  );
}

export default function Home(props: PageProps<"/">) {
  return (
    <div className="space-y-10">
      <section>
        <h1 className="text-4xl font-black tracking-tight sm:text-5xl">
          Early warnings for <span className="text-tremor">cancer drug trials</span>.
        </h1>
        <p className="mt-4 text-lg text-muted">
          When a drug trial is in trouble, companies rarely say so right away. But clues show up first. Tremor
          watches for them and gives every trial a worry score from 0 to 100.
        </p>
      </section>

      <Suspense fallback={<div className="h-20 animate-pulse rounded-xl bg-line" />}>
        <Stats />
      </Suspense>

      <section>
        <h2 className="mb-1 text-xl font-bold">Biggest worries right now</h2>
        <p className="mb-3 text-sm text-muted">Trials with the most warning signs. A high score is not a prediction.</p>
        <Suspense fallback={<div className="h-40 animate-pulse rounded-xl bg-line" />}>
          <TopWorries />
        </Suspense>
      </section>

      <section>
        <Suspense fallback={<div className="h-40 animate-pulse rounded-xl bg-line" />}>
          <LatestChanges searchParams={props.searchParams} />
        </Suspense>
      </section>
    </div>
  );
}
