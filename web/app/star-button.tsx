"use client";
// Star a trial or company to add it to your watchlist. Signed-out visitors are asked to sign in first.
import { useEffect, useState } from "react";
import { signIn, supabase, useUser } from "@/lib/supabase-browser";

const TABLES = { trial: ["watch_trials", "nct_id"], company: ["watch_companies", "ticker"] } as const;

export function StarButton({ kind, id }: { kind: "trial" | "company"; id: string }) {
  const user = useUser();
  const [starred, setStarred] = useState<boolean | null>(null);
  const [busy, setBusy] = useState(false);
  const [table, column] = TABLES[kind];

  useEffect(() => {
    if (!user) return;
    supabase()
      .from(table)
      .select(column)
      .eq(column, id)
      .maybeSingle()
      .then(({ data }) => setStarred(!!data));
  }, [user, table, column, id]);

  async function toggle() {
    if (!user) return signIn();
    setBusy(true);
    const sb = supabase();
    const { error } = starred
      ? await sb.from(table).delete().eq(column, id)
      : await sb.from(table).insert(kind === "trial" ? { nct_id: id } : { ticker: id });
    if (!error) setStarred(!starred);
    setBusy(false);
  }

  const on = !!user && starred === true;
  return (
    <button
      onClick={toggle}
      disabled={busy || (!!user && starred === null)}
      aria-pressed={on}
      className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-sm font-semibold transition ${
        on ? "border-foreground bg-foreground text-background" : "border-line bg-surface hover:border-foreground"
      }`}
    >
      <span aria-hidden>{on ? "★" : "☆"}</span>
      {on ? "On your watchlist" : "Add to watchlist"}
    </button>
  );
}
