import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Suspense } from "react";
import { getTrial } from "@/lib/db";
import { companyName, niceDate, phaseLabel } from "@/lib/words";
import { BANDS } from "@/lib/score";
import { ChangeRow, Empty, StatusPill, Ticker } from "../../components";
import { Reasons, ScoreHero } from "../../score";
import { ScoreChart } from "../../score-chart";
import { StarButton } from "../../star-button";
import { AskBox } from "../../ask-box";
import { OutlookSection } from "../../past-cases";
import { Facts, SectionHead } from "../../ui";
import { Term } from "../../term";

export async function generateMetadata({ params }: PageProps<"/trials/[nct]">): Promise<Metadata> {
  const { nct } = await params;
  const { trial: t, company } = await getTrial(nct);
  if (!t) return { title: "Trial not found", robots: { index: false } };
  const who = companyName(company?.name ?? t.sponsor_name, t.ticker);
  const title = `${t.title.length > 70 ? t.title.slice(0, 70).replace(/\s+\S*$/, "") + "…" : t.title} (${t.ticker})`;
  const description =
    `${who}'s ${phaseLabel(t.phases)} cancer trial${t.conditions.length ? ` in ${t.conditions.slice(0, 2).join(", ")}` : ""}. ` +
    `Worry score ${t.score} out of 100 (${BANDS[t.score_label].name}). Every change to its official record, explained in plain English.`;
  return {
    title,
    description: description.slice(0, 300),
    alternates: { canonical: `/trials/${t.nct_id}` },
    // A page-level openGraph replaces the inherited one, so the share card is named again here
    openGraph: { title, description: description.slice(0, 300), url: `/trials/${t.nct_id}`, images: "/opengraph-image" },
    robots: t.tracked === false ? { index: false } : undefined,
  };
}

