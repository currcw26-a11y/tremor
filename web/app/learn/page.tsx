import type { Metadata } from "next";
import Link from "next/link";
import { getTrackRecord } from "@/lib/db";
import { Term } from "../term";

export const metadata: Metadata = {
  title: "How biotech stocks move · Tremor",
  description: "A 2-minute guide for people who have never bought a stock: why small drug companies' stocks jump and crash, and how to read Tremor.",
};

function Step({ n, title, children }: { n: number; title: string; children: React.ReactNode }) {
  return (
    <section className="mt-7">
      <h2 className="flex items-baseline gap-2 text-xl font-bold">
        <span className="text-sm font-black text-muted">{n}</span>
        {title}
      </h2>
      <div className="mt-2 space-y-2 leading-relaxed">{children}</div>
    </section>
  );
}

const ROAD = ["Phase 1", "Phase 2", "Phase 3", "FDA decision", "Sold to patients"];

export default async function LearnPage() {
  const { summaries } = await getTrackRecord();
  const exec = summaries.find((s) => s.signal_type === "key_exec_departure");

  return (
    <article className="max-w-2xl">
      <p className="text-sm font-semibold text-muted">2-minute read</p>
      <h1 className="mt-1 text-3xl font-black tracking-tight">How biotech stocks move</h1>
      <p className="mt-2 text-muted">For anyone who has never bought a stock. Tap any dotted word for a quick definition.</p>

      <Step n={1} title="A stock is a slice of a company">
        <p>
          Owning a <Term id="stock">stock</Term> means owning a tiny piece of a company. Its price is basically a group
          guess about what the company will be worth in the future. When that guess changes, the price moves. Each stock
          has a short code called a <Term id="ticker">ticker</Term>.
        </p>
      </Step>

      <Step n={2} title="Why small drug companies swing so hard">
        <p>
          Many small biotech companies don&apos;t sell anything yet. Their whole value is a bet that one or two drugs
          will work. So a single piece of news about that drug can move the stock a lot, up or down, in one day.
        </p>
        <p className="rounded-xl border border-line bg-surface p-3 text-sm">
          Example from Tremor&apos;s own data: when Soligenix announced in April 2026 that a trial was being stopped
          because the drug wasn&apos;t working well enough, its stock fell 76% from the day before to the day after.
        </p>
      </Step>

      <Step n={3} title="The road every drug travels">
        <ol className="flex flex-wrap items-center gap-1.5 text-sm font-semibold" aria-label="Steps a drug goes through">
          {ROAD.map((s, i) => (
            <li key={s} className="flex items-center gap-1.5">
              <span className="rounded-lg border border-line bg-surface px-2 py-1">{s}</span>
              {i < ROAD.length - 1 && <span aria-hidden className="text-muted">→</span>}
            </li>
          ))}
        </ol>
        <p>
          A drug is tested in a series of <Term id="clinical_trial">clinical trials</Term>: <Term id="phase1">Phase 1</Term>{" "}
          checks safety, <Term id="phase2">Phase 2</Term> checks whether it seems to work, and{" "}
          <Term id="phase3">Phase 3</Term> is the big final test. Then the <Term id="fda">FDA</Term> decides whether it
          can be sold. A drug can fail at any step, and most drugs that start this road never make it to the end.
          Tremor watches Phase 2 and Phase 3 cancer trials.
        </p>
      </Step>

      <Step n={4} title="The big days">
        <p>Stocks of small drug companies often move most on a few kinds of days:</p>
        <ul className="list-disc space-y-1 pl-5">
          <li>Trial results come out, especially on the trial&apos;s <Term id="primary_outcome">main goal</Term>.</li>
          <li>
            The FDA decides on a drug. Its deadline is called a <Term id="pdufa">PDUFA date</Term>.
          </li>
          <li>
            Outside experts discuss the drug at an <Term id="fda_advisory">FDA advisory meeting</Term>.
          </li>
        </ul>
        <p>
          Tremor&apos;s{" "}
          <Link href="/upcoming" className="font-semibold underline">
            Coming up
          </Link>{" "}
          page lists these dates when they&apos;re known.
        </p>
      </Step>

      <Step n={5} title="Money matters">
        <p>
          Running trials is expensive, and small companies spend cash every month. Tremor shows each company&apos;s{" "}
          <Term id="runway">money left</Term>. When it runs low, companies often raise more by{" "}
          <Term id="dilution">selling new shares</Term>, which usually lowers the price of each existing share, even if
          the drug is doing fine.
        </p>
      </Step>

      <Step n={6} title="Why prices don't always react the way you'd expect">
        <ul className="list-disc space-y-1 pl-5">
          <li>Professional investors watch the same public records, so some news is &ldquo;already in the price.&rdquo;</li>
          <li>Good results can still make a stock fall if people hoped for even better.</li>
          <li>Bad news about one drug matters less to a big company with many drugs.</li>
        </ul>
      </Step>

      <Step n={7} title="How to read Tremor">
        <ul className="list-disc space-y-1 pl-5">
          <li>
            The <Term id="worry_score">worry score</Term> counts warning signs. It is not a prediction.
          </li>
          <li>
            Most warning signs are followed by nothing bad.
            {exec && exec.cases > 0 && (
              <>
                {" "}
                For example, after a key executive left a smaller cancer-drug company, {exec.fine} out of {exec.cases} times
                no trial was stopped in the next year.
              </>
            )}
          </li>
          <li>Many edits to trial records are harmless paperwork. Tremor says so when it can tell.</li>
          <li>
            Always check the source: every change links to the official record or filing. And see how past warning signs
            turned out on the{" "}
            <Link href="/track-record" className="font-semibold underline">
              track record
            </Link>{" "}
            page.
          </li>
        </ul>
        <p className="rounded-xl bg-shaky/10 p-3 text-sm">
          Tremor shows what changed and what happened in similar past cases. It never tells anyone to buy or sell, and
          nothing here is advice about your own money.
        </p>
      </Step>

      <p className="mt-8 text-sm">
        <Link href="/glossary" className="underline">
          All words to know
        </Link>
        {" · "}
        <Link href="/how-it-works" className="underline">
          How the score works
        </Link>
      </p>
    </article>
  );
}
