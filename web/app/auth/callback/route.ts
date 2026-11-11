// Google sends people back here after they sign in. We swap the one-time code for a
// session (saved in a cookie, so they stay signed in), then return them to the page they were on.
// First sign-in: a welcome email goes out right after (lib/server/welcome.ts).
import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";
import { after, NextResponse, type NextRequest } from "next/server";
import { sendWelcome } from "@/lib/server/welcome";

export async function GET(request: NextRequest) {
  const url = new URL(request.url);
  const code = url.searchParams.get("code");
  const next = url.searchParams.get("next") ?? "/";
  const safeNext = next.startsWith("/") && !next.startsWith("//") ? next : "/"; // only send people to our own pages

  if (code) {
    const store = await cookies();
    const sb = createServerClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!.trim(),
      process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY!.trim(),
      {
        cookies: {
          getAll: () => store.getAll(),
          setAll: (list) => list.forEach(({ name, value, options }) => store.set(name, value, options)),
        },
      },
    );
    const { data, error } = await sb.auth.exchangeCodeForSession(code);
    if (!error) {
      // New here? Send the welcome email after the page has loaded (does nothing for people already welcomed)
      const userId = data.user?.id;
      if (userId) after(() => sendWelcome(userId));
      return NextResponse.redirect(new URL(safeNext, url.origin));
    }
    console.error("Sign-in failed:", error.message);
  }
  return NextResponse.redirect(new URL("/?signin=failed", url.origin));
}
