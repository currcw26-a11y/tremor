// Builds the facts Claude is allowed to use for one trial or company. Every number here comes
// from Tremor's database; Claude may only reword these facts, never add new numbers.
import { select } from "./supabase-admin";

type Reason = { label: string; points: number; occurred: string };

const STATUS: Record<string, string> = {
  RECRUITING: "signing up patients",
  NOT_YET_RECRUITING: "not started yet",
  ACTIVE_NOT_RECRUITING: "running, no longer signing up patients",
  COMPLETED: "finished",
  SUSPENDED: "paused",
  TERMINATED: "stopped early",
  WITHDRAWN: "cancelled before it started",
  ENROLLING_BY_INVITATION: "signing up invited patients",
};

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
/** "2026-11-06" -> "Nov 6, 2026", "2027-06" -> "Jun 2027" */
function niceDate(d: unknown) {
  if (!d) return "unknown";
  const [y, m, day] = String(d).slice(0, 10).split("-");
  if (!m) return y;
  return day ? `${MONTHS[+m - 1]} ${+day}, ${y}` : `${MONTHS[+m - 1]} ${y}`;
}

// Plain-English names for the kinds of changes Tremor spots
const CHANGE_WORDS: Record<string, string> = {
  primary_outcome_changed: "the main goal (what counts as success) was changed",
  primary_outcome_added: "a new main goal was added",
  primary_outcome_reworded: "the main goal was reworded",
  enrollment_cut: "the number of patients was cut",
  enrollment_small_cut: "the number of patients was lowered slightly",
  enrollment_increased: "the number of patients was raised",
  date_delayed: "a key date was pushed back",
  date_small_change: "a date moved slightly",
  date_moved_earlier: "a date moved earlier",
  trial_stopped: "the trial was stopped",
  status_changed: "the trial's status changed (usually normal progress)",
  results_posted: "results were posted",
  interventions_changed: "the drugs in the trial changed",
  phase_changed: "the trial's phase changed",
};

function money(n: number | null | undefined) {
  if (n == null) return "unknown";
  const a = Math.abs(n);
  if (a >= 1e9) return `$${(a / 1e9).toFixed(1)} billion`;
  if (a >= 1e6) return `$${(a / 1e6).toFixed(1)} million`;
  return `$${Math.round(a / 1e3)} thousand`;
}

async function companyFacts(ticker: string): Promise<string[]> {
  const [c] = await select<Record<string, never>>("companies", { select: "*", ticker: `eq.${ticker}` });
  if (!c) return [];
  const lines = [`Company: ${c["name"]} (stock ticker ${ticker})`];
  if (c["finances_as_of"]) {
    lines.push(`Cash and short-term investments: ${money(c["cash_usd"])} as of ${niceDate(c["finances_as_of"])}`);
    if (c["runway_months"] != null) {
      lines.push(`Spending on running the business: about ${money(c["monthly_burn_usd"])} a month`);
      lines.push(`Money left at that rate: about ${Math.round(c["runway_months"])} months`);
    } else if (c["monthly_burn_usd"] != null) {
      lines.push("Not burning cash: it brings in more cash than it spends running the business");
    }
  }
  return lines;
}

export async function trialContext(nct: string): Promise<{ text: string; ticker: string } | null> {
  const [t] = await select<Record<string, never>>("trials", {
    select: "nct_id,title,sponsor_name,ticker,phases,overall_status,conditions,interventions,primary_outcomes,enrollment,enrollment_type,start_date,primary_completion_date,completion_date,results_first_posted,score,score_label,score_breakdown",
    nct_id: `eq.${nct}`,
  });
  if (!t) return null;
  const changes = await select<{ change_type: string; detected_at: string; explanation: string | null; old_value: unknown; new_value: unknown }>(
    "trial_changes",
    { select: "change_type,detected_at,explanation,old_value,new_value", nct_id: `eq.${nct}`, is_paperwork: "eq.false", order: "detected_at.desc", limit: "8" },
  );
  const reasons = (t["score_breakdown"] as Reason[] | null) ?? [];
  const lines = [
    ...(await companyFacts(t["ticker"])),
    `Trial ID: ${nct}`,
    `Trial: ${t["title"]}`,
    `Stage: Phase ${((t["phases"] as string[]) ?? []).map((p) => p.replace("PHASE", "")).join("/") || "not listed"}`,
    `Cancer type: ${((t["conditions"] as string[]) ?? []).join(", ")}`,
    `Drugs: ${((t["interventions"] as string[]) ?? []).join(", ")}`,
    `Status: ${STATUS[t["overall_status"]] ?? t["overall_status"]}`,
    `Patients: ${t["enrollment"]} (${t["enrollment_type"] === "ACTUAL" ? "final count" : "planned"})`,
    `Main goals (what counts as success): ${((t["primary_outcomes"] as { measure: string }[]) ?? []).map((o) => o.measure).join("; ")}`,
    `Started: ${niceDate(t["start_date"])}; main results expected: ${niceDate(t["primary_completion_date"])}; fully finished: ${niceDate(t["completion_date"])}`,
    `Results posted: ${t["results_first_posted"] ? niceDate(t["results_first_posted"]) : "not yet"}`,
    `Tremor worry score: ${t["score"]} out of 100 (${t["score_label"]})`,
    `Reasons behind the score: ${reasons.length ? reasons.map((r) => `${r.label} (+${Math.round(r.points)})`).join("; ") : "none, no warning signs right now"}`,
    ...changes.map((c) => `Change spotted on ${niceDate(c.detected_at)}: ${CHANGE_WORDS[c.change_type] ?? c.change_type.replaceAll("_", " ")}${c.explanation ? `. Explanation: ${c.explanation}` : ""}`),
  ];
  return { text: lines.join("\n"), ticker: t["ticker"] };
}

export async function companyOnlyContext(ticker: string): Promise<string | null> {
  const base = await companyFacts(ticker);
  if (!base.length) return null;
  const trials = await select<{ nct_id: string; title: string; score: number; score_label: string; overall_status: string; score_breakdown: Reason[] | null }>(
    "trials",
    { select: "nct_id,title,score,score_label,overall_status,score_breakdown", ticker: `eq.${ticker}`, tracked: "eq.true", order: "score.desc", limit: "15" },
  );
  const companyWide = new Set<string>();
  for (const t of trials) for (const r of t.score_breakdown ?? []) if (/insider|executive|layoffs/i.test(r.label)) companyWide.add(r.label);
  const lines = [
    ...base,
    `Tremor tracks ${trials.length} of its cancer trials${trials.length === 15 ? " (showing the 15 with the highest worry scores)" : ""}:`,
    ...trials.map((t) => `- ${t.title} (${t.nct_id}): worry score ${t.score} (${t.score_label}), ${STATUS[t.overall_status] ?? t.overall_status}`),
    `Company-wide warning signs: ${companyWide.size ? [...companyWide].join("; ") : "none right now"}`,
  ];
  return lines.join("\n");
}
