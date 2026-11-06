// Reads Tremor's data from Supabase. The website can only READ (database security rules
// block writes), so the public "publishable" key is safe to use here.
import { cacheLife } from "next/cache";

const URL = (process.env.NEXT_PUBLIC_SUPABASE_URL ?? "").trim().replace(/\/+$/, "");
const KEY = (process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY ?? "").trim();

async function query<T>(table: string, params: Record<string, string>, withCount = false) {
  if (!URL || !KEY) {
    throw new Error(
      "Missing settings: NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY must both be set " +
        "(in web/.env.local on your computer, or in Vercel → Project → Settings → Environment Variables).",
    );
  }
  if (!URL.startsWith("https://") || URL.includes("/rest/")) {
    throw new Error(`NEXT_PUBLIC_SUPABASE_URL looks wrong: "${URL}". It should look like https://abcd.supabase.co`);
  }
  const res = await fetch(`${URL}/rest/v1/${table}?${new URLSearchParams(params)}`, {
    headers: { apikey: KEY, ...(withCount ? { Prefer: "count=exact" } : {}) },
  });
  if (res.status === 401 || res.status === 403) {
    throw new Error(
      `Supabase rejected the key (${res.status}). Check NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY: it should be the ` +
        "sb_publishable_ key from Supabase → Project Settings → API Keys, with no spaces.",
    );
  }
  if (!res.ok) throw new Error(`Database error ${res.status}: ${await res.text()}`);
  const total = Number(res.headers.get("content-range")?.split("/")[1] ?? 0);
  return { rows: (await res.json()) as T[], total };
}

export type Trial = {
  nct_id: string;
  title: string;
  sponsor_name: string;
  ticker: string;
  phases: string[];
  overall_status: string;
  conditions: string[];
  interventions: string[];
  primary_outcomes: { measure: string; description?: string; timeFrame?: string }[];
  enrollment: number | null;
  enrollment_type: string | null;
  start_date: string | null;
  primary_completion_date: string | null;
  completion_date: string | null;
  results_first_posted: string | null;
  last_update_posted: string | null;
  last_checked_at: string;
};

export type Change = {
  id: number;
  nct_id: string;
  detected_at: string;
  change_type: string;
  field: string | null;
  old_value: unknown;
  new_value: unknown;
  is_paperwork: boolean;
  details: Record<string, unknown> | null;
  trials?: { title: string; ticker: string; sponsor_name: string };
};

const LIST_COLUMNS =
  "nct_id,title,sponsor_name,ticker,phases,overall_status,enrollment,primary_completion_date,last_update_posted";

export async function getStats() {
  "use cache";
  cacheLife("minutes");
  const [trials, companies, runs] = await Promise.all([
    query("trials", { select: "nct_id", tracked: "eq.true", limit: "1" }, true),
    query("companies", { select: "ticker", limit: "1" }, true),
    query<{ finished_at: string; status: string }>("pipeline_runs", {
      select: "finished_at,status",
      status: "eq.success",
      order: "finished_at.desc",
      limit: "1",
    }),
  ]);
  return { trials: trials.total, companies: companies.total, lastRun: runs.rows[0]?.finished_at ?? null };
}

export async function getRecentChanges(limit = 20, includePaperwork = false) {
  "use cache";
  cacheLife("minutes");
  const params: Record<string, string> = {
    select: "*,trials(title,ticker,sponsor_name)",
    order: "detected_at.desc,id.desc",
    limit: String(limit),
  };
  if (!includePaperwork) params.is_paperwork = "eq.false";
  return (await query<Change>("trial_changes", params)).rows;
}

export const PAGE_SIZE = 25;

export async function searchTrials(q: string, page: number) {
  "use cache";
  cacheLife("minutes");
  const params: Record<string, string> = {
    select: LIST_COLUMNS,
    tracked: "eq.true",
    order: "last_update_posted.desc.nullslast",
    limit: String(PAGE_SIZE),
    offset: String((page - 1) * PAGE_SIZE),
  };
  const clean = q.replace(/[^\p{L}\p{N} .-]/gu, "").trim(); // stop symbols breaking the search
  if (clean) params.or = `(ticker.ilike.*${clean}*,sponsor_name.ilike.*${clean}*,title.ilike.*${clean}*)`;
  return query<Trial>("trials", params, true);
}

export async function getTrial(nct: string) {
  "use cache";
  cacheLife("minutes");
  const [trial, changes] = await Promise.all([
    query<Trial>("trials", { select: "*", nct_id: `eq.${nct}` }),
    query<Change>("trial_changes", { select: "*", nct_id: `eq.${nct}`, order: "detected_at.desc" }),
  ]);
  return { trial: trial.rows[0] ?? null, changes: changes.rows };
}
