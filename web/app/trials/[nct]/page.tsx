import { notFound } from "next/navigation";
import { Suspense } from "react";
import { getTrial } from "@/lib/db";
import { niceDate, phaseLabel } from "@/lib/words";
import { ChangeRow, Empty, StatusPill, Ticker } from "../../components";

async function TrialDetails({ params }: { params: PageProps<"/trials/[nct]">["params"] }) {
  const { nct } = await params;
  const { trial: t, changes } = await getTrial(nct);
  if (!t) notFound();

  const facts = [
    ["Stage", phaseLabel(t.phases)],
    ["Patients", t.enrollment != null ? `${t.enrollment.toLocaleString()} ${t.enrollment_type === "ACTUAL" ? "(final count)" : "(planned)"}` : "unknown"],
    ["Started", niceDate(t.start_date)],
    ["Main results expected", niceDate(t.primary_completion_date)],
    ["Fully finished", niceDate(t.completion_date)],
    ["Results posted", t.results_first_posted ? niceDate(t.results_first_posted) : "not yet"],
  ];

  return (
    <article>
      <div className="flex flex-wrap items-center gap-2">
        <Ticker symbol={t.ticker} />
        <span className="text-sm font-medium text-muted">{t.sponsor_name}</span>
        <StatusPill status={t.overall_status} />
      </div>
      <h1 className="mt-3 text-2xl font-black leading-tight tracking-tight sm:text-3xl">{t.title}</h1>
      <p className="mt-2 text-sm text-muted">{t.conditions.join(" · ")}</p>

      <dl className="mt-6 grid grid-cols-2 gap-2 sm:grid-cols-3">
        {facts.map(([label, value]) => (
          <div key={label} className="rounded-xl border border-line bg-surface p-3">
            <dt className="text-xs text-muted">{label}</dt>
            <dd className="mt-1 font-semibold">{value}</dd>
          </div>
        ))}
      </dl>

      <section className="mt-8">
        <h2 className="text-lg font-bold">What counts as success</h2>
        <p className="text-sm text-muted">The trial&apos;s main goal(s), called the &ldquo;primary outcome.&rdquo;</p>
        <ul className="mt-3 space-y-2">
          {t.primary_outcomes.map((o, i) => (
            <li key={i} className="rounded-xl border border-line bg-surface p-3">
              <p className="font-semibold">{o.measure}</p>
              {o.timeFrame && <p className="mt-1 text-sm text-muted">Measured over: {o.timeFrame}</p>}
            </li>
          ))}
        </ul>
      </section>

      <section className="mt-8">
        <h2 className="text-lg font-bold">Changes Tremor has spotted</h2>
        <div className="mt-3">
          {changes.length ? (
            <ul className="space-y-2">
              {changes.map((c) => (
                <ChangeRow key={c.id} c={c} showTrial={false} />
              ))}
            </ul>
          ) : (
            <Empty>No changes since Tremor started watching this trial.</Empty>
          )}
        </div>
      </section>

      <a
        href={`https://clinicaltrials.gov/study/${t.nct_id}`}
        target="_blank"
        rel="noreferrer"
        className="mt-8 inline-block text-sm font-semibold underline"
      >
        See the official record on ClinicalTrials.gov ({t.nct_id}) ↗
      </a>
    </article>
  );
}

export default function TrialPage(props: PageProps<"/trials/[nct]">) {
  return (
    <Suspense fallback={<div className="h-96 animate-pulse rounded-xl bg-line" />}>
      <TrialDetails params={props.params} />
    </Suspense>
  );
}
