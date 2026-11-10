// Before/after helpers for trial-record edits. Pure functions (no React), so they're easy to reason about.

export type Piece = { kind: "same" | "removed" | "added"; text: string };

const words = (s: string) => s.split(/(\s+)/).filter((w) => w.length > 0);

/** Word-by-word difference between two texts (longest common subsequence). */
export function wordDiff(before: string, after: string): Piece[] {
  const a = words(before ?? "");
  const b = words(after ?? "");
  // Very long texts: fall back to "all removed, all added" rather than doing a huge table
  if (a.length * b.length > 400_000) {
    return [
      { kind: "removed", text: before },
      { kind: "added", text: after },
    ];
  }
  // Capital letters alone don't count as a change ("Months" -> "months")
  const same = (x: string, y: string) => x.toLowerCase() === y.toLowerCase();
  const dp: number[][] = Array.from({ length: a.length + 1 }, () => new Array(b.length + 1).fill(0));
  for (let i = a.length - 1; i >= 0; i--)
    for (let j = b.length - 1; j >= 0; j--)
      dp[i][j] = same(a[i], b[j]) ? dp[i + 1][j + 1] + 1 : Math.max(dp[i + 1][j], dp[i][j + 1]);
  const out: Piece[] = [];
  const push = (kind: Piece["kind"], text: string) => {
    const last = out[out.length - 1];
    if (last && last.kind === kind) last.text += text;
    else out.push({ kind, text });
  };
  let i = 0;
  let j = 0;
  while (i < a.length && j < b.length) {
    if (same(a[i], b[j])) {
      push("same", b[j]);
      i++;
      j++;
    } else if (dp[i + 1][j] >= dp[i][j + 1]) push("removed", a[i++]);
    else push("added", b[j++]);
  }
  while (i < a.length) push("removed", a[i++]);
  while (j < b.length) push("added", b[j++]);
  return out;
}

export type Outcome = { measure?: string; timeFrame?: string; description?: string };
export type OutcomePair =
  | { kind: "changed"; before: Outcome; after: Outcome }
  | { kind: "same"; before: Outcome; after: Outcome }
  | { kind: "removed"; before: Outcome }
  | { kind: "added"; after: Outcome };

const norm = (s = "") => s.toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
const bag = (o: Outcome) => new Set(norm(`${o.measure ?? ""} ${o.description ?? ""}`).split(" ").filter(Boolean));

function overlap(x: Outcome, y: Outcome) {
  const a = bag(x);
  const b = bag(y);
  let shared = 0;
  for (const w of a) if (b.has(w)) shared++;
  return shared / Math.max(1, Math.min(a.size, b.size));
}

/** Match each old main goal to its closest new one, so rewording shows as a change, not remove + add. */
export function pairOutcomes(before: Outcome[], after: Outcome[]): OutcomePair[] {
  const left = [...(before ?? [])];
  const out: OutcomePair[] = [];
  for (const n of after ?? []) {
    let best = -1;
    let bestScore = 0.4; // need at least this much in common to count as "the same goal, reworded"
    left.forEach((o, i) => {
      const s = overlap(o, n);
      if (s > bestScore) {
        best = i;
        bestScore = s;
      }
    });
    if (best === -1) out.push({ kind: "added", after: n });
    else {
      const [o] = left.splice(best, 1);
      const same =
        norm(o.measure) === norm(n.measure) &&
        norm(o.timeFrame) === norm(n.timeFrame) &&
        norm(o.description) === norm(n.description);
      out.push({ kind: same ? "same" : "changed", before: o, after: n });
    }
  }
  for (const o of left) out.push({ kind: "removed", before: o });
  // Removed and changed first: they matter most
  const order = { removed: 0, changed: 1, added: 2, same: 3 };
  return out.sort((x, y) => order[x.kind] - order[y.kind]);
}

/** Record sections in plain words (ClinicalTrials.gov calls them "modules"). */
export const SECTION_WORDS: Record<string, string> = {
  identificationModule: "trial name and ID numbers",
  statusModule: "status and record dates",
  sponsorCollaboratorsModule: "sponsor and partners",
  oversightModule: "safety oversight",
  descriptionModule: "trial description",
  conditionsModule: "diseases and keywords",
  designModule: "trial design",
  armsInterventionsModule: "treatment groups",
  outcomesModule: "goals other than the main one",
  eligibilityModule: "who can join",
  contactsLocationsModule: "contacts and hospital locations",
  referencesModule: "references and links",
  ipdSharingStatementModule: "data sharing plan",
  largeDocumentModule: "attached documents",
  miscInfoModule: "other information",
};
