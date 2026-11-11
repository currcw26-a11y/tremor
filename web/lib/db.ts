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

/** Like query(), but follows pages: the database returns at most 1,000 rows per request. */
async function queryAll<T>(table: string, params: Record<string, string>) {
  const rows: T[] = [];
  for (let offset = 0; ; offset += 1000) {
    const page = await query<T>(table, { ...params, limit: "1000", offset: String(offset) });
    rows.push(...page.rows);
    if (page.rows.length < 1000) return rows;
  }
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
  score: number;
  score_label: ScoreLabel;
  score_breakdown: Reason[] | null;
  outlook?: Outlook | null;
};

/** The upside/downside breakdown, computed by the pipeline (pipeline/tremor/outlook.py). */
export type PastCases = {
  type: string;
  cases: number;
  bad?: number;
  fine?: number;
  has_history: boolean;
  confidence?: "low" | "medium" | "high";
  sentences: string[];
};
export type Outlook = {
  signals: PastCases[];
  stakes: { level: "high" | "medium" | "low"; trial_count: number; text: string };
  next_event: { date: string; passed: boolean } | null;
  notes: string[];
};

export type ScoreLabel = "calm" | "shaky" | "tremor";

/** One reason behind a score, written by the pipeline's scoring engine. */
export type Reason = {
  type: string;
  label: string;
  occurred: string;
  base_points: number;
  points: number;
  fades: boolean;
  source: Record<string, unknown>;
};

export type ScorePoint = { computed_at: string; new_score: number; new_label: ScoreLabel };

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
  explanation: string | null;
  trials?: { title: string; ticker: string; sponsor_name: string; score: number; score_label: ScoreLabel };
};

const LIST_COLUMNS =
  "nct_id,title,sponsor_name,ticker,phases,overall_status,enrollment,primary_completion_date,last_update_posted,score,score_label";

// Changes that are usually routine. Hidden on the home feed unless you ask to see them.
export const MINOR_TYPES = [
  "status_changed",
  "date_small_change",
  "date_moved_earlier",
  "enrollment_small_cut",
  "enrollment_increased",
  "primary_outcome_reworded",
  "paperwork",
];

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

export async function getRecentChanges(limit = 30, includeMinor = false) {
  "use cache";
  cacheLife("minutes");
  const params: Record<string, string> = {
    // !inner + the filter below: only changes on trials Tremor still tracks
    select: "*,trials!inner(title,ticker,sponsor_name,score,score_label,tracked)",
    "trials.tracked": "eq.true",
    order: "detected_at.desc,id.desc",
    limit: String(limit),
  };
  if (!includeMinor) params.change_type = `not.in.(${MINOR_TYPES.join(",")})`;
  return (await query<Change>("trial_changes", params)).rows;
}

export async function getTopWorries(limit = 8) {
  "use cache";
  cacheLife("minutes");
  return (
    await query<Trial>("trials", {
      select: "nct_id,title,sponsor_name,ticker,score,score_label,score_breakdown",
      tracked: "eq.true",
      score: "gt.0",
      order: "score.desc,nct_id",
      limit: String(limit),
    })
  ).rows;
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
  const [trial, changes, history] = await Promise.all([
    query<Trial>("trials", { select: "*", nct_id: `eq.${nct}` }),
    query<Change>("trial_changes", { select: "*", nct_id: `eq.${nct}`, order: "detected_at.desc,id.desc" }),
    query<ScorePoint>("score_history", {
      select: "computed_at,new_score,new_label",
      nct_id: `eq.${nct}`,
      order: "computed_at",
    }),
  ]);
  const t = trial.rows[0] ?? null;
  const company = t
    ? (await query<Company>("companies", { select: "*", ticker: `eq.${t.ticker}` })).rows[0] ?? null
    : null;
  return { trial: t, changes: changes.rows, history: history.rows, company };
}

export type Company = {
  ticker: string;
  name: string;
  cik: string;
  cash_usd: number | null;
  monthly_burn_usd: number | null;
  runway_months: number | null;
  finances_as_of: string | null;
  burn_period_months: number | null;
  finances_form: string | null;
};
export type Filing = {
  accession_number: string;
  form: string;
  filed_at: string;
  items: string[];
  url: string;
  description: string | null;
  key_exec_departure: boolean | null;
  departure_details: string | null;
};
export type InsiderTrade = {
  accession_number: string;
  line_number: number;
  insider_name: string | null;
  insider_title: string | null;
  is_officer: boolean | null;
  is_director: boolean | null;
  transaction_date: string | null;
  transaction_code: string;
  shares: number | null;
  price: number | null;
  is_10b5_1: boolean | null;
  url: string;
};

export type JobCount = { day: string; total_jobs: number; clinical_jobs: number };
export type LayoffNotice = { state: string; company_name: string; notice_date: string | null; employees: number | null; location: string | null };

function daysAgo(n: number) {
  // Used only inside cached functions, so it is fixed per cache entry (fine for "last 6 months")
  return new Date(Date.now() - n * 86_400_000).toISOString().slice(0, 10);
}

