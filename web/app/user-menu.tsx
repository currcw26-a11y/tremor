"use client";
import Link from "next/link";
import { signIn, supabase, useUser } from "@/lib/supabase-browser";

export function UserMenu() {
  const user = useUser();
  if (user === undefined) return <span className="w-16" aria-hidden />;
  if (!user)
    return (
      <button onClick={() => signIn()} className="rounded-full bg-foreground px-3 py-1 text-sm font-semibold text-background">
        Sign in
      </button>
    );
  return (
    <span className="flex items-center gap-3">
      <Link href="/watchlist" className="text-sm font-semibold text-foreground">
        ★ Watchlist
      </Link>
      <button onClick={() => supabase().auth.signOut()} className="text-xs text-muted hover:text-foreground">
        Sign out
      </button>
    </span>
  );
}
