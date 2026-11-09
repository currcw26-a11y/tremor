"use client";
import { useEffect, useState } from "react";
import { signIn, supabase, useUser } from "@/lib/supabase-browser";

type Profile = { email: string; instant_alerts: boolean; daily_digest: boolean; unsubscribed: boolean };

const OPTIONS: { key: keyof Omit<Profile, "email" | "unsubscribed">; title: string; help: string }[] = [
  {
    key: "instant_alerts",
    title: "Instant alerts",
    help: "An email right away when something big happens: a trial stops, its main goal changes, a key executive leaves, or a score jumps. Sent for your watchlist, plus anything huge on any trial.",
  },
  {
    key: "daily_digest",
    title: "Daily digest",
    help: "One email a day with smaller changes on your watchlist, like delays, insider selling, or FDA meetings. Only sent on days with news.",
  },
];

export function Settings() {
  const user = useUser();
  const [profile, setProfile] = useState<Profile | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!user) return;
    supabase()
      .from("profiles")
      .select("email,instant_alerts,daily_digest,unsubscribed")
      .eq("user_id", user.id)
      .maybeSingle()
      .then(({ data }) => setProfile(data as Profile | null));
  }, [user]);

  async function save(changes: Partial<Profile>) {
    if (!user || !profile) return;
    setSaving(true);
    const { error } = await supabase().from("profiles").update(changes).eq("user_id", user.id);
    if (!error) setProfile({ ...profile, ...changes });
    setError(!!error);
    setSaving(false);
  }

  if (user === undefined) return <div className="h-40 animate-pulse rounded-xl bg-line" />;
  if (!user)
    return (
      <div className="rounded-xl border border-line bg-surface p-6 text-center">
        <p className="font-semibold">Sign in to choose your alerts.</p>
        <button onClick={() => signIn("/settings")} className="mt-4 rounded-full bg-foreground px-4 py-2 font-semibold text-background">
          Sign in with Google
        </button>
      </div>
    );
  if (!profile) return <div className="h-40 animate-pulse rounded-xl bg-line" />;

  return (
    <div className="space-y-4">
      <p className="text-muted">
        Emails go to <strong className="text-foreground">{profile.email}</strong>.
      </p>
      {profile.unsubscribed && (
        <div className="rounded-xl border border-shaky bg-shaky/10 p-4">
          <p className="font-semibold">All emails are off.</p>
          <button onClick={() => save({ unsubscribed: false })} disabled={saving} className="mt-2 rounded-full bg-foreground px-4 py-1.5 text-sm font-semibold text-background">
            Turn emails back on
          </button>
        </div>
      )}
      <ul className="divide-y divide-line overflow-hidden rounded-xl border border-line bg-surface">
        {OPTIONS.map((o) => (
          <li key={o.key} className="flex items-start justify-between gap-4 p-4">
            <span>
              <span className="block font-semibold">{o.title}</span>
              <span className="mt-1 block text-sm text-muted">{o.help}</span>
            </span>
            <button
              role="switch"
              aria-checked={profile[o.key]}
              aria-label={o.title}
              disabled={saving || profile.unsubscribed}
              onClick={() => save({ [o.key]: !profile[o.key] })}
              className={`relative mt-1 h-7 w-12 shrink-0 rounded-full transition disabled:opacity-50 ${profile[o.key] ? "bg-foreground" : "bg-line"}`}
            >
              <span className={`absolute top-1 h-5 w-5 rounded-full bg-surface transition ${profile[o.key] ? "left-6" : "left-1"}`} />
              <span className="sr-only">{profile[o.key] ? "On" : "Off"}</span>
            </button>
          </li>
        ))}
      </ul>
      {!profile.unsubscribed && (
        <button onClick={() => save({ unsubscribed: true })} disabled={saving} className="text-sm text-muted underline">
          Pause all emails
        </button>
      )}
      {error && <p role="alert" className="text-sm text-tremor">Couldn&apos;t save that. Please try again.</p>}
      <p className="text-sm text-muted">Every email also has a one-click unsubscribe link. Tremor never tells anyone to buy or sell.</p>
    </div>
  );
}
