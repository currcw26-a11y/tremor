import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import { getRecentChanges } from "@/lib/db";
import { ChangeRow, Empty } from "../components";

export const metadata: Metadata = {
  title: "Latest changes",
  description: "Every important edit Tremor has spotted in cancer drug trial records, newest first, explained in plain English.",
  alternates: { canonical: "/changes" },
};

async function Feed({ searchParams }: { searchParams: PageProps<"/changes">["searchParams"] }) {
  const showMinor = (await searchParams).minor === "1";
  const changes = await getRecentChanges(50, showMinor);
  return (
    <>
      <p className="text-sm text-muted">
        {showMinor ? "Showing routine edits too. " : "Routine edits, like a trial starting to sign up patients, are hidden. "}
        <Link
          href={showMinor ? "/changes" : "/changes?minor=1"}
          scroll={false}
          className="text-ink-2 underline underline-offset-2 hover:text-foreground"
        >
          {showMinor ? "Hide them" : "Show them"}
        </Link>
      </p>
      {changes.length ? (
        <ul className="mt-2 border-t border-line">
          {changes.map((c) => (
            <ChangeRow key={c.id} c={c} />
          ))}
        </ul>
      ) : (
        <div className="mt-4">
          <Empty>No important changes spotted yet. Tremor checks every trial every 4 hours.</Empty>
        </div>
      )}
    </>
  );
}

const DOTS = [
  ["bg-tremor", "Important", "The main goal changed, patients were cut, a date slipped by months, or the trial stopped."],
  ["bg-shaky", "Worth noting", "New results, a new main goal, or a change to which drugs are tested."],
  ["bg-line", "Routine", "Small date moves and status updates. Usually normal progress."],
] as const;

export default function ChangesPage(props: PageProps<"/changes">) {
  return (
    <div className="grid grid-cols-1 gap-12 lg:grid-cols-12">
      <div className="rise min-w-0 lg:col-span-8">
        <h1 className="font-serif text-4xl font-medium tracking-tight sm:text-5xl">Latest changes</h1>
        <p className="mt-4 max-w-xl text-ink-2">
          Edits Tremor spotted in the official records of the cancer trials it watches, newest first.
        </p>
        <div className="mt-8">
          <Suspense fallback={<div className="h-96" />}>
            <Feed searchParams={props.searchParams} />
          </Suspense>
        </div>
      </div>
      <aside className="rise rise-2 lg:col-span-4">
        <div className="lg:sticky lg:top-24">
          <p className="border-t border-foreground pt-3 text-sm font-semibold text-foreground">
            What the dots mean
          </p>
          <ul className="mt-3 space-y-4 text-sm">
            {DOTS.map(([dot, title, text]) => (
              <li key={title} className="flex gap-3">
                <span className={`mt-[6px] h-2 w-2 shrink-0 rounded-full ${dot}`} aria-hidden />
                <span>
                  <span className="font-medium">{title}.</span> <span className="text-ink-2">{text}</span>
                </span>
              </li>
            ))}
          </ul>
          <p className="mt-6 text-sm text-muted">
            Many edits turn out to be harmless paperwork. Each change links to its trial, where you can see exactly what
            changed.
          </p>
        </div>
      </aside>
    </div>
  );
}
