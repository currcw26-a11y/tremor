// Turning database codes into plain English for people who've never bought a stock.
import type { Change } from "./db";

export const STATUS: Record<string, { label: string; tone: "good" | "neutral" | "bad" }> = {
  RECRUITING: { label: "Signing up patients", tone: "good" },
  NOT_YET_RECRUITING: { label: "Not started yet", tone: "neutral" },
  ENROLLING_BY_INVITATION: { label: "Invite-only sign-up", tone: "good" },
  ACTIVE_NOT_RECRUITING: { label: "Running, no new patients", tone: "neutral" },
  COMPLETED: { label: "Finished", tone: "neutral" },
  SUSPENDED: { label: "Paused", tone: "bad" },
  TERMINATED: { label: "Stopped early", tone: "bad" },
  WITHDRAWN: { label: "Cancelled before starting", tone: "bad" },
};

export function statusLabel(code: string) {
  return STATUS[code]?.label ?? code.toLowerCase().replaceAll("_", " ");
}

export function phaseLabel(phases: string[] = []) {
  const nums = phases.map((p) => p.replace("PHASE", "")).filter(Boolean);
  return nums.length ? `Phase ${nums.join("/")}` : "Phase not listed";
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/** "2027-06" -> "Jun 2027", "2027-06-15" -> "Jun 15, 2027" */
export function niceDate(d: string | null | undefined) {
  if (!d) return "unknown";
  const [y, m, day] = d.slice(0, 10).split("-");
  if (!m) return y;
  return day ? `${MONTHS[+m - 1]} ${+day}, ${y}` : `${MONTHS[+m - 1]} ${y}`;
}

export function timeAgo(iso: string | null) {
  if (!iso) return "never";
  const mins = Math.round((Date.now() - new Date(iso).getTime()) / 60000);
  if (mins < 60) return `${mins} minute${mins === 1 ? "" : "s"} ago`;
  const hours = Math.round(mins / 60);
  if (hours < 48) return `${hours} hour${hours === 1 ? "" : "s"} ago`;
  return `${Math.round(hours / 24)} days ago`;
}

const n = (v: unknown) => (typeof v === "number" ? v.toLocaleString() : String(v ?? "?"));

function monthsText(months: unknown) {
  const m = Math.abs(Number(months));
  return m >= 1.5 ? `about ${Math.round(m)} months` : "a few weeks";
}

/** One plain-English sentence per change. Severity drives the color. */
export function describeChange(c: Change): { text: string; severity: "high" | "medium" | "low" } {
  const d = c.details ?? {};
  const dateName = c.field === "primary_completion_date" ? "main results date" : "final finish date";
  switch (c.change_type) {
    case "primary_outcome_changed":
      return { severity: "high", text: "Changed the trial's main goal (what counts as success)." };
    case "primary_outcome_added":
      return { severity: "medium", text: "Added a new main goal to the trial." };
    case "primary_outcome_reworded":
      return { severity: "low", text: "Reworded the trial's main goal or its timing." };
    case "enrollment_cut":
      return { severity: "high", text: `Cut the number of patients from ${n(c.old_value)} to ${n(c.new_value)} (${Math.round(Number(d.percent_cut))}% fewer).` };
    case "enrollment_small_cut":
      return { severity: "low", text: `Slightly lowered the number of patients, from ${n(c.old_value)} to ${n(c.new_value)}.` };
    case "enrollment_increased":
      return { severity: "low", text: `Raised the number of patients from ${n(c.old_value)} to ${n(c.new_value)}.` };
    case "date_delayed":
      return { severity: "high", text: `Pushed back the ${dateName} by ${monthsText(d.months)}: ${niceDate(String(c.old_value))} → ${niceDate(String(c.new_value))}.` };
    case "date_small_change":
      return { severity: "low", text: `Moved the ${dateName} slightly later: ${niceDate(String(c.old_value))} → ${niceDate(String(c.new_value))}.` };
    case "date_moved_earlier":
      return { severity: "low", text: `Moved the ${dateName} earlier: ${niceDate(String(c.old_value))} → ${niceDate(String(c.new_value))}.` };
    case "trial_stopped":
      return { severity: "high", text: `The trial was ${statusLabel(String(c.new_value)).toLowerCase()}.` };
    case "status_changed":
      return { severity: "low", text: `Status changed: ${statusLabel(String(c.old_value))} → ${statusLabel(String(c.new_value))}. Usually normal progress.` };
    case "results_posted":
      return { severity: "medium", text: "Posted results for the first time." };
    case "interventions_changed":
      return { severity: "medium", text: "Changed which drugs are in the trial." };
    case "phase_changed":
      return { severity: "medium", text: "Changed the trial's phase." };
    case "paperwork":
      return { severity: "low", text: "Paperwork edit (contacts, locations, wording). Usually harmless." };
    default:
      return { severity: "low", text: c.change_type.replaceAll("_", " ") };
  }
}

const KEEP_UPPER = new Set(["AG", "SA", "NV", "PLC", "AB", "AS", "SE", "BV", "LLC", "II", "III", "US", "USA"]);
/** "VERTEX PHARMACEUTICALS INC / MA" -> "Vertex Pharmaceuticals"; mixed-case names keep their own style. */
export function companyName(name: string | null | undefined, ticker = "") {
  let n = (name ?? ticker).replace(/\s*\/\s*[a-z]{2}\s*\/?\s*$/i, "").trim();
  if (n === n.toUpperCase()) {
    n = n
      .toLowerCase()
      .split(/\s+/)
      .map((w) => (KEEP_UPPER.has(w.toUpperCase()) ? w.toUpperCase() : w.charAt(0).toUpperCase() + w.slice(1)))
      .join(" ");
  }
  return n.replace(/,?\s+(Inc|Corp|Corporation|Co|Ltd|Limited)\.?$/i, "").trim() || ticker;
}

/** AI summaries sometimes copy dates the way records store them ("2026-11-10", "2026-11"). Show them the normal way. */
export function tidyDates(text: string) {
  const M = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
  return text
    .replace(/\b(20\d\d)-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])\b/g, (_, y, m, d) => `${M[+m - 1]} ${+d}, ${y}`)
    .replace(/\b(20\d\d)-(0[1-9]|1[0-2])\b/g, (_, y, m) => `${M[+m - 1]} ${y}`);
}
