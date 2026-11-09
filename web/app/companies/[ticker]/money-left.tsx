import type { Company, Filing } from "@/lib/db";
import { niceDate } from "@/lib/words";

const SHARE_SALE_FORMS = new Set(["S-3", "S-1", "424B5"]);

function dollars(n: number) {
  const a = Math.abs(n);
  if (a >= 1e9) return `$${(a / 1e9).toFixed(1)} billion`;
  if (a >= 1e6) return `$${(a / 1e6).toFixed(1)} million`;
  if (a >= 1e3) return `$${Math.round(a / 1e3)} thousand`;
  return `$${Math.round(a)}`;
}

/** "Money left": all numbers come from the company's own SEC reports (computed by the pipeline). */
export function MoneyLeft({ company, filings }: { company: Company; filings: Filing[] }) {
  const c = company;
  if (!c.finances_as_of || c.cash_usd == null) {
    return <p className="text-muted">We couldn&apos;t find recent cash numbers in this company&apos;s SEC reports.</p>;
  }
  const asOf = niceDate(c.finances_as_of);
  const laterShareSale = filings.find((f) => SHARE_SALE_FORMS.has(f.form) && f.filed_at > c.finances_as_of!);
  const months = c.runway_months == null ? null : Math.round(c.runway_months);
  const tone = months == null ? "text-calm" : months < 12 ? "text-tremor" : months < 24 ? "text-shaky" : "text-calm";

  return (
    <div className="rounded-xl border border-line bg-surface p-4">
      {months != null ? (
        <p>
          <span className={`text-4xl font-black tabular-nums ${tone}`}>{months < 1 ? "Under 1" : `About ${months}`}</span>{" "}
          <span className="font-semibold">month{months === 1 ? "" : "s"} of money left</span>
          <span className="block text-sm text-muted">at its recent spending rate</span>
        </p>
      ) : (
        <p className="text-lg font-bold text-calm">Not burning cash</p>
      )}
      <dl className="mt-4 space-y-1 text-sm">
        <div>
          <dt className="inline text-muted">Cash and short-term investments: </dt>
          <dd className="inline font-semibold">{dollars(c.cash_usd)}</dd>
          <span className="text-muted"> (as of {asOf})</span>
        </div>
        {c.monthly_burn_usd != null && (
          <div>
            <dt className="inline text-muted">
              {c.monthly_burn_usd > 0 ? "Spending on running the business: " : "Brings in from running the business: "}
            </dt>
            <dd className="inline font-semibold">about {dollars(c.monthly_burn_usd)} a month</dd>
            {c.burn_period_months && (
              <span className="text-muted"> (average over the {c.burn_period_months} months up to {asOf})</span>
            )}
          </div>
        )}
      </dl>
      {months != null && months < 18 && (
        <p className="mt-3 text-sm">
          Companies running low on money often raise more by creating and issuing new shares, which usually makes each
          existing share worth less.
        </p>
      )}
      {laterShareSale && (
        <p className="mt-3 rounded-lg bg-shaky/10 p-2 text-sm">
          Since {asOf}, the company has filed paperwork to issue new shares ({laterShareSale.form} on{" "}
          {niceDate(laterShareSale.filed_at)}), so it may have more cash now.
        </p>
      )}
      <p className="mt-3 text-xs text-muted">
        Money left = cash ÷ monthly spending. It doesn&apos;t count money the company might raise or earn later, and
        spending can change. Numbers come from the company&apos;s {c.finances_form ?? "SEC"} report.
      </p>
    </div>
  );
}
