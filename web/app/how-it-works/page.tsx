import type { Metadata } from "next";
import Link from "next/link";
import rules from "@/lib/score-rules.json";
import { getTrackRecord } from "@/lib/db";
import { BANDS } from "@/lib/score";
import { Shape } from "../score";

export const metadata: Metadata = {
  title: "How the score works",
  alternates: { canonical: "/how-it-works" },
  description:
    "Every rule behind Tremor's 0-100 worry score, in plain English, with what the past says about each one.",
};

const W = rules.weights as Record<string, number>;
const D = rules.detection;

type Rule = {
  key: string;
  title: string;
  what: string;
  why: string;
  status?: string;
  tested?: string;
};

const TRIAL_RULES: Rule[] = [
  {
    key: "primary_outcome_changed",
    title: "The main goal changed",
    what: 'The company changed or removed what the trial is trying to prove (its "main goal" or primary outcome).',
    why: "Changing what counts as success can mean the company worries the original goal won't be met. It can also be routine: regulators sometimes ask for it.",
  },
  {
    key: "enrollment_cut",
    title: "Fewer patients",
    what: `The planned number of patients dropped by ${D.enrollment_cut_percent}% or more.`,
    why: `Fewer patients can mean sign-up is going badly or the company is saving money. When the number just switches from a plan to the final count as sign-up ends, it gets only ${rules.enrollment_final_count_factor === 0.5 ? "half" : rules.enrollment_final_count_factor} the points, because that's common.`,
  },
  {
    key: "date_delayed",
    title: "Dates pushed back",
    what: `The date for main results, or for finishing, moved ${D.date_delay_months} or more months later.`,
    why: "Delays can mean the trial is struggling to sign up patients. Many are ordinary scheduling changes.",
  },
  {
    key: "results_overdue",
    title: "Results overdue",
    what: `The main part finished ${D.results_overdue_months}+ months ago and no results are posted.`,
    why: "Companies are usually quick to share good news. A long silence is worth noticing, though some just post late.",
  },
  {
    key: "fda_advisory_meeting",
    title: "FDA advisory meeting",
    what: "The FDA scheduled a public meeting of outside experts about this trial's drug.",
    why: "These meetings often happen when the FDA has questions. The stock usually moves on the vote, in either direction.",
  },
  {
    key: "rival_trial_failed",
    title: "A rival drug failed",
    what: "In the last year, another company's drug aimed at the same target, in the same kind of cancer, had its trial stopped because it wasn't working well enough or wasn't safe.",
    why: "If a similar drug didn't work, investors may worry this one won't either. Stops for business reasons don't count.",
    status: "Only counts when both drugs' targets are known, from the ChEMBL drug database or named in the trial record. Only the new drug that failed counts, not an approved drug given alongside it. Not tested on past cases yet.",
  },
];

const COMPANY_RULES: Rule[] = [
  {
    key: "key_exec_departure",
    title: "A key executive left",
    what: "Someone like the chief medical officer or head of research is leaving (from the company's SEC filings).",
    why: "People close to the data sometimes leave before bad news. Many leave for ordinary reasons.",
  },
  {
    key: "repeat_exec_departure",
    title: "A second key executive left within 6 months",
    what: `Extra points when another key executive leaves within ${Math.round(rules.repeat_exec_window_days / 30)} months of the last one.`,
    why: "This was the strongest pattern in our look back at past cases.",
  },
  {
    key: "layoffs",
    title: "Layoffs",
    what: "The company announced layoffs or restructuring, or filed a state layoff notice.",
    why: "Cutting staff can mean money is tight or a program is being dropped.",
  },
  {
    key: "insider_selling_cluster",
    title: "Several insiders sold shares",
    what: `${D.insider_cluster_min_people} or more company insiders sold shares within ${D.insider_cluster_days} days, not as part of a sale planned in advance (a \"10b5-1 plan\").`,
    why: "Insiders know the company best. But most of their sales are planned months ahead, so those don't count.",
    status: "Not tested on past cases yet.",
  },
  {
    key: "job_postings_drop",
    title: "Fewer clinical job postings",
    what: "Job postings for clinical roles dropped by half or more compared with a few weeks earlier.",
    why: "A hiring freeze on trial staff can come before a trial is cut back.",
    status:
      "Needs about 2 weeks of daily job counts before it can fire; only for companies whose job board we could confirm.",
  },
];

function RuleCard({ r, tested }: { r: Rule; tested?: string }) {
  return (
    <li className="border-t border-line py-5">
      <div className="flex items-start justify-between gap-3">
        <h3 className="font-bold">{r.title}</h3>
        <span className="shrink-0 font-serif text-3xl font-medium leading-none tabular-nums">
          +{W[r.key]}
        </span>
      </div>
      <p className="mt-1.5 text-sm">{r.what}</p>
      <p className="mt-1.5 text-sm text-muted">{r.why}</p>
      {(tested || r.status) && (
        <p className="mt-3 border-l-2 border-line pl-3 text-xs leading-relaxed text-ink-2">
          <span className="font-semibold">
            {tested ? "What the past says: " : "Note: "}
          </span>
          {tested ?? r.status}
        </p>
      )}
    </li>
  );
}

const ONE_IN = (share: number) => Math.floor(1 / share + 0.5);