async function TrialDetails({ params }: { params: PageProps<"/trials/[nct]">["params"] }) {
  const { nct } = await params;
  const { trial: t, changes, history, company, profile } = await getTrial(nct);
  if (!t) notFound();

  const facts: [React.ReactNode, React.ReactNode][] = [
    ["Stage", <PhaseTerm key="stage" phases={t.phases} />],
    [<Term key="p" id="enrollment">Patients</Term>, t.enrollment != null ? `${t.enrollment.toLocaleString()} ${t.enrollment_type === "ACTUAL" ? "(final count)" : "(planned)"}` : "unknown"],
    ["Started", niceDate(t.start_date)],
    ["Main results due", niceDate(t.primary_completion_date)],
    ["Finish date", niceDate(t.completion_date)],
    ["Results posted", t.results_first_posted ? niceDate(t.results_first_posted) : "not yet"],
    [
      <Term key="dt" id="drug_target">Drug targets</Term>,
      profile?.targets.length ? (
        <span
          title={profile.targets
            .map((x) => `${x}: ${profile.target_source?.[x] === "chembl" ? "from the ChEMBL drug database" : "named in the trial record"}`)
            .join("\n")}
        >
          {profile.targets.join(" · ")}
        </span>
      ) : (
        <span className="font-normal text-muted">not known</span>
      ),
    ],
  ];

  const band = BANDS[t.score_label];
  return (
    <article>
      <header className="rise border-b border-line pb-8">
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
          <Link href={`/companies/${t.ticker}`} className="group flex items-center gap-2">
            <Ticker symbol={t.ticker} />
            <span className="text-sm text-ink-2 group-hover:text-foreground">{companyName(company?.name ?? t.sponsor_name, t.ticker)}</span>
          </Link>
          <StatusPill status={t.overall_status} />
        </div>
        <h1 className="mt-4 max-w-4xl font-serif text-[1.9rem] font-medium leading-[1.12] tracking-tight sm:text-[2.6rem]">
          {t.title}
        </h1>
        {t.conditions.length > 0 && <p className="mt-3 max-w-3xl text-ink-2">{t.conditions.join(" · ")}</p>}
      </header>

      <div className="mt-10 grid grid-cols-1 gap-x-12 gap-y-14 lg:grid-cols-12">
        <section className="rise rise-1 min-w-0 lg:col-span-8">
          <ScoreHero score={t.score} label={t.score_label} />
          <p className="mt-5 max-w-xl text-ink-2">
            {band.meaning} The score counts warning signs in public records; it is not a prediction.{" "}
            <Link href="/how-it-works" className="whitespace-nowrap text-foreground underline underline-offset-2">
              How it works
            </Link>
          </p>
        </section>

        <aside className="rise rise-2 min-w-0 lg:col-span-4 lg:row-span-6">
          <div className="space-y-8 lg:sticky lg:top-24">
            <StarButton kind="trial" id={t.nct_id} />
            <div>
              <h2 className="mb-2 text-sm font-semibold">The trial</h2>
              <Facts rows={facts} />
            </div>
            <div className="space-y-2 text-sm">
              <a href={`https://clinicaltrials.gov/study/${t.nct_id}`} target="_blank" rel="noreferrer" className="block text-ink-2 hover:text-foreground">
                <span className="link-grow">Official record on ClinicalTrials.gov</span> <span className="nudge">↗</span>
              </a>
              <Link href={`/companies/${t.ticker}`} className="block text-ink-2 hover:text-foreground">
                <span className="link-grow">Everything about {companyName(company?.name ?? t.sponsor_name, t.ticker)}</span>
              </Link>
              <p className="font-mono text-xs text-muted">{t.nct_id}</p>
            </div>
          </div>
        </aside>

        <section className="min-w-0 lg:col-span-8">
          <SectionHead title="Why this score" />
          <div className="mt-2">
            <Reasons reasons={t.score_breakdown ?? []} score={t.score} />
          </div>
        </section>

        <section className="min-w-0 lg:col-span-8">
          <SectionHead title="Score over time" />
          <div className="mt-4">
            <ScoreChart points={history} current={t.score} currentLabel={t.score_label} />
          </div>
        </section>

        <div className="min-w-0 lg:col-span-8">
          <OutlookSection outlook={t.outlook} company={company} />
        </div>

        <section className="min-w-0 lg:col-span-8">
          <SectionHead title="Changes Tremor has spotted" />
          {changes.length ? (
            <ul className="mt-1">
              {changes.map((c) => (
                <ChangeRow key={c.id} c={c} showTrial={false} />
              ))}
            </ul>
          ) : (
            <div className="mt-3">
              <Empty>No changes since Tremor started watching this trial.</Empty>
            </div>
          )}
        </section>

        <section className="min-w-0 lg:col-span-8">
          <SectionHead title="What counts as success" />
          <p className="mt-3 text-sm text-ink-2">
            The trial&apos;s <Term id="primary_outcome">main goal(s)</Term>, decided before it started.
          </p>
          <ol className="mt-3 divide-y divide-line border-y border-line">
            {t.primary_outcomes.map((o, i) => (
              <li key={i} className="grid grid-cols-[1.5rem_minmax(0,1fr)] gap-2 py-3">
                <span className="font-mono text-sm text-muted">{i + 1}</span>
                <span>
                  <span className="block font-medium leading-snug">{o.measure}</span>
                  {o.timeFrame && <span className="mt-1 block text-sm text-muted">Time frame: {o.timeFrame}</span>}
                </span>
              </li>
            ))}
          </ol>
        </section>

        <div className="min-w-0 space-y-10 lg:col-span-8">
          <AskBox nctId={t.nct_id} ticker={t.ticker} kind="trial" />
    <details className="group/tech border-t border-line pt-4">
            <summary className="cursor-pointer list-none text-sm font-medium text-ink-2 hover:text-foreground">
              <span className="mr-1 inline-block transition-transform group-open/tech:rotate-90">›</span> Show details (technical version)
            </summary>
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
        </div>
      </div>
    </article>
  );
}

export default function TrialPage(props: PageProps<"/trials/[nct]">) {
  return (
    <Suspense fallback={<div className="h-96 animate-pulse rounded-lg bg-line" />}>
      <TrialDetails params={props.params} />
    </Suspense>
  );
}

/** "Phase 3" with a tap-to-learn popup (the highest phase listed). */
function PhaseTerm({ phases }: { phases: string[] }) {
  const label = phaseLabel(phases);
  const top = Math.max(...(phases ?? []).map((x) => Number(x.replace(/\D/g, "")) || 0), 0);
  if (top === 3) return <Term id="phase3">{label}</Term>;
  if (top === 2) return <Term id="phase2">{label}</Term>;
  return <>{label}</>;
}
