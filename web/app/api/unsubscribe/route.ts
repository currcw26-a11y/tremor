// One-click unsubscribe for email apps (Gmail and Apple Mail show their own "Unsubscribe" button,
// which POSTs here). The token in the link is the only thing needed; no sign-in.
import { NextResponse, type NextRequest } from "next/server";

async function unsubscribe(token: string | null) {
  if (!token || !/^[0-9a-f-]{36}$/i.test(token)) return false;
  const res = await fetch(`${process.env.NEXT_PUBLIC_SUPABASE_URL!.trim()}/rest/v1/rpc/unsubscribe_by_token`, {
    method: "POST",
    headers: {
      apikey: process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY!.trim(),
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ token }),
  });
  return res.ok && (await res.json()) === true;
}

export async function POST(request: NextRequest) {
  const ok = await unsubscribe(new URL(request.url).searchParams.get("token"));
  return NextResponse.json({ unsubscribed: ok }, { status: ok ? 200 : 400 });
}
