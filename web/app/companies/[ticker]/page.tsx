import { notFound } from "next/navigation";
import { Suspense } from "react";
import { getCompany, type InsiderTrade } from "@/lib/db";
import { FORM_HELP, FORM_NAMES, filingSummary } from "@/lib/filings";
import { niceDate } from "@/lib/words";
import { Empty, Ticker, TrialRow } from "../../components";
import { StarButton } from "../../star-button";
import { MoneyLeft } from "./money-left";
import { Hiring, Layoffs } from "./hiring";
import { AskBox } from "../../ask-box";

const COMPANY_SIGNALS = new Set(["insider_selling_cluster", "key_exec_departure", "layoffs"]);
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

async function CompanyDetails({ params }: { params: PageProps<"/companies/[ticker]">["params"] }) {
  const { ticker } = await params;
  const { company, trials, filings, trades, jobs, layoffs, jobBoard } = await getCompany(ticker);
  if (!company) notFound();

  const signals = (trials[0]?.score_breakdown ?? []).filter((r) => COMPANY_SIGNALS.has(r.type));
  const departures = filings.filter((f) => f.key_exec_departure);
  const sales = trades.filter((t) => t.transaction_code === "S");
  const unplannedSales = sales.filter((t) => !t.is_10b5_1);
  const buys = trades.filter((t) => t.transaction_code === "P");

  return (
    <article className="space-y-10">
      <header>
        <Ticker symbol={company.ticker} />
        <h1 className="mt-2 text-3xl font-black tracking-tight">{company.name}</h1>
        <div className="mt-3">
          <StarButton kind="company" id={company.ticker} />
        </div>
        <p className="mt-2 text-muted">
          Tremor tracks {trials.length} of its cancer trials.
          {trials.length >= BIG_COMPANY &&
            " This is a large company with many drugs, so one trial matters less to it, and company-wide signals count for half."}
        </p>
      </header>

      <section>
        <h2 className="mb-3 text-xl font-bold">Money left</h2>
        <MoneyLeft company={company} filings={filings} />
      </section>

      <section>
        <h2 className="text-xl font-bold">Company-wide warning signs</h2>
        <p className="text-sm text-muted">These add points to every one of this company&apos;s trials.</p>
        <div className="mt-3">
          {signals.length ? (
            <ul className="space-y-2">
              {signals.map((s, i) => (
                <li key={i} className="flex justify-between gap-4 rounded-xl border border-line bg-surface p-3">
                  <span>
                    <span className="font-medium">{s.label}</span>
                    <span className="block text-xs text-muted">Since {niceDate(s.occurred)}</span>
                  </span>
                  <span className="font-bold tabular-nums">+{Math.round(s.points * 10) / 10}</span>
                </li>
              ))}
            </ul>
          ) : (
            <Empty>None right now.</Empty>
          )}
        </div>
      </section>

      <AskBox ticker={company.ticker} kind="company" />

      <section>
        <h2 className="text-xl font-bold">Trials</h2>
        <ul className="mt-3 space-y-2">
          {trials.map((t) => (
            <TrialRow key={t.nct_id} t={t} />
          ))}
        </ul>
      </section>

      <section>
        <h2 className="text-xl font-bold">Key executives leaving</h2>
        <p className="text-sm text-muted">From the last 12 months of the company&apos;s SEC reports.</p>
        <div className="mt-3">
          {departures.length ? (
            <ul className="space-y-2">
              {departures.map((f) => (
                <li key={f.accession_number} className="rounded-xl border border-line bg-surface p-3">
                  <p className="text-xs text-muted">{niceDate(f.filed_at)}</p>
                  <p className="mt-1">&ldquo;{f.departure_details}&rdquo;</p>
                  <a href={f.url} target="_blank" rel="noreferrer" className="mt-1 inline-block text-sm underline">
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
        <h2 className="text-xl font-bold">Insider trades (last 6 months)</h2>
        <p className="text-sm text-muted">
          &ldquo;Insiders&rdquo; are executives, board members, and big shareholders. Many of their sales are{" "}
          <strong>pre-planned</strong>: scheduled months ahead under a legal plan (called 10b5-1), so they usually
          say little. Tremor only counts sales that weren&apos;t pre-planned.
        </p>
        <p className="mt-3 text-sm">
          {sales.length} sale{sales.length === 1 ? "" : "s"} ({unplannedSales.length} not pre-planned) · {buys.length}{" "}
          purchase{buys.length === 1 ? "" : "s"}
        </p>
        <div className="mt-3">
          {trades.length ? (
            <ul className="divide-y divide-line overflow-hidden rounded-xl border border-line bg-surface">
              {trades.slice(0, 30).map((t) => (
                <li key={`${t.accession_number}-${t.line_number}`} className="flex items-start justify-between gap-3 p-3 text-sm">
                  <span className="min-w-0">
                    <span className="block font-medium">{t.insider_name}</span>
                    <span className="block text-xs text-muted">
                      {role(t)} · {niceDate(t.transaction_date)}
                    </span>
                  </span>
                  <span className="shrink-0 text-right">
                    <span className={`block font-semibold ${t.transaction_code === "S" ? "" : "text-calm"}`}>
                      {t.transaction_code === "S" ? "Sold" : "Bought"} {Math.round(t.shares ?? 0).toLocaleString()} shares
                    </span>
                    <span className="block text-xs text-muted">
                      {t.price ? `about ${money((t.shares ?? 0) * t.price)} · ` : ""}
                      {t.transaction_code === "S" ? (t.is_10b5_1 ? "pre-planned" : "not pre-planned") : ""}
                    </span>
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <Empty>No insider sales or purchases in the last 6 months.</Empty>
          )}
          {trades.length > 30 && <p className="mt-2 text-sm text-muted">Showing the 30 most recent.</p>}
        </div>
      </section>

      <section>
        <h2 className="mb-3 text-xl font-bold">Hiring</h2>
        <Hiring jobs={jobs} board={jobBoard} />
      </section>

      <section>
        <h2 className="mb-3 text-xl font-bold">Layoff notices</h2>
        <Layoffs notices={layoffs} />
      </section>

      <section>
        <h2 className="text-xl font-bold">Recent SEC filings</h2>
        <p className="text-sm text-muted">
          Public companies must report important news and their finances to the SEC, the US agency that oversees
          the stock market.
        </p>
        <ul className="mt-3 divide-y divide-line overflow-hidden rounded-xl border border-line bg-surface">
          {filings.map((f) => (
            <li key={f.accession_number} className="p-3 text-sm">
              <a href={f.url} target="_blank" rel="noreferrer" className="flex justify-between gap-3 hover:underline">
                <span>
                  <span className="block font-medium">{filingSummary(f)}</span>
                  <span className="block text-xs text-muted" title={FORM_HELP[f.form]}>
                    {FORM_NAMES[f.form] ?? f.form} ({f.form})
                  </span>
                </span>
                <span className="shrink-0 text-xs text-muted">{niceDate(f.filed_at)}</span>
              </a>
            </li>
          ))}
          {!filings.length && <li className="p-3 text-muted">None in the last 12 months.</li>}
        </ul>
      </section>


    </article>
  );
}

export default function CompanyPage(props: PageProps<"/companies/[ticker]">) {
  return (
    <Suspense fallback={<div className="h-96 animate-pulse rounded-xl bg-line" />}>
      <CompanyDetails params={props.params} />
    </Suspense>
  );
}
