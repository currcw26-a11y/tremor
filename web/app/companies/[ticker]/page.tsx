import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Suspense } from "react";
import { getCompany, type InsiderTrade } from "@/lib/db";
import { FORM_HELP, FORM_NAMES, filingSummary } from "@/lib/filings";
import { companyName, niceDate } from "@/lib/words";
import { Empty, Ticker, TrialRow } from "../../components";
import { StarButton } from "../../star-button";
import { MoneyLeft } from "./money-left";
import { Hiring, Layoffs } from "./hiring";
import { AskBox } from "../../ask-box";
import { Term } from "../../term";

const COMPANY_SIGNALS = new Set([
  "insider_selling_cluster",
  "key_exec_departure",
  "layoffs",
]);
const BIG_COMPANY = 15; // matches big_company_trial_count in config/tremor.yaml

function money(n: number) {
  if (n >= 1e6) return `$${(n / 1e6).toFixed(1)} million`;
  if (n >= 1e3) return `$${Math.round(n / 1e3)} thousand`;
  return `$${Math.round(n)}`;
}

function role(t: InsiderTrade) {
  if (t.insider_title) return t.insider_title;
  if (t.is_officer) return "Executive";
  if (t.is_director) return "Board member";
  return "Large shareholder";
}

export async function generateMetadata({
  params,
}: PageProps<"/companies/[ticker]">): Promise<Metadata> {
  const { ticker } = await params;
  const { company, trials } = await getCompany(ticker);
  if (!company) return { title: "Company not found", robots: { index: false } };
  const name = companyName(company.name, company.ticker);
  const title = `${name} (${company.ticker})`;
  const description =
    `${name}'s ${trials.length} tracked cancer drug trial${trials.length === 1 ? "" : "s"}, money left, insider trades, ` +
    "executive changes and layoff notices, with worry scores explained in plain English.";
  return {
    title,
    description,
    alternates: { canonical: `/companies/${company.ticker}` },
    openGraph: {
      title,
      description,
      url: `/companies/${company.ticker}`,
      images: "/opengraph-image",
    },
    robots: trials.length ? undefined : { index: false },
  };
}

