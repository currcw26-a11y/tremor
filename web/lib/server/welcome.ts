// The welcome email, sent the moment someone signs up (from app/auth/callback/route.ts).
// The words come from the pipeline (web/lib/welcome-email.json, exported by `python -m tremor.export_rules`),
// so the website and the pipeline's backup sender always send the same email.
import template from "@/lib/welcome-email.json";
import { SITE } from "@/lib/site";
import { claim, insert, select, update } from "./supabase-admin";

type Profile = { user_id: string; email: string; name: string | null; unsubscribed: boolean; unsubscribe_token: string };

const FROM = "Tremor <alerts@tremoralerts.com>";

function escape(s: string) {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#x27;");
}

export function greeting(name: string | null) {
  const first = (name ?? "").trim().split(" ")[0];
  return first && first.length <= 40 ? `Hi ${first},` : "Hi,";
}

export function fill(p: Pick<Profile, "name" | "unsubscribe_token">) {
  const unsub = `${SITE.url}/unsubscribe?token=${p.unsubscribe_token}`;
  const g = greeting(p.name);
  return {
    subject: template.subject,
    html: template.html.replaceAll("{{UNSUBSCRIBE_URL}}", escape(unsub)).replaceAll("{{GREETING}}", escape(g)),
    text: template.text.replaceAll("{{UNSUBSCRIBE_URL}}", unsub).replaceAll("{{GREETING}}", g),
    oneClick: `${SITE.url}/api/unsubscribe?token=${p.unsubscribe_token}`,
  };
}

/** Within Resend's free limits? (Every kind of email counts.) */
async function roomToSend() {
  const now = new Date();
  const month = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), 1)).toISOString();
  const today = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate())).toISOString();
  const rows = await select<{ sent_at: string }>("email_log", { select: "sent_at", ok: "eq.true", sent_at: `gte.${month}` });
  return rows.filter((r) => r.sent_at >= today).length < template.daily_limit && rows.length < template.monthly_limit;
}

/** Sends the welcome email if this person hasn't had one. Safe to call on every sign-in. Never throws. */
export async function sendWelcome(userId: string) {
  const key = (process.env.RESEND_API_KEY ?? "").trim();
  if (!key) return; // the pipeline's backup sender will send it within 4 hours
  let claimed: Profile | undefined;
  try {
    [claimed] = await claim<Profile>(
      "profiles",
      { user_id: `eq.${userId}`, welcome_sent_at: "is.null", select: "user_id,email,name,unsubscribed,unsubscribe_token" },
      { welcome_sent_at: new Date().toISOString() },
    );
    if (!claimed || claimed.unsubscribed) return; // already welcomed (or turned emails off)
    if (!(await roomToSend())) throw new Error("email limit reached; the pipeline will retry");
    const msg = fill(claimed);
    const res = await fetch("https://api.resend.com/emails", {
      method: "POST",
      headers: { Authorization: `Bearer ${key}`, "Content-Type": "application/json" },
      body: JSON.stringify({
        from: FROM,
        to: [claimed.email],
        subject: msg.subject,
        html: msg.html,
        text: msg.text,
        headers: { "List-Unsubscribe": `<${msg.oneClick}>`, "List-Unsubscribe-Post": "List-Unsubscribe=One-Click" },
      }),
    });
    if (!res.ok) throw new Error(`Resend ${res.status}: ${(await res.text()).slice(0, 300)}`);
    const { id } = (await res.json()) as { id?: string };
    await insert("email_log", [{ kind: "welcome", user_id: userId, provider_id: id ?? null, ok: true }]);
  } catch (err) {
    console.error("Welcome email failed:", err);
    if (claimed) {
      // Hand it back to the pipeline's backup sender
      await update("profiles", { user_id: `eq.${userId}` }, { welcome_sent_at: null }).catch(() => {});
      await insert("email_log", [{ kind: "welcome", user_id: userId, ok: false, note: String(err).slice(0, 300) }]).catch(() => {});
    }
  }
}
