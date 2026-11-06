import Link from "next/link";
import { notFound } from "next/navigation";
import { Suspense } from "react";
import { getTrial } from "@/lib/db";
import { niceDate, phaseLabel } from "@/lib/words";
import { BANDS } from "@/lib/score";
import { ChangeRow, Empty, StatusPill, Ticker } from "../../components";
import { Reasons, ScoreBadge } from "../../score";
import { ScoreChart } from "../../score-chart";

async function TrialDetails({ params }: { params: PageProps<"/trials/[nct]">["params"] }) {
  const { nct } = await params;
  const { trial: t, changes, history } = await getTrial(nct);
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
        <Link href={`/companies/${t.ticker}`} className="flex items-center gap-2 hover:underline">
          <Ticker symbol={t.ticker} />
          <span className="text-sm font-medium text-muted">{t.sponsor_name}</span>
        </Link>
        <StatusPill status={t.overall_status} />
      </div>
      <h1 className="mt-3 text-2xl font-black leading-tight tracking-tight sm:text-3xl">{t.title}</h1>
      <p className="mt-2 text-sm text-muted">{t.conditions.join(" · ")}</p>

      <section className="mt-6">
        <ScoreBadge score={t.score} label={t.score_label} size="lg" />
        <p className="mt-2 text-sm text-muted">{BANDS[t.score_label].meaning} The score counts warning signs; it is not a prediction.</p>
        <h2 className="mt-6 text-lg font-bold">Why this score</h2>
        <div className="mt-3">
          <Reasons reasons={t.score_breakdown ?? []} score={t.score} />
        </div>
        <h2 className="mt-6 text-lg font-bold">Score over time</h2>
        <div className="mt-3">
          <ScoreChart points={history} current={t.score} currentLabel={t.score_label} />
        </div>
      </section>

      <dl className="mt-8 grid grid-cols-2 gap-2 sm:grid-cols-3">
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

      <details className="mt-8 rounded-xl border border-line bg-surface p-4">
        <summary className="cursor-pointer font-semibold">Show details (technical version)</summary>
        <div className="mt-3 space-y-4 text-sm">
          <div>
            <h3 className="font-semibold">Score inputs</h3>
            <ul className="mt-1 space-y-1 font-mono text-xs">
              {(t.score_breakdown ?? []).map((r, i) => (
                <li key={i}>
                  {r.type}: base {r.base_points}, now {r.points}, since {r.occurred}
                  {r.fades ? ", fades (half-life)" : ", no fading"}
                  {typeof r.source?.url === "string" && (
                    <>
                      {" · "}
                      <a href={r.source.url} className="underline" target="_blank" rel="noreferrer">source filing</a>
                    </>
                  )}
                </li>
              ))}
              {!t.score_breakdown?.length && <li>none</li>}
            </ul>
          </div>
          <div>
            <h3 className="font-semibold">Raw record changes</h3>
            <ul className="mt-1 space-y-2 font-mono text-xs">
              {changes.map((c) => (
                <li key={c.id} className="break-words">
                  {c.detected_at.slice(0, 16).replace("T", " ")} UTC · {c.change_type} · {c.field}
                  <br />
                  old: {JSON.stringify(c.old_value)}
                  <br />
                  new: {JSON.stringify(c.new_value)}
                  {c.details && (
                    <>
                      <br />
                      details: {JSON.stringify(c.details)}
                    </>
                  )}
                </li>
              ))}
              {!changes.length && <li>none yet</li>}
            </ul>
          </div>
          <p className="text-xs text-muted">
            Trial ID {t.nct_id} · record last updated {t.last_update_posted} · checked{" "}
            {t.last_checked_at.slice(0, 16).replace("T", " ")} UTC
          </p>
        </div>
      </details>

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
