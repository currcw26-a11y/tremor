// AI chat: answers questions about one trial or company, using only Tremor's own data.
// Signed-in users only, 10 questions per day each, paused if the monthly AI budget is used up.
import { NextResponse, type NextRequest } from "next/server";
import { companyOnlyContext, trialContext } from "@/lib/server/chat-context";
import { ask, overBudget } from "@/lib/server/claude";
import { insert, select, userFromToken } from "@/lib/server/supabase-admin";

const DAILY_LIMIT = 10;
const MAX_QUESTION = 500;

const SYSTEM = `You answer questions on Tremor, a website for college students who have never bought a stock.
It tracks cancer drug trials run by public companies.

Rules (never break these):
- Answer ONLY from "Tremor's data" in the message. If the answer isn't there, say Tremor doesn't have that information.
- Never add a number, percentage, date, price, prediction, or price target that isn't in the data.
- Never say or hint that anyone should buy, sell, or hold a stock, or how a stock will move. If asked, say Tremor
  doesn't give investment advice, then explain what the data shows instead.
- Explain any finance or science term in a few words. Plain English. Say "typically", not "median".
- Be honest about uncertainty: many trial edits are harmless, and a worry score counts warning signs; it isn't a prediction.
- Keep it under 120 words. Plain text, no headings or bullet points.`;

function json(body: object, status = 200) {
  return NextResponse.json(body, { status });
}

export async function POST(request: NextRequest) {
  try {
    return await handle(request);
  } catch (err) {
    // Explain setup problems clearly (never includes the key itself)
    const msg = err instanceof Error ? err.message : String(err);
    console.error("Chat error:", msg);
    if (msg.includes("SUPABASE_SECRET_KEY is not set"))
      return json({ error: "Setup problem: SUPABASE_SECRET_KEY isn't set in Vercel (or the site wasn't redeployed after adding it)." }, 500);
    if (/Database error 40[13]/.test(msg))
      return json({ error: "Setup problem: the database didn't accept SUPABASE_SECRET_KEY in Vercel. Check it's the sb_secret_ key." }, 500);
    return json({ error: "Something went wrong on our side. Please try again later." }, 500);
  }
}

async function handle(request: NextRequest) {
  const token = request.headers.get("authorization")?.replace(/^Bearer /, "") ?? null;
  const userId = await userFromToken(token);
  if (!userId) return json({ error: "Please sign in to ask questions." }, 401);

  const body = await request.json().catch(() => ({}));
  const question = String(body.question ?? "").trim().slice(0, MAX_QUESTION);
  const nct = typeof body.nct_id === "string" && /^NCT\d{8}$/.test(body.nct_id) ? body.nct_id : null;
  const ticker = typeof body.ticker === "string" && /^[A-Z.]{1,6}$/.test(body.ticker) ? body.ticker : null;
  if (!question) return json({ error: "Type a question first." }, 400);
  if (!nct && !ticker) return json({ error: "Ask from a trial or company page." }, 400);

  const today = new Date().toISOString().slice(0, 10);
  const asked = await select<{ id: number }>("chat_questions", { select: "id", user_id: `eq.${userId}`, asked_at: `gte.${today}` });
  if (asked.length >= DAILY_LIMIT)
    return json({ error: `You've used all ${DAILY_LIMIT} questions for today. Come back tomorrow!`, remaining: 0 }, 429);
  if (await overBudget())
    return json({ error: "The AI chat is paused for the rest of this month to stay within Tremor's budget." }, 503);

  const ctx = nct ? await trialContext(nct) : null;
  const facts = ctx?.text ?? (ticker ? await companyOnlyContext(ticker) : null);
  if (!facts) return json({ error: "Tremor doesn't track that trial or company." }, 404);

  let answer: string | null = null;
  try {
    answer = await ask(SYSTEM, facts, question);
  } catch (err) {
    console.error("Chat failed:", err);
    const status = (err as { status?: number }).status;
    const detail = status === 401 ? " (Anthropic didn't accept ANTHROPIC_API_KEY in Vercel)"
      : status === 400 ? " (Anthropic setup: the key may need ANTHROPIC_WORKSPACE_ID in Vercel)" : "";
    return json({ error: `The AI chat isn't available right now${detail}. Please try again later.` }, 502);
  }
  const reply = answer ?? "Sorry, I couldn't answer that reliably from Tremor's data. Try asking it a different way.";
  await insert("chat_questions", [{ user_id: userId, question, answer: reply, nct_id: nct, ticker: ctx?.ticker ?? ticker }]);
  return json({ answer: reply, remaining: DAILY_LIMIT - asked.length - 1 });
}