export async function getCompanies() {
  "use cache";
  cacheLife("hours");
  const [companies, trials] = await Promise.all([
    query<Company>("companies", { select: "ticker,name,cik", order: "ticker" }),
    queryAll<{ ticker: string; score: number; score_label: ScoreLabel }>("trials", {
      select: "ticker,score,score_label",
      tracked: "eq.true",
      order: "nct_id",
    }),
  ]);
  const stats = new Map<string, { count: number; top: number; label: ScoreLabel }>();
  for (const t of trials) {
    const s = stats.get(t.ticker) ?? { count: 0, top: -1, label: "calm" as ScoreLabel };
    s.count += 1;
    if (t.score > s.top) Object.assign(s, { top: t.score, label: t.score_label });
    stats.set(t.ticker, s);
  }
  return companies.rows
    .map((c) => ({ ...c, ...(stats.get(c.ticker) ?? { count: 0, top: 0, label: "calm" as ScoreLabel }) }))
    .filter((c) => c.count > 0)
    .sort((a, b) => b.top - a.top || b.count - a.count);
}

export async function getCompany(ticker: string) {
  "use cache";
  cacheLife("minutes");
  const t = ticker.toUpperCase().replace(/[^A-Z.]/g, "");
  const [company, trials, filings, trades] = await Promise.all([
    query<Company>("companies", { select: "*", ticker: `eq.${t}` }),
    query<Trial>("trials", {
      select: LIST_COLUMNS + ",score_breakdown",
      ticker: `eq.${t}`,
      tracked: "eq.true",
      order: "score.desc,last_update_posted.desc.nullslast",
    }),
    query<Filing>("sec_filings", {
      select: "accession_number,form,filed_at,items,url,description,key_exec_departure,departure_details",
      ticker: `eq.${t}`,
      filed_at: `gte.${daysAgo(365)}`,
      form: "not.in.(4,4/A)", // insider trade forms are shown separately
      order: "filed_at.desc",
      limit: "40",
    }),
    query<InsiderTrade>("insider_trades", {
      select:
        "accession_number,line_number,insider_name,insider_title,is_officer,is_director,transaction_date,transaction_code,shares,price,is_10b5_1,url",
      ticker: `eq.${t}`,
      transaction_code: "in.(S,P)",
      transaction_date: `gte.${daysAgo(183)}`,
      order: "transaction_date.desc",
      limit: "200",
    }),
  ]);
  const [jobs, layoffs, board] = await Promise.all([
    query<JobCount>("job_counts", { select: "day,total_jobs,clinical_jobs", ticker: `eq.${t}`, order: "day.desc", limit: "60" }),
    query<LayoffNotice>("layoff_notices", {
      select: "state,company_name,notice_date,employees,location",
      ticker: `eq.${t}`,
      order: "notice_date.desc.nullslast",
      limit: "20",
    }),
    query<{ provider: string }>("job_boards", { select: "provider", ticker: `eq.${t}`, confirmed: "eq.true" }),
  ]);
  return {
    company: company.rows[0] ?? null,
    trials: trials.rows,
    filings: filings.rows,
    trades: trades.rows,
    jobs: jobs.rows,
    layoffs: layoffs.rows,
    jobBoard: board.rows[0]?.provider ?? null,
  };
}

// ---------- Track record ----------
export type BacktestSummary = {
  signal_type: string;
  cases: number;
  bad: number;
  fine: number;
  typical_bad_move: number | null;
  typical_fine_move: number | null;
  bad_moves: number | null;
  fine_moves: number | null;
  baseline_bad_share: number | null;
  confidence: "low" | "medium" | "high";
  computed_at: string;
  extra: { plain?: string[]; reasons?: Record<string, number> } | null;
};
export type BacktestCase = {
  signal_type: string;
  ticker: string;
  signal_day: string;
  outcome: "bad" | "fine" | "unknown";
  news_day: string | null;
  move_pct: number | null;
  detail: string | null;
};
export type LiveAlert = {
  id: number;
  nct_id: string | null;
  ticker: string | null;
  detected_at: string;
  kind: string;
  signal_type: string | null;
  headline: string;
  baseline: boolean;
};

export async function getTrackRecord() {
  "use cache";
  cacheLife("hours");
  const [summaries, cases, alerts, companies] = await Promise.all([
    query<BacktestSummary>("backtest_summary", { select: "*" }),
    queryAll<BacktestCase>("backtest_cases", {
      select: "signal_type,ticker,signal_day,outcome,news_day,move_pct,detail",
      signal_type: "in.(layoffs,key_exec_departure,repeat_exec_departure,trial_stopped)",
      order: "signal_day.desc",
    }),
    query<LiveAlert>(
      "alerts",
      {
        select: "id,nct_id,ticker,detected_at,kind,signal_type,headline,baseline",
        kind: "eq.critical",
        order: "detected_at.desc",
        limit: "15",
      },
      true,
    ),
    queryAll<{ ticker: string; name: string }>("companies", { select: "ticker,name" }),
  ]);
  return {
    summaries: summaries.rows,
    cases,
    alerts: alerts.rows,
    alertCount: alerts.total || alerts.rows.length,
    names: Object.fromEntries(companies.map((c) => [c.ticker, c.name])),
  };
}

// ---------- Upcoming calendar ----------
export type UpcomingEvent = {
  id: number;
  kind: "fda_decision" | "fda_meeting" | "results_due";
  ticker: string;
  nct_id: string | null;
  event_date: string;
  date_precision: "day" | "month";
  title: string | null;
  quote: string | null;
  source_url: string | null;
  source_form: string | null;
  filed_at: string | null;
  updated_at: string;
  trials: { score: number; score_label: ScoreLabel } | null;
  companies: { name: string } | null;
};

export async function getUpcoming() {
  "use cache";
  cacheLife("hours");
  try {
    return await queryAll<UpcomingEvent>("upcoming_events", {
      select: "*,trials(score,score_label),companies(name)",
      order: "event_date,ticker",
    });
  } catch {
    return []; // table not created yet (migration 010): show an empty calendar rather than break the build
  }
}
