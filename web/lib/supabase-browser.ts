// The Supabase connection used in the visitor's browser, for sign-in and watchlists.
// Uses the public "publishable" key; database security rules decide what each person can see.
import { createBrowserClient } from "@supabase/ssr";
import type { SupabaseClient, User } from "@supabase/supabase-js";
import { useEffect, useState } from "react";

let client: SupabaseClient | null = null;

export function supabase() {
  client ??= createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!.trim(),
    process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY!.trim(),
  );
  return client;
}

/** Sends the visitor to Google, then back to `returnTo` on this site. */
export function signIn(returnTo: string = window.location.pathname + window.location.search) {
  const redirectTo = `${window.location.origin}/auth/callback?next=${encodeURIComponent(returnTo)}`;
  return supabase().auth.signInWithOAuth({ provider: "google", options: { redirectTo } });
}

/** The signed-in user (or null). `undefined` while still checking. Stays signed in across visits. */
export function useUser() {
  const [user, setUser] = useState<User | null | undefined>(undefined);
  useEffect(() => {
    const sb = supabase();
    sb.auth.getUser().then(({ data }) => setUser(data.user ?? null));
    const { data } = sb.auth.onAuthStateChange((_event, session) => setUser(session?.user ?? null));
    return () => data.subscription.unsubscribe();
  }, []);
  return user;
}
