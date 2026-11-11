// Renders one Tremor Weekly issue. The text is plain: "## " lines are section titles, "- " lines are bullets.
import Link from "next/link";
import type { WeeklyIssue } from "@/lib/db";
import { niceDate } from "@/lib/words";

function blocks(text: string) {
  const out: ({ kind: "h"; text: string } | { kind: "p"; text: string } | { kind: "ul"; items: string[] })[] = [];
  for (const raw of text.split("\n")) {
    const line = raw.trim();
    if (!line) continue;
    if (line.startsWith("## ")) out.push({ kind: "h", text: line.slice(3) });
    else if (line.startsWith("- ")) {
      const last = out[out.length - 1];
      if (last?.kind === "ul") last.items.push(line.slice(2));
      else out.push({ kind: "ul", items: [line.slice(2)] });
    } else out.push({ kind: "p", text: line });
  }
  return out;
}

export function Issue({ issue }: { issue: WeeklyIssue }) {
  return (
    <article className="rise">
      <p className="font-mono text-xs uppercase tracking-[0.14em] text-muted">
        {niceDate(issue.week_start)} to {niceDate(issue.week_end)}
      </p>
      <h1 className="mt-2 font-serif text-4xl font-medium tracking-tight sm:text-5xl">{issue.title.replace(/^Tremor Weekly: /, "")}</h1>
      <div className="mt-8 max-w-2xl">
        {blocks(issue.body).map((b, i) =>
          b.kind === "h" ? (
            <h2 key={i} className="mt-10 border-t border-foreground pt-3 font-serif text-2xl font-medium tracking-tight first:mt-0">
              {b.text}
            </h2>
          ) : b.kind === "ul" ? (
            <ul key={i} className="mt-3 divide-y divide-line border-y border-line">
              {b.items.map((it, j) => (
                <li key={j} className="py-2.5 text-[17px] leading-relaxed text-ink-2">
                  {it}
                </li>
              ))}
            </ul>
          ) : (
            <p key={i} className="mt-3 text-[17px] leading-relaxed text-ink-2">
              {b.text}
            </p>
          ),
        )}
      </div>
      <p className="mt-10 max-w-2xl border-t border-line pt-4 text-sm text-muted">
        {issue.written_by === "ai"
          ? "Written by AI from the week's facts, which Tremor's code collected. Code checked that every number came from those facts and that there's no buy or sell advice."
          : "This week's roundup was put together by Tremor's code from the week's facts."}{" "}
        Not investment advice. See every change on the{" "}
        <Link href="/changes" className="text-ink-2 underline underline-offset-2">
          Changes
        </Link>{" "}
        page.
      </p>
    </article>
  );
}

export function PastIssues({ issues, current }: { issues: WeeklyIssue[]; current?: string }) {
  return (
    <div className="lg:sticky lg:top-24">
      <p className="border-t border-foreground pt-3 text-xs font-semibold uppercase tracking-[0.14em] text-muted">
        All issues
      </p>
      <ul className="mt-3 space-y-2.5 text-sm">
        {issues.map((i) => (
          <li key={i.week_start}>
            {i.week_start === current ? (
              <span className="font-medium">
                {niceDate(i.week_start)} to {niceDate(i.week_end)}
              </span>
            ) : (
              <Link href={`/weekly/${i.week_start}`} className="link-grow text-ink-2 hover:text-foreground">
                {niceDate(i.week_start)} to {niceDate(i.week_end)}
              </Link>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
