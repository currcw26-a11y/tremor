"use client";
import Link from "next/link";
import { signIn, supabase, useUser } from "@/lib/supabase-browser";

export function UserMenu() {
  const user = useUser();
  if (user === undefined) return <span className="w-16" aria-hidden />;
  if (!user)
    return (
      <button
        onClick={() => signIn()}
        className="rounded-md border border-foreground/80 px-3 py-1.5 text-sm font-medium text-foreground transition-colors hover:bg-foreground hover:text-background"
      >
        Sign in
      </button>
    );
  return (
    <span className="flex items-center gap-3">
      <Link href="/watchlist" className="link-grow text-sm font-medium text-foreground">
        Watchlist
      </Link>
      <Link href="/settings" aria-label="Alert settings" className="text-sm text-muted hover:text-foreground">
        ⚙︎
      </Link>
      <button onClick={() => supabase().auth.signOut()} className="text-xs text-muted hover:text-foreground">
        Sign out
      </button>
    </span>
  );
}
