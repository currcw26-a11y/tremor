"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import type { ScoreLabel, Trial } from "@/lib/db";
import { signIn, supabase, useUser } from "@/lib/supabase-browser";
import { companyName } from "@/lib/words";
import { Empty, Ticker, TrialRow } from "../components";

type Row<T> = { created_at: string } & T;

export function Watchlist() {
  const user = useUser();
  const [trials, setTrials] = useState<Trial[] | null>(null);
  const [companies, setCompanies] = useState<{ ticker: string; name: string }[] | null>(null);

  useEffect(() => {
    if (!user) return;
    const sb = supabase();
    sb.from("watch_trials")
      .select(
        "created_at, trials(nct_id,title,sponsor_name,ticker,phases,overall_status,enrollment,primary_completion_date,last_update_posted,score,score_label)",
      )
      .order("created_at", { ascending: false })
      .then(({ data }) =>
        setTrials(((data ?? []) as unknown as Row<{ trials: Trial }>[]).map((r) => r.trials).filter(Boolean)),
      );
    sb.from("watch_companies")
      .select("created_at, ticker, companies(name)")
      .order("created_at", { ascending: false })
      .then(({ data }) =>
        setCompanies(
          ((data ?? []) as unknown as Row<{ ticker: string; companies: { name: string } }>[]).map((r) => ({
            ticker: r.ticker,
            name: r.companies?.name ?? r.ticker,
          })),
        ),
      );
  }, [user]);

  if (user === undefined) return <div className="h-40 animate-pulse rounded-lg bg-line" />;
  if (!user)
    return (
      <div className="max-w-xl border-t border-foreground pt-5">
        <p className="font-semibold">Sign in to keep a watchlist.</p>
        <p className="mt-3 text-sm text-muted">Star trials and companies, and Tremor will email you when something changes.</p>
        <button onClick={() => signIn("/watchlist")} className="mt-4 rounded-md bg-foreground px-4 py-2 font-medium text-background transition-colors hover:bg-navy-2">
          Sign in with Google
        </button>
      </div>
    );

  return (
    <div className="space-y-8">
      <section>
        <h2 className="border-t border-foreground pt-3 font-serif text-2xl font-medium tracking-tight">Trials</h2>
        <div className="mt-3">
          {trials === null ? (
            <div className="h-24 animate-pulse rounded-lg bg-line" />
          ) : trials.length ? (
            <ul className="space-y-2">
              {trials.map((t) => (
                <TrialRow key={t.nct_id} t={{ ...t, score_label: t.score_label as ScoreLabel }} />
              ))}
            </ul>
          ) : (
            <Empty>
              No starred trials yet. Open any trial and tap <strong>Add to watchlist</strong>.{" "}
              <Link href="/trials" className="underline">Browse trials</Link>
            </Empty>
          )}
        </div>
      </section>
      <section>
        <h2 className="border-t border-foreground pt-3 font-serif text-2xl font-medium tracking-tight">Companies</h2>
        <div className="mt-3">
          {companies === null ? (
            <div className="h-16 animate-pulse rounded-lg bg-line" />
          ) : companies.length ? (
            <ul className="max-w-2xl divide-y divide-line border-y border-line">
              {companies.map((c) => (
                <li key={c.ticker}>
                  <Link href={`/companies/${c.ticker}`} className="flex items-center gap-3 p-3 hover:bg-background">
                    <Ticker symbol={c.ticker} />
                    <span className="font-semibold">{companyName(c.name, c.ticker)}</span>
                  </Link>
                </li>
              ))}
            </ul>
          ) : (
            <Empty>
              No starred companies yet. <Link href="/companies" className="underline">Browse companies</Link>
            </Empty>
          )}
        </div>
      </section>
    </div>
  );
}
