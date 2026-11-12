// "See exactly what changed": a before/after view of one trial-record edit.
import type { Change } from "@/lib/db";
import { pairOutcomes, SECTION_WORDS, wordDiff, type Outcome } from "@/lib/diff";
import { niceDate, statusLabel } from "@/lib/words";

function Diff({ before, after }: { before?: string; after?: string }) {
  if ((before ?? "") === (after ?? "")) return <span>{after}</span>;
  return (
    <span>
      {wordDiff(before ?? "", after ?? "").map((p, i, all) =>
        p.kind === "same" ? (
          <span key={i}>{p.text}</span>
        ) : p.kind === "removed" ? (
          <span key={i}>
            <del className="rounded-sm bg-tremor/10 text-tremor decoration-tremor/70">{p.text.trim()}</del>
            {/* keep removed and added words apart: "DLT adverse", not "DLTadverse" */}
            {all[i + 1]?.kind === "added" || /\s$/.test(p.text) ? " " : ""}
          </span>
        ) : (
          <span key={i}>
            <ins className="rounded-sm bg-calm/10 text-calm decoration-calm/70">{p.text.trim()}</ins>
            {/\s$/.test(p.text) ? " " : ""}
          </span>
        ),
      )}
    </span>
  );
}

function Legend() {
  return (
    <p className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted">
      <span>
        <del className="rounded-sm bg-tremor/10 text-tremor">crossed out</del> = removed
      </span>
      <span>
        <ins className="rounded-sm bg-calm/10 text-calm">underlined</ins> = added
      </span>
    </p>
  );
}

function OutcomeFields({ before, after }: { before?: Outcome; after?: Outcome }) {
  const rows: [string, keyof Outcome][] = [
    ["Goal", "measure"],
    ["Measured over", "timeFrame"],
    ["Details", "description"],
  ];
  return (
    <dl className="space-y-1.5">
      {rows.map(([label, key]) =>
        before?.[key] || after?.[key] ? (
          <div key={key}>
            <dt className="text-xs font-semibold text-muted">{label}</dt>
            <dd className="text-sm leading-relaxed">
              <Diff before={before?.[key]} after={after?.[key]} />
            </dd>
          </div>
        ) : null,
      )}
    </dl>
  );
}

function MainGoals({ c }: { c: Change }) {
  const pairs = pairOutcomes((c.old_value as Outcome[]) ?? [], (c.new_value as Outcome[]) ?? []);
  const label = { changed: "Reworded", removed: "Removed", added: "Added", same: "Unchanged" } as const;
  const shown = pairs.filter((p) => p.kind !== "same");
  const unchanged = pairs.length - shown.length;
  return (
    <div className="space-y-3">
      <Legend />
      {shown.map((p, i) => (
        <div key={i} className="rounded-lg border border-line bg-background p-3">
          <p
            className={`mb-1.5 text-xs font-bold uppercase tracking-wide ${
              p.kind === "removed" ? "text-tremor" : p.kind === "added" ? "text-calm" : "text-muted"
            }`}
          >
            {label[p.kind]} main goal
          </p>
          <OutcomeFields
            before={p.kind === "added" ? undefined : p.before}
            after={p.kind === "removed" ? undefined : p.after}
          />
        </div>
      ))}
      {unchanged > 0 && (
        <p className="text-xs text-muted">
          {unchanged} other main goal{unchanged === 1 ? " was" : "s were"} not changed.
        </p>
      )}
    </div>
  );
}

function BeforeAfter({ before, after, note }: { before: string; after: string; note?: string }) {
  return (
    <div>
      <div className="flex flex-wrap items-center gap-2 text-sm">
        <span className="rounded-lg border border-line bg-background px-2.5 py-1.5">
          <span className="block text-[11px] text-muted">Before</span>
          <del className="font-semibold text-muted decoration-1">{before}</del>
        </span>
        <span aria-hidden className="text-muted">→</span>
        <span className="rounded-lg border border-line bg-background px-2.5 py-1.5">
          <span className="block text-[11px] text-muted">After</span>
          <span className="font-semibold">{after}</span>
        </span>
      </div>
      {note && <p className="mt-2 text-sm text-muted">{note}</p>}
    </div>
  );
}

const PLANNED = (t: unknown) => (t === "ACTUAL" ? "final count" : "planned");

function Body({ c }: { c: Change }) {
  const d = c.details ?? {};
  switch (c.change_type) {
    case "primary_outcome_changed":
    case "primary_outcome_reworded":
    case "primary_outcome_added":
      return <MainGoals c={c} />;
    case "enrollment_cut":
    case "enrollment_small_cut":
    case "enrollment_increased": {
      const before = Number(c.old_value);
      const after = Number(c.new_value);
      const diff = Math.abs(after - before);
      const toFinal = d.old_type === "ESTIMATED" && d.new_type === "ACTUAL";
      return (
        <BeforeAfter
          before={`${before.toLocaleString()} patients (${PLANNED(d.old_type)})`}
          after={`${after.toLocaleString()} patients (${PLANNED(d.new_type)})`}
          note={
            `${diff.toLocaleString()} ${after < before ? "fewer" : "more"} patients.` +
            (toFinal
              ? " The number switched from a plan to the final count, which usually happens when a trial stops signing up patients. Ending a little below plan is common."
              : "")
          }
        />
      );
    }
    case "date_delayed":
    case "date_small_change":
    case "date_moved_earlier": {
      const m = Math.abs(Number(d.months));
      const which = c.field === "primary_completion_date" ? "Main results date" : "Final finish date";
      return (
        <BeforeAfter
          before={niceDate(String(c.old_value))}
          after={niceDate(String(c.new_value))}
          note={`${which} moved ${c.change_type === "date_moved_earlier" ? "earlier" : "later"} by ${
            m >= 1.5 ? `about ${Math.round(m)} months` : "a few weeks"
          }.`}
        />
      );
    }
    case "trial_stopped":
    case "status_changed":
      return <BeforeAfter before={statusLabel(String(c.old_value))} after={statusLabel(String(c.new_value))} />;
    default: {
      const sections = ((d.sections as string[]) ?? []).map((s) => SECTION_WORDS[s] ?? s);
      return (
        <p className="text-sm">
          {sections.length ? (
            <>
              Edited: <span className="font-semibold">{sections.join(", ")}</span>. Tremor doesn&apos;t save the exact
              wording of these sections, but the official record history shows every version.
            </>
          ) : (
            "The official record history shows every version."
          )}
        </p>
      );
    }
  }
}

// Dates and status changes already say "before → after" in their headline, so they don't get the button
const WORTH_SHOWING = new Set([
  "primary_outcome_changed", "primary_outcome_reworded", "primary_outcome_added",
  "enrollment_cut", "enrollment_small_cut", "enrollment_increased", "paperwork",
]);

export function ChangeDiff({ c }: { c: Change }) {
  if (!WORTH_SHOWING.has(c.change_type)) return null;
  return (
    <details className="mt-2 rounded-lg border border-line px-3 py-2">
      <summary className="cursor-pointer text-sm font-semibold">See exactly what changed</summary>
      <div className="mt-3">
        <Body c={c} />
        <a
          href={`https://clinicaltrials.gov/study/${c.nct_id}?tab=history`}
          target="_blank"
          rel="noreferrer"
          className="tap mt-3 inline-block text-xs underline"
        >
          Every version on ClinicalTrials.gov ↗
        </a>
      </div>
    </details>
  );
}
