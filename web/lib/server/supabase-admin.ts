// Server-only database helpers for the chat. Uses the SECRET key, which lives only in Vercel's
// server environment (never sent to browsers). Never import this file from a "use client" file.
const URL = (process.env.NEXT_PUBLIC_SUPABASE_URL ?? "").trim();
const PUBLISHABLE = (process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY ?? "").trim();
const SECRET = (process.env.SUPABASE_SECRET_KEY ?? "").trim();

function headers(extra: Record<string, string> = {}) {
  if (!SECRET) throw new Error("SUPABASE_SECRET_KEY is not set in Vercel");
  return { apikey: SECRET, "Content-Type": "application/json", ...extra };
}

export async function select<T>(table: string, params: Record<string, string>): Promise<T[]> {
  const res = await fetch(`${URL}/rest/v1/${table}?${new URLSearchParams(params)}`, { headers: headers(), cache: "no-store" });
  if (!res.ok) throw new Error(`Database error ${res.status}: ${await res.text()}`);
  return res.json();
}

export async function insert(table: string, rows: object[]) {
  const res = await fetch(`${URL}/rest/v1/${table}`, {
    method: "POST",
    headers: headers({ Prefer: "return=minimal" }),
    body: JSON.stringify(rows),
  });
  if (!res.ok) throw new Error(`Database error ${res.status}: ${await res.text()}`);
}

/** Who is asking? Checks the sign-in token the browser sent. Returns the user id, or null. */
export async function userFromToken(token: string | null): Promise<string | null> {
  if (!token) return null;
  const res = await fetch(`${URL}/auth/v1/user`, {
    headers: { apikey: PUBLISHABLE, Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  if (!res.ok) return null;
  const user = await res.json();
  return typeof user?.id === "string" ? user.id : null;
}

/** Update matching rows and return the ones that changed (a filter like welcome_sent_at=is.null makes it a claim). */
export async function claim<T>(table: string, filters: Record<string, string>, values: object): Promise<T[]> {
  const res = await fetch(`${URL}/rest/v1/${table}?${new URLSearchParams(filters)}`, {
    method: "PATCH",
    headers: headers({ Prefer: "return=representation" }),
    body: JSON.stringify(values),
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Database error ${res.status}: ${await res.text()}`);
  return res.json();
}

export async function update(table: string, filters: Record<string, string>, values: object) {
  const res = await fetch(`${URL}/rest/v1/${table}?${new URLSearchParams(filters)}`, {
    method: "PATCH",
    headers: headers({ Prefer: "return=minimal" }),
    body: JSON.stringify(values),
  });
  if (!res.ok) throw new Error(`Database error ${res.status}: ${await res.text()}`);
}
