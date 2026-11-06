import Link from "next/link";
import { Suspense } from "react";
import { getRecentChanges, getStats } from "@/lib/db";
import { ChangeRow, Empty } from "./components";
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

async function LatestChanges() {
  const changes = await getRecentChanges(20);
  if (!changes.length)
    return (
      <Empty>
        No important changes spotted yet. Tremor checks every trial every 4 hours. Companies edit trial
        records every few weeks or months, so changes will start showing up here soon.
      </Empty>
    );
  return (
    <ul className="space-y-2">
      {changes.map((c) => (
        <ChangeRow key={c.id} c={c} />
      ))}
    </ul>
  );
}

export default function Home() {
  return (
    <div className="space-y-10">
      <section>
        <h1 className="text-4xl font-black tracking-tight sm:text-5xl">
          Early warnings for <span className="text-tremor">cancer drug trials</span>.
        </h1>
        <p className="mt-4 text-lg text-muted">
          When a drug trial is in trouble, companies rarely say so right away. But clues show up first, like
          quiet edits to the trial&apos;s official record. Tremor watches for them.
        </p>
      </section>

      <Suspense fallback={<div className="h-20 animate-pulse rounded-xl bg-line" />}>
        <Stats />
      </Suspense>

      <section>
        <div className="mb-3 flex items-baseline justify-between">
          <h2 className="text-xl font-bold">Latest changes</h2>
          <Link href="/trials" className="text-sm font-semibold text-muted hover:text-foreground">
            Browse all trials →
          </Link>
        </div>
        <Suspense fallback={<div className="h-40 animate-pulse rounded-xl bg-line" />}>
          <LatestChanges />
        </Suspense>
      </section>
    </div>
  );
}
