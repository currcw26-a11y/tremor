import type { Metadata } from "next";
import Link from "next/link";
import { GLOSSARY } from "@/lib/glossary";

export const metadata: Metadata = {
  title: "Words to know",
  alternates: { canonical: "/glossary" },
  description:
    "Plain-English definitions of the drug-trial and stock-market words used on Tremor.",
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
    <div className="grid grid-cols-1 gap-12 lg:grid-cols-12">
      <article className="rise min-w-0 lg:col-span-9">
        <h1 className="font-serif text-4xl font-medium tracking-tight sm:text-5xl">
          Words to know
        </h1>
        <p className="mt-4 max-w-2xl text-ink-2">
          Short, plain-English meanings. Across the site, words with a dotted
          underline open these when you tap them. New to all this? Start with{" "}
          <Link
            href="/learn"
            className="font-semibold text-foreground underline"
          >
            how biotech stocks move
          </Link>
          .
        </p>
        {GROUPS.map(([group, title]) => (
          <section key={group} id={`g-${group}`} className="mt-14 scroll-mt-24">
            <h2 className="border-t border-foreground pt-3 font-serif text-2xl font-medium tracking-tight">
              {title}
            </h2>
            <dl className="mt-2 grid grid-cols-1 gap-x-12 md:grid-cols-2">
              {entries
                .filter(([, g]) => g.group === group)
                .map(([id, g]) => (
                  <div
                    key={id}
                    id={id}
                    className="scroll-mt-24 border-b border-line py-4 target:bg-surface"
                  >
                    <dt className="font-medium">{g.term}</dt>
                    <dd className="mt-1 text-sm leading-relaxed text-ink-2">
                      {g.text}
                    </dd>
                  </div>
                ))}
            </dl>
          </section>
        ))}
      </article>
      <aside className="hidden lg:col-span-3 lg:block">
        <nav className="sticky top-24" aria-label="Sections">
          <p className="border-t border-foreground pt-3 text-sm font-semibold text-foreground">
            Sections
          </p>
          <ul className="mt-3 space-y-2.5 text-sm">
            {GROUPS.map(([group, title]) => (
              <li key={group}>
                <a
                  href={`#g-${group}`}
                  className="link-grow text-ink-2 hover:text-foreground"
                >
                  {title}
                </a>
              </li>
            ))}
          </ul>
        </nav>
      </aside>
    </div>
  );
}
