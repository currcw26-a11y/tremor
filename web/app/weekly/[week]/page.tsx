import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Suspense } from "react";
import { getWeeklyIssues } from "@/lib/db";
import { Issue, PastIssues } from "../issue";

export async function generateMetadata({ params }: PageProps<"/weekly/[week]">): Promise<Metadata> {
  const { week } = await params;
  const issue = (await getWeeklyIssues()).find((i) => i.week_start === week);
  if (!issue) return { title: "Tremor Weekly", robots: { index: false } };
  return { title: issue.title, alternates: { canonical: `/weekly/${week}` } };
}

async function One({ params }: { params: PageProps<"/weekly/[week]">["params"] }) {
  const { week } = await params;
  const issues = await getWeeklyIssues();
  const issue = issues.find((i) => i.week_start === week);
  if (!issue) notFound();
  return (
    <div className="grid grid-cols-1 gap-12 lg:grid-cols-12">
      <div className="min-w-0 lg:col-span-8">
        <Issue issue={issue} />
      </div>
      <aside className="lg:col-span-3 lg:col-start-10">
        <PastIssues issues={issues} current={week} />
      </aside>
    </div>
  );
}

export default function WeeklyIssuePage(props: PageProps<"/weekly/[week]">) {
  return (
    <Suspense fallback={<div className="h-96" />}>
      <One params={props.params} />
    </Suspense>
  );
}
