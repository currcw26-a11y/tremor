import Link from "next/link";
import { Suspense } from "react";
import { getCompanies } from "@/lib/db";
import { Ticker } from "../components";
import { ScoreBadge } from "../score";

export const metadata = {
  title: "Companies",
  description: "Every company Tremor tracks, with its cancer drug trials and worst current worry score.",
  alternates: { canonical: "/companies" },
};

async function List() {
  const companies = await getCompanies();
  return (
    <ul className="mt-6 divide-y divide-line overflow-hidden rounded-xl border border-line bg-surface">
      {companies.map((c) => (
        <li key={c.ticker}>
          <Link href={`/companies/${c.ticker}`} className="flex items-center gap-3 p-3 hover:bg-background">
            <Ticker symbol={c.ticker} />
            <span className="min-w-0 flex-1">
              <span className="block truncate font-semibold">{c.name}</span>
              <span className="text-xs text-muted">
                {c.count} tracked trial{c.count === 1 ? "" : "s"} · highest score
              </span>
            </span>
            <ScoreBadge score={c.top} label={c.label} />
          </Link>
        </li>
      ))}
    </ul>
  );
}

export default function CompaniesPage() {
  return (
    <div>
      <h1 className="text-3xl font-black tracking-tight">Companies</h1>
      <p className="mt-2 text-muted">
        Every company Tremor watches, sorted by its most worrying trial. All trade on the Nasdaq or the New York
        Stock Exchange.
      </p>
      <Suspense fallback={<div className="mt-6 h-96 animate-pulse rounded-xl bg-line" />}>
        <List />
      </Suspense>
    </div>
  );
}
