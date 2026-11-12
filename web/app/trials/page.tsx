import Link from "next/link";
import { Suspense } from "react";
import { PAGE_SIZE, searchTrials } from "@/lib/db";
import { BANDS } from "@/lib/score";
import { Empty, TrialRow } from "../components";
import { Shape } from "../score";

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
      <form className="flex items-end gap-3" action="/trials" role="search">
        <label className="min-w-0 flex-1">
          <span className="sr-only">Search trials</span>
          <input
            name="q"
            defaultValue={q}
            placeholder="Search a company, ticker, or cancer…"
            className="w-full border-b-2 border-foreground bg-transparent px-0 py-2.5 text-lg outline-none placeholder:text-muted focus:border-navy-2"
          />
        </label>
        <button className="rounded-md bg-foreground px-5 py-2.5 text-sm font-medium text-background transition-colors hover:bg-navy-2">
          Search
        </button>
      </form>
      <p className="mt-4 text-sm text-muted">
        {total.toLocaleString()} trial{total === 1 ? "" : "s"}
        {q && <> matching &ldquo;{q}&rdquo;</>} · most recently edited first
      </p>
      {rows.length ? (
        <ul className="mt-2 border-t border-line">
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
        <nav className="mt-8 flex items-center justify-between border-t border-line pt-4 text-sm">
          {page > 1 ? <Link href={link(page - 1)} className="link-grow font-medium">← Newer</Link> : <span />}
          <span className="font-mono text-xs text-muted">
            Page {page} of {pages}
          </span>
          {page < pages ? <Link href={link(page + 1)} className="font-medium"><span className="link-grow">Older</span> <span className="nudge">→</span></Link> : <span />}
        </nav>
      )}
    </>
  );
}

export default function TrialsPage(props: PageProps<"/trials">) {
  return (
    <div className="grid grid-cols-1 gap-12 lg:grid-cols-12">
      <div className="rise min-w-0 lg:col-span-8">
        <h1 className="font-serif text-4xl font-medium tracking-tight sm:text-5xl">All tracked trials</h1>
        <p className="mt-4 max-w-xl text-ink-2">
          Phase 2 and Phase 3 cancer trials run by companies on the Nasdaq or New York Stock Exchange.
        </p>
        <div className="mt-8">
          <Suspense fallback={<div className="h-96" />}>
            <Results searchParams={props.searchParams} />
          </Suspense>
        </div>
      </div>
      <aside className="rise rise-2 hidden lg:col-span-4 lg:block">
        <div className="sticky top-24 space-y-8 text-sm">
          <div>
            <p className="border-t border-foreground pt-3 text-sm font-semibold text-foreground">
              Reading the scores
            </p>
            <ul className="mt-3 space-y-3">
              {(["calm", "shaky", "tremor"] as const).map((l) => (
                <li key={l} className="flex gap-3">
                  <span className={`mt-0.5 ${BANDS[l].mark}`}>
                    <Shape label={l} size={11} />
                  </span>
                  <span>
                    <span className={`font-medium ${BANDS[l].color}`}>{BANDS[l].name}.</span>{" "}
                    <span className="text-ink-2">{BANDS[l].meaning}</span>
                  </span>
                </li>
              ))}
            </ul>
            <Link href="/how-it-works" className="mt-4 inline-block text-ink-2 hover:text-foreground">
              <span className="link-grow">How the score works</span>
            </Link>
          </div>
          <div>
            <p className="border-t border-foreground pt-3 text-sm font-semibold text-foreground">
              Search tips
            </p>
            <p className="mt-3 leading-relaxed text-ink-2">
              Try a ticker like <span className="font-mono text-foreground">MRK</span>, a company name, or a kind of cancer
              like &ldquo;lung&rdquo; or &ldquo;leukemia&rdquo;.
            </p>
          </div>
        </div>
      </aside>
    </div>
  );
}