export default async function HowItWorks() {
  const { summaries } = await getTrackRecord();
  const by = Object.fromEntries(summaries.map((s) => [s.signal_type, s]));
  const base = summaries.find((s) => s.baseline_bad_share)?.baseline_bad_share;
  const tested = (key: string) => {
    const s = by[key];
    if (!s || !s.cases) return undefined;
    return (
      `In ${s.bad} out of ${s.cases} past cases at smaller companies, one of the company's trials was stopped within a year` +
      (base ? ` (from a random day: about 1 in ${ONE_IN(base)}).` : ".")
    );
  };
  const notYet = `Not tested yet. There's no free archive of old trial records, so Tremor started saving its own copies on Nov 6, 2026 and will check these as cases build up.`;
  const L = rules.labels;

  return (
    <article className="rise">
      <h1 className="font-serif text-4xl font-medium tracking-tight sm:text-5xl">
        How the score works
      </h1>
      <p className="mt-4 max-w-2xl text-ink-2">
        Every trial gets a worry score from 0 to 100. It adds up warning signs
        found in public records. It is not a prediction, and it never tells
        anyone to buy or sell.
      </p>

      <section className="mt-10 grid grid-cols-1 gap-x-10 gap-y-6 sm:grid-cols-3">
        {(
          [
            [
              "calm",
              `${L.calm} to ${L.shaky - 1}`,
              "No strong warning signs right now.",
            ],
            [
              "shaky",
              `${L.shaky} to ${L.tremor - 1}`,
              "A few warning signs. Worth a look.",
            ],
            [
              "tremor",
              `${L.tremor} to 100`,
              "Several strong warning signs, or the trial was stopped.",
            ],
          ] as const
        ).map(([label, range, text]) => (
          <div key={label} className="border-t-2 border-foreground pt-3">
            <p
              className={`flex items-center gap-1.5 font-bold ${BANDS[label].color}`}
            >
              <Shape label={label} size={12} />
              {BANDS[label].name}
              <span className="font-semibold text-muted">{range}</span>
            </p>
            <p className="mt-1 text-sm">{text}</p>
          </div>
        ))}
      </section>

      <section className="mt-14">
        <h2 className="border-t border-foreground pt-3 font-serif text-2xl font-medium tracking-tight">
          The basic rules
        </h2>
        <ul className="mt-4 grid max-w-4xl list-disc grid-cols-1 gap-x-12 gap-y-2 pl-5 leading-relaxed text-ink-2 md:grid-cols-2">
          <li>Each warning sign adds points. The points are listed below.</li>
          <li>
            Points fade: after {rules.half_life_days} days a sign counts half,
            after {rules.half_life_days * 2} days a quarter. After{" "}
            {rules.max_age_days} days it stops counting. (A few signs, like
            overdue results, count until they&apos;re fixed.)
          </li>
          <li>
            A stopped trial (suspended, ended early, or withdrawn) goes straight
            to at least {rules.stopped_floor}, which is red. The trial page
            shows the company&apos;s stated reason, because many stops are
            business decisions.
          </li>
          <li>
            Company-wide signs (executives, layoffs, insider sales) count for
            every trial the company runs. For big companies with{" "}
            {rules.big_company_trial_count}+ cancer trials, they count{" "}
            {rules.big_company_factor === 0.5
              ? "half"
              : rules.big_company_factor}
            , since one sign matters less to a giant.
          </li>
          <li>
            Some signs are counted once even if they show up in several places:
            only the newest layoff and the newest group of insider sales count.
          </li>
          <li>The score can&apos;t go above 100.</li>
        </ul>
      </section>

      <section className="mt-14">
        <h2 className="border-t border-foreground pt-3 font-serif text-2xl font-medium tracking-tight">
          Signs from the trial&apos;s official record
        </h2>
        <p className="mt-3 text-sm text-muted">
          Tremor saves its own copy of each trial record every 4 hours and
          compares it with the last one. Many edits are harmless paperwork;
          those add no points.
        </p>
        <ul className="mt-2 grid grid-cols-1 gap-x-12 md:grid-cols-2">
          {TRIAL_RULES.map((r) => (
            <RuleCard
              key={r.key}
              r={r}
              tested={r.status ? undefined : notYet}
            />
          ))}
        </ul>
      </section>

      <section className="mt-14">
        <h2 className="border-t border-foreground pt-3 font-serif text-2xl font-medium tracking-tight">
          Signs about the company
        </h2>
        <p className="mt-3 text-sm text-muted">
          From SEC filings, state layoff notices, and job boards.
        </p>
        <ul className="mt-2 grid grid-cols-1 gap-x-12 md:grid-cols-2">
          {COMPANY_RULES.map((r) => (
            <RuleCard key={r.key} r={r} tested={tested(r.key)} />
          ))}
        </ul>
      </section>

      <section className="mt-14 max-w-3xl text-sm leading-relaxed">
        <h2 className="border-t border-foreground pt-3 font-serif text-xl font-medium tracking-tight">
          How the points were chosen
        </h2>
        <p className="mt-2">
          The first points were starting guesses. On Nov 11, 2026 we changed
          three of them after checking past cases: layoffs and a key executive
          leaving went from 15 to 10 points each, because they came before bad
          news only a bit more often than a random day. A second executive
          leaving within 6 months got +10 extra, because that came before bad
          news about 1 in 4 times. Signs that can&apos;t be tested yet keep
          their starting points.
        </p>
        <p className="mt-2">
          <Link href="/track-record" className="font-semibold underline">
            See every past case on the track record page
          </Link>
        </p>
      </section>

      <section className="mt-10 max-w-3xl text-sm">
        <h2 className="border-t border-foreground pt-3 font-serif text-xl font-medium tracking-tight">
          Email alerts
        </h2>
        <p className="mt-1 leading-relaxed">
          Big events (the main goal changes, patients are cut, a trial stops, a
          key executive leaves) and score jumps of {rules.big_jump_points}+
          points are emailed right away. Smaller signs and &ldquo;coming
          up&rdquo; reminders go in one daily email.
        </p>
      </section>
    </article>
  );
}
