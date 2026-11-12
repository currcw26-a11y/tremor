// Small shared layout pieces for the redesigned pages.
import Link from "next/link";

/** A section title with a thin rule above it (editorial style), and an optional quiet link on the right. */
export function SectionHead({
  title,
  href,
  linkText,
  as: Tag = "h2",
  children,
}: {
  title: React.ReactNode;
  href?: string;
  linkText?: string;
  as?: "h2" | "h3";
  children?: React.ReactNode;
}) {
  return (
    <div className="flex items-baseline justify-between gap-4 border-t border-foreground pt-3">
      <Tag className={`font-serif font-medium tracking-tight ${Tag === "h2" ? "text-2xl" : "text-xl"}`}>{title}</Tag>
      {href && (
        <Link href={href} className="tap shrink-0 text-sm text-ink-2 hover:text-foreground">
          <span className="link-grow">{linkText}</span> <span className="nudge">→</span>
        </Link>
      )}
      {children}
    </div>
  );
}

/** Label/value rows separated by thin lines, for facts in a side column. */
export function Facts({ rows }: { rows: [React.ReactNode, React.ReactNode][] }) {
  return (
    <dl className="divide-y divide-line border-y border-line text-sm">
      {rows.map(([k, v], i) => (
        <div key={i} className="flex items-baseline justify-between gap-4 py-2.5">
          <dt className="text-muted">{k}</dt>
          <dd className="text-right font-medium">{v}</dd>
        </div>
      ))}
    </dl>
  );
}