async function CompanyDetails({
  params,
}: {
  params: PageProps<"/companies/[ticker]">["params"];
}) {
  const { ticker } = await params;
  const { company, trials, filings, trades, jobs, layoffs, jobBoard } =
    await getCompany(ticker);
  if (!company) notFound();

  const signals = (trials[0]?.score_breakdown ?? []).filter((r) =>
    COMPANY_SIGNALS.has(r.type),
  );
  const departures = filings.filter((f) => f.key_exec_departure);
  const sales = trades.filter((t) => t.transaction_code === "S");
  const unplannedSales = sales.filter((t) => !t.is_10b5_1);
  const buys = trades.filter((t) => t.transaction_code === "P");

  return (
    <article>
      <header className="rise border-b border-line pb-8">
        <Ticker symbol={company.ticker} />
        <h1 className="mt-3 font-serif text-4xl font-medium tracking-tight sm:text-5xl">
          {companyName(company.name, company.ticker)}
        </h1>
        <p className="mt-3 max-w-2xl text-ink-2">
          Tremor tracks {trials.length} of its cancer trial
          {trials.length === 1 ? "" : "s"}.
          {trials.length >= BIG_COMPANY &&
            " This is a large company with many drugs, so one trial matters less to it, and company-wide signals count for half."}
        </p>
      </header>

      <div className="mt-10 grid grid-cols-1 gap-x-12 gap-y-14 lg:grid-cols-12">
        <div className="min-w-0 space-y-14 lg:col-span-8">
          <section>
            <h2 className="border-t border-foreground pt-3 font-serif text-2xl font-medium tracking-tight">
              Trials
            </h2>
            <ul className="mt-2">
              {trials.map((t) => (
                <TrialRow key={t.nct_id} t={t} />
              ))}
            </ul>
          </section>

          <section>
            <h2 className="border-t border-foreground pt-3 font-serif text-2xl font-medium tracking-tight">
              Company-wide warning signs
            </h2>
            <p className="mt-3 text-sm text-muted">
              These add points to every one of this company&apos;s trials.
            </p>
            <div className="mt-3">
              {signals.length ? (
                <ul className="divide-y divide-line border-y border-line">
                  {signals.map((s, i) => (
                    <li key={i} className="flex justify-between gap-4 py-3">
                      <span>
                        <span className="font-medium">{s.label}</span>
                        <span className="block text-xs text-muted">
                          Since {niceDate(s.occurred)}
                        </span>
                      </span>
                      <span className="font-mono font-semibold tabular-nums">
                        +{Math.round(s.points * 10) / 10}
                      </span>
                    </li>
                  ))}
                </ul>
              ) : (
                <Empty>None right now.</Empty>
              )}
            </div>
          </section>

          <section>
            <h2 className="border-t border-foreground pt-3 font-serif text-2xl font-medium tracking-tight">
              Key executives leaving
            </h2>
            <p className="mt-3 text-sm text-muted">
              From the last 12 months of the company&apos;s SEC reports.
            </p>
            <div className="mt-3">
              {departures.length ? (
                <ul className="divide-y divide-line border-y border-line">
                  {departures.map((f) => (
                    <li key={f.accession_number} className="py-3">
                      <p className="text-xs text-muted">
                        {niceDate(f.filed_at)}
                      </p>
                      <p className="mt-1 max-w-2xl">
                        &ldquo;{f.departure_details}&rdquo;
                      </p>
                      <a
                        href={f.url}
                        target="_blank"
                        rel="noreferrer"
                        className="mt-1 inline-block text-sm underline"
                      >
                        Read the filing ↗
                      </a>
                    </li>
                  ))}
                </ul>
              ) : (
                <Empty>None found.</Empty>
              )}
            </div>
          </section>

          <section>
            <h2 className="border-t border-foreground pt-3 font-serif text-2xl font-medium tracking-tight">
              Insider trades (last 6 months)
            </h2>
            <p className="mt-3 text-sm text-muted">
              &ldquo;<Term id="insider">Insiders</Term>&rdquo; are executives,
              board members, and big shareholders. Many of their sales are{" "}
              <strong>pre-planned</strong>: scheduled months ahead under a legal
              plan (called <Term id="plan_10b5_1">10b5-1</Term>), so they
              usually say little. Tremor only counts sales that weren&apos;t
              pre-planned.
            </p>
            <p className="mt-3 text-sm">
              {sales.length} sale{sales.length === 1 ? "" : "s"} (
              {unplannedSales.length} not pre-planned) · {buys.length} purchase
              {buys.length === 1 ? "" : "s"}
            </p>
            <div className="mt-3">
              {trades.length ? (
                <ul className="divide-y divide-line border-y border-line">
                  {trades.slice(0, 30).map((t) => (
                    <li
                      key={`${t.accession_number}-${t.line_number}`}
                      className="flex items-start justify-between gap-3 py-3 text-sm"
                    >
                      <span className="min-w-0">
                        <span className="block font-medium">
                          {t.insider_name}
                        </span>
                        <span className="block text-xs text-muted">
                          {role(t)} · {niceDate(t.transaction_date)}
                        </span>
                      </span>
                      <span className="shrink-0 text-right">
                        <span
                          className={`block font-semibold ${t.transaction_code === "S" ? "" : "text-calm"}`}
                        >
                          {t.transaction_code === "S" ? "Sold" : "Bought"}{" "}
                          {Math.round(t.shares ?? 0).toLocaleString()} shares
                        </span>
                        <span className="block text-xs text-muted">
                          {t.price
                            ? `about ${money((t.shares ?? 0) * t.price)} · `
                            : ""}
                          {t.transaction_code === "S"
                            ? t.is_10b5_1
                              ? "pre-planned"
                              : "not pre-planned"
                            : ""}
                        </span>
                      </span>
                    </li>
                  ))}
                </ul>
              ) : (
                <Empty>
                  No insider sales or purchases in the last 6 months.
                </Empty>
              )}
              {trades.length > 30 && (
                <p className="mt-2 text-sm text-muted">
                  Showing the 30 most recent.
                </p>
              )}
            </div>
          </section>

          <section>
            <h2 className="border-t border-foreground pt-3 font-serif text-2xl font-medium tracking-tight">
              Recent <Term id="sec">SEC filings</Term>
            </h2>
            <p className="mt-3 text-sm text-muted">
              Public companies must report important news and their finances to
              the SEC, the US agency that oversees the stock market.
            </p>
            <ul className="mt-3 divide-y divide-line overflow-hidden rounded-lg bg-surface">
              {filings.map((f) => (
                <li key={f.accession_number} className="py-3 text-sm">
                  <a
                    href={f.url}
                    target="_blank"
                    rel="noreferrer"
                    className="group flex justify-between gap-3"
                  >
                    <span>
                      <span className="block font-medium group-hover:underline">
                        {filingSummary(f)}
                      </span>
                      <span
                        className="block text-xs text-muted"
                        title={FORM_HELP[f.form]}
                      >
                        {FORM_NAMES[f.form] ?? f.form} ({f.form})
                      </span>
                    </span>
                    <span className="shrink-0 text-xs text-muted">
                      {niceDate(f.filed_at)}
                    </span>
                  </a>
                </li>
              ))}
              {!filings.length && (
                <li className="py-3 text-muted">None in the last 12 months.</li>
              )}
            </ul>
          </section>
          <AskBox ticker={company.ticker} kind="company" />
        </div>

        <aside className="rise rise-2 min-w-0 space-y-12 lg:col-span-4">
          <StarButton kind="company" id={company.ticker} />
          <section>
            <h2 className="mb-3 border-t border-foreground pt-3 font-serif text-xl font-medium tracking-tight">
              <Term id="runway">Money left</Term>
            </h2>
            <MoneyLeft company={company} filings={filings} />
          </section>

          <section>
            <h2 className="mb-3 border-t border-foreground pt-3 font-serif text-xl font-medium tracking-tight">
              Hiring
            </h2>
            <Hiring jobs={jobs} board={jobBoard} />
          </section>

          <section>
            <h2 className="mb-3 border-t border-foreground pt-3 font-serif text-xl font-medium tracking-tight">
              <Term id="layoff_notice">Layoff notices</Term>
            </h2>
            <Layoffs notices={layoffs} />
          </section>
        </aside>
      </div>
    </article>
  );
}

export default function CompanyPage(props: PageProps<"/companies/[ticker]">) {
  return (
    <Suspense
      fallback={<div className="h-96 animate-pulse rounded-lg bg-line" />}
    >
      <CompanyDetails params={props.params} />
    </Suspense>
  );
}
