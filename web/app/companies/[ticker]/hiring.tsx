import type { JobCount, LayoffNotice } from "@/lib/db";
import { niceDate } from "@/lib/words";
import { Empty } from "../../components";

const BOARD_NAMES: Record<string, string> = { greenhouse: "Greenhouse", lever: "Lever", ashby: "Ashby" };

/** Open jobs today vs. about a month ago. A sharp drop in clinical jobs is a (small) warning sign. */
export function Hiring({ jobs, board }: { jobs: JobCount[]; board: string | null }) {
  if (!board) return <Empty>We haven&apos;t found a public job board for this company.</Empty>;
  if (!jobs.length) return <Empty>Tremor started counting this company&apos;s job postings recently. Check back tomorrow.</Empty>;
  const now = jobs[0];
  const monthAgo = jobs.find((j) => (Date.parse(now.day) - Date.parse(j.day)) / 86_400_000 >= 28);
  return (
    <div>
      <p>
        <span className="font-serif text-4xl font-medium tabular-nums">{now.clinical_jobs}</span>{" "}
        <span className="font-medium">clinical job openings</span>
        <span className="block text-sm text-muted">
          out of {now.total_jobs} total, on {niceDate(now.day)}
        </span>
      </p>
      {monthAgo ? (
        <p className="mt-2 text-sm">
          About a month earlier ({niceDate(monthAgo.day)}): {monthAgo.clinical_jobs} clinical out of {monthAgo.total_jobs}.
        </p>
      ) : (
        <p className="mt-2 text-sm text-muted">Tremor started counting on {niceDate(jobs[jobs.length - 1].day)}, so there&apos;s no month-ago number yet.</p>
      )}
      <p className="mt-3 text-xs text-muted">
        &ldquo;Clinical&rdquo; means jobs running trials, medical, regulatory, and drug-safety work. If a company stops hiring
        for these, it can mean it&apos;s scaling back a trial, though hiring also changes for ordinary reasons. Counted
        daily from the company&apos;s {BOARD_NAMES[board] ?? board} job board.
      </p>
    </div>
  );
}

/** Public layoff (WARN) notices filed with states. */
export function Layoffs({ notices }: { notices: LayoffNotice[] }) {
  return (
    <>
      {notices.length ? (
        <ul className="divide-y divide-line border-y border-line">
          {notices.map((n, i) => (
            <li key={i} className="py-3 text-sm">
              <span className="font-medium">
                {n.employees ? `${n.employees.toLocaleString()} people` : "Layoff notice"} in {n.state}
              </span>
              <span className="block text-xs text-muted">
                {n.notice_date ? `Filed ${niceDate(n.notice_date)}` : "Date not listed"}
                {n.location ? ` · ${n.location}` : ""} · listed as &ldquo;{n.company_name}&rdquo;
              </span>
            </li>
          ))}
        </ul>
      ) : (
        <Empty>No layoff notices found in the last 12 months.</Empty>
      )}
      <p className="mt-2 text-xs text-muted">
        Many states require big employers to file a public notice before layoffs. Tremor checks 10 states daily (not
        Massachusetts, which blocks automated access). Layoffs announced in SEC reports show up under warning signs above.
      </p>
    </>
  );
}
