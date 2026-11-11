import Link from "next/link";
import { Suspense } from "react";
import { PAGE_SIZE, searchTrials } from "@/lib/db";
import { Empty, TrialRow } from "../components";

export const metadata = {
  title: "All cancer trials",
  description: "Search every Phase 2 and Phase 3 cancer drug trial Tremor tracks, with each one's worry score.",
  alternates: { canonical: "/trials" },
};

async function Results({ searchParams }: { searchParams: PageProps<"/trials">["searchParams"] }) {
  const sp = await searchParams;
  const q = typeof sp.q === "string" ? sp.q : "";
  const page = Math.max(1, Number(sp.page) || 1);
  const { rows, total } = await searchTrials(q, page);
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const link = (p: number) => `/trials?${new URLSearchParams({ ...(q ? { q } : {}), page: String(p) })}`;

  return (
    <>
      <form className="flex gap-2" action="/trials">
        <input
          name="q"
          defaultValue={q}
          placeholder="Search a company, ticker, or cancer…"
          className="min-w-0 flex-1 rounded-xl border border-line bg-surface px-4 py-3 outline-none focus:border-foreground"
        />
        <button className="rounded-xl bg-foreground px-5 font-semibold text-background">Search</button>
      </form>
      <p className="mt-4 text-sm text-muted">
        {total.toLocaleString()} trial{total === 1 ? "" : "s"}
        {q && <> matching &ldquo;{q}&rdquo;</>} · most recently edited first
      </p>
      {rows.length ? (
        <ul className="mt-3 space-y-2">
          {rows.map((t) => (
            <TrialRow key={t.nct_id} t={t} />
          ))}
        </ul>
      ) : (
        <div className="mt-3">
          <Empty>No trials match that search.</Empty>
        </div>
      )}
      {pages > 1 && (
        <nav className="mt-6 flex items-center justify-between text-sm font-semibold">
          {page > 1 ? <Link href={link(page - 1)}>← Newer</Link> : <span />}
          <span className="text-muted">
            Page {page} of {pages}
          </span>
          {page < pages ? <Link href={link(page + 1)}>Older →</Link> : <span />}
        </nav>
      )}
    </>
  );
}

export default function TrialsPage(props: PageProps<"/trials">) {
  return (
    <div>
      <h1 className="text-3xl font-black tracking-tight">All tracked trials</h1>
      <p className="mt-2 text-muted">
        Phase 2 and Phase 3 cancer trials run by companies on the Nasdaq or New York Stock Exchange.
      </p>
      <div className="mt-6">
        <Suspense fallback={<div className="h-96 animate-pulse rounded-xl bg-line" />}>
          <Results searchParams={props.searchParams} />
        </Suspense>
      </div>
    </div>
  );
}
