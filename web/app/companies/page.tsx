import Link from "next/link";
import { Suspense } from "react";
import { getCompanies } from "@/lib/db";
import { companyName } from "@/lib/words";
import { Ticker } from "../components";
import { ScoreBadge } from "../score";

export const metadata = {
  title: "Companies",
  description: "Every company Tremor tracks, with its cancer drug trials and worst current worry score.",
  alternates: { canonical: "/companies" },
};

function months(m: number | null | undefined, burn?: number | null, cash?: number | null) {
  if (m == null) {
    if (cash != null && burn != null && burn <= 0) return <span className="font-sans text-xs text-muted">Not burning cash</span>;
    return <span className="text-muted" title="No recent cash numbers in its SEC reports">—</span>;
  }
  const n = Math.round(m);
  return <span className={n < 12 ? "font-semibold text-foreground" : ""}>{n < 1 ? "under 1" : n} mo</span>;
}

async function List() {
  const companies = await getCompanies();
  return (
    <div className="mt-8">
      <div className="hidden grid-cols-[minmax(0,1fr)_7rem_7rem_9rem] gap-4 border-b border-foreground pb-2 text-xs font-medium text-muted md:grid">
        <span>Company</span>
        <span className="text-right">Trials</span>
        <span className="text-right">Money left</span>
        <span className="text-right">Highest score</span>
      </div>
      <ul>
        {companies.map((c) => (
          <li key={c.ticker} className="border-b border-line">
            <Link
              href={`/companies/${c.ticker}`}
              className="group -mx-3 grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-4 gap-y-1 rounded-md px-3 py-3.5 transition-colors hover:bg-surface md:grid-cols-[minmax(0,1fr)_7rem_7rem_9rem]"
            >
              <span className="flex min-w-0 items-center gap-3">
                <Ticker symbol={c.ticker} />
                <span className="truncate font-medium">{companyName(c.name, c.ticker)}</span>
                <span className="nudge hidden text-muted opacity-0 transition-opacity group-hover:opacity-100 md:inline">→</span>
              </span>
              <span className="col-start-1 row-start-2 text-xs text-muted md:col-start-auto md:row-start-auto md:text-right md:font-mono md:text-sm md:text-foreground">
                {c.count}
                <span className="md:hidden"> tracked trial{c.count === 1 ? "" : "s"}</span>
              </span>
              <span className="hidden text-right font-mono text-sm md:block">{months(c.runway_months, c.monthly_burn_usd, c.cash_usd)}</span>
              <span className="row-span-2 justify-self-end md:row-span-1">
                <ScoreBadge score={c.top} label={c.label} />
              </span>
            </Link>
          </li>
        ))}
      </ul>
      <p className="mt-4 text-sm text-muted">
        Money left = months the company could keep going at its recent spending rate, from its SEC reports.
      </p>
    </div>
  );
}

export default function CompaniesPage() {
  return (
    <div className="rise">
      <h1 className="font-serif text-4xl font-medium tracking-tight sm:text-5xl">Companies</h1>
      <p className="mt-4 max-w-2xl text-ink-2">
        Every company Tremor watches, sorted by its most worrying trial. All trade on the Nasdaq or the New York Stock
        Exchange.
      </p>
      <Suspense fallback={<div className="mt-8 h-96" />}>
        <List />
      </Suspense>
    </div>
  );
}
