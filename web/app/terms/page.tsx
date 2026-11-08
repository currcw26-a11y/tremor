import { SITE } from "@/lib/site";
import { LegalPage } from "../legal";

export const metadata = { title: "Terms of use — Tremor" };

export default function Terms() {
  return (
    <LegalPage title="Terms of use" updated={SITE.updated}>
      <p>By using Tremor, you agree to these terms. They&apos;re short, so please read them.</p>

      <h2>Not investment advice</h2>
      <p>
        Tremor shows changes in public records about drug trials and companies, and what happened in similar past
        cases. It never tells anyone to buy, sell, or hold any stock, and nothing on Tremor is a recommendation or
        a prediction. Worry scores count warning signs; they don&apos;t predict results. Many trial edits are
        harmless paperwork. Do your own research, and talk to a licensed professional before making any investment
        decision.
      </p>

      <h2>Information may be wrong or late</h2>
      <p>
        Tremor gets its data automatically from ClinicalTrials.gov, the SEC, and the Federal Register, and some
        explanations are written by AI from that data. Data can be delayed, incomplete, or wrong, and our matching
        of trials to companies can make mistakes. Always check the original source, which we link to.
      </p>

      <h2>A student project, provided as is</h2>
      <p>
        Tremor is a free student project. It&apos;s provided &ldquo;as is,&rdquo; without any guarantee that it
        works, is accurate, or stays available. We aren&apos;t responsible for any losses from using it.
      </p>

      <h2>Fair use</h2>
      <p>Please don&apos;t try to break the site, overload it, or get around limits like the daily AI chat limit.</p>

      <h2>Contact</h2>
      <p>
        Questions? Email <a className="underline" href={`mailto:${SITE.contactEmail}`}>{SITE.contactEmail}</a>.
      </p>
    </LegalPage>
  );
}
