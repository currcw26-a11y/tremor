import type { Metadata } from "next";
import { getWeeklyIssues } from "@/lib/db";
import { Issue, PastIssues } from "./issue";

export const metadata: Metadata = {
  title: "Tremor Weekly",
  description: "A short weekly roundup of what changed in cancer drug trials, in plain English.",
  alternates: { canonical: "/weekly" },
};

export default async function WeeklyPage() {
  const issues = await getWeeklyIssues();
  if (!issues.length) {
    return (
      <div className="rise max-w-2xl">
        <h1 className="font-serif text-4xl font-medium tracking-tight sm:text-5xl">Tremor Weekly</h1>
        <p className="mt-4 text-ink-2">
          A short roundup of each week: the most important changes, the biggest score moves, and what&apos;s coming up. The
          first issue appears here on the first Monday after a full week of data.
        </p>
      </div>
    );
  }
  return (
    <div className="grid grid-cols-1 gap-12 lg:grid-cols-12">
      <div className="min-w-0 lg:col-span-8">
        <Issue issue={issues[0]} />
      </div>
      <aside className="lg:col-span-3 lg:col-start-10">
        <PastIssues issues={issues} current={issues[0].week_start} />
      </aside>
    </div>
  );
}
