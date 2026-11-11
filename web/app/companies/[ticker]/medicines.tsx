import type { ApprovedMedicine } from "@/lib/db";
import { Empty } from "../../components";

const NOTE =
  "From the FDA's drug database (Drugs@FDA), under the names the FDA uses for this company. It leaves out cell and gene therapies and vaccines, which a different part of the FDA approves.";

/** One row per medicine: versions of the same brand (like an under-the-skin form) are folded together. */
function byBrand(meds: ApprovedMedicine[]) {
  const seen = new Map<string, ApprovedMedicine & { firstYear: string }>();
  for (const m of [...meds].sort((a, b) => a.approved_on.localeCompare(b.approved_on))) {
    const key = m.brand_name.split(",")[0].split(" ")[0].toLowerCase();
    const prev = seen.get(key);
    seen.set(key, {
      ...m,
      brand_name: prev?.brand_name ?? m.brand_name.split(",")[0],
      firstYear: prev?.firstYear ?? m.approved_on.slice(0, 4),
      still_sold: m.still_sold || !!prev?.still_sold,
    });
  }
  return [...seen.values()].sort((a, b) => b.firstYear.localeCompare(a.firstYear));
}

function Row({ m }: { m: ApprovedMedicine & { firstYear: string } }) {
  return (
    <li className="flex items-baseline justify-between gap-3 py-2.5 text-sm">
      <span className="min-w-0">
        <span className="font-medium">{m.brand_name}</span>
        {m.ingredient && <span className="block truncate text-xs text-muted">{m.ingredient}</span>}
      </span>
      <span className="shrink-0 font-mono text-xs text-muted">{m.firstYear}</span>
    </li>
  );
}

/** Medicines the company already sells. A company with none depends entirely on drugs still in testing. */
export function Medicines({ medicines }: { medicines: ApprovedMedicine[] }) {
  const sold = byBrand(medicines).filter((m) => m.still_sold);
  if (!sold.length)
    return (
      <>
        <Empty>None found in the FDA&apos;s drug database.</Empty>
        <p className="mt-2 text-xs text-muted">{NOTE}</p>
      </>
    );
  const shown = sold.slice(0, 6);
  const rest = sold.slice(6);
  return (
    <div>
      <p>
        <span className="font-serif text-4xl font-medium tabular-nums">{sold.length}</span>{" "}
        <span className="font-medium">
          {sold.length === 1 ? "medicine" : "medicines"} on the market
        </span>
        <span className="block text-sm text-muted">
          {sold.length === 1 ? "With its year of approval" : "Newest first, with year of approval"}
        </span>
      </p>
      <ul className="mt-3 divide-y divide-line border-y border-line">
        {shown.map((m) => (
          <Row key={m.application_number} m={m} />
        ))}
      </ul>
      {rest.length > 0 && (
        <details className="group/med">
          <summary className="cursor-pointer list-none py-2 text-sm font-medium underline-offset-4 hover:underline">
            <span className="mr-1.5 inline-block text-muted transition-transform group-open/med:rotate-90">›</span>
            {rest.length} more
          </summary>
          <ul className="divide-y divide-line border-b border-line">
            {rest.map((m) => (
              <Row key={m.application_number} m={m} />
            ))}
          </ul>
        </details>
      )}
      <p className="mt-3 text-xs text-muted">
        A company that already sells medicines has money coming in, so one trial matters less than at a company with
        nothing on the market yet. {NOTE}
      </p>
    </div>
  );
}
