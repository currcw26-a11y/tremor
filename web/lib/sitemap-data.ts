import { cacheLife } from "next/cache";

const URL = process.env.NEXT_PUBLIC_SUPABASE_URL;
const KEY = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY;

async function all<T>(table: string, params: Record<string, string>): Promise<T[]> {
  const rows: T[] = [];
  for (let offset = 0; ; offset += 1000) {
    const res = await fetch(`${URL}/rest/v1/${table}?${new URLSearchParams({ ...params, limit: "1000", offset: String(offset) })}`, {
      headers: { apikey: KEY ?? "" },
    });
    if (!res.ok) throw new Error(`Database error ${res.status}`);
    const page = (await res.json()) as T[];
    rows.push(...page);
    if (page.length < 1000) return rows;
  }
}

/** Every tracked trial (with its last official update) and every company that has one. */
export async function sitemapData() {
  "use cache";
  cacheLife("hours");
  const trials = await all<{ nct_id: string; ticker: string; last_update_posted: string | null }>("trials", {
    select: "nct_id,ticker,last_update_posted",
    tracked: "eq.true",
    order: "nct_id",
  });
  return { trials, tickers: [...new Set(trials.map((t) => t.ticker))].sort() };
}
