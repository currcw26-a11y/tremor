import type { Metadata } from "next";
import Link from "next/link";
import { GLOSSARY } from "@/lib/glossary";

export const metadata: Metadata = {
  title: "Words to know",
  alternates: { canonical: "/glossary" },
  description: "Plain-English definitions of the drug-trial and stock-market words used on Tremor.",
};

const GROUPS = [
  ["trials", "Drug trials"],
  ["fda", "The FDA"],
  ["stocks", "Stocks and companies"],
  ["tremor", "Tremor itself"],
] as const;

export default function GlossaryPage() {
  const entries = Object.entries(GLOSSARY);
  return (
    <article>
      <h1 className="text-3xl font-black tracking-tight">Words to know</h1>
      <p className="mt-2 text-muted">
        Short, plain-English meanings. Across the site, words with a dotted underline open these when you tap them.
        New to all this? Start with{" "}
        <Link href="/learn" className="font-semibold text-foreground underline">
          how biotech stocks move
        </Link>
        .
      </p>
      {GROUPS.map(([group, title]) => (
        <section key={group} className="mt-8">
          <h2 className="text-xl font-bold">{title}</h2>
          <dl className="mt-3 space-y-2">
            {entries
              .filter(([, g]) => g.group === group)
              .map(([id, g]) => (
                <div key={id} id={id} className="scroll-mt-20 rounded-xl border border-line bg-surface p-4 target:border-foreground">
                  <dt className="font-bold">{g.term}</dt>
                  <dd className="mt-1 text-sm leading-relaxed">{g.text}</dd>
                </div>
              ))}
          </dl>
        </section>
      ))}
    </article>
  );
}
