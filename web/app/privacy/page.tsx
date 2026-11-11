import { SITE } from "@/lib/site";
import { LegalPage } from "../legal";

export const metadata = { title: "Privacy policy" };

export default function Privacy() {
  return (
    <LegalPage title="Privacy policy" updated={SITE.updated}>
      <p>
        Tremor is a student project that tracks public information about cancer drug trials. This page explains
        what we collect about you, why, and how to have it deleted.
      </p>

      <h2>What we collect</h2>
      <p>You can use most of Tremor without signing in. If you sign in with Google, we receive and store:</p>
      <ul>
        <li>Your name and email address from your Google account</li>
        <li>The trials and companies you add to your watchlist</li>
        <li>Your email alert settings (once alerts launch)</li>
        <li>If you use the AI chat (once it launches): your questions and a daily count, to enforce the limit</li>
      </ul>
      <p>We don&apos;t ask for or store your password, and we never see your Google account&apos;s other data.</p>

      <h2>How we use it</h2>
      <ul>
        <li>To show you your own watchlist</li>
        <li>To email you alerts about trials and companies you follow, if you turn alerts on</li>
      </ul>
      <p>
        We don&apos;t sell your information, show you ads, or share it with anyone except the services that run
        Tremor (below). Everyone sees the same information about each trial; nothing is tailored to your finances.
      </p>

      <h2>Services that help run Tremor</h2>
      <ul>
        <li>Supabase: stores the database and handles Google sign-in</li>
        <li>Vercel: hosts the website</li>
        <li>Resend: sends alert emails (once alerts launch)</li>
        <li>
          Anthropic (Claude): writes plain-English explanations from public trial data. If you use the AI chat,
          your question is sent to Anthropic to get an answer.
        </li>
        <li>Google: lets you sign in</li>
      </ul>

      <h2>Deleting your data</h2>
      <p>
        You can remove anything from your watchlist at any time. To delete your account and everything linked to
        it, email <a className="underline" href={`mailto:${SITE.contactEmail}`}>{SITE.contactEmail}</a> from the
        address you signed in with, and we&apos;ll delete it within 7 days. Every alert email will include a
        one-click unsubscribe link.
      </p>

      <h2>Changes</h2>
      <p>If this policy changes, we&apos;ll update the date at the top of this page.</p>
    </LegalPage>
  );
}
