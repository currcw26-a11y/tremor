// Calling Claude for the chat, with the same safety nets as the pipeline:
// monthly budget cap, cost log, and the invented-number check.
import Anthropic from "@anthropic-ai/sdk";
import { insert, select } from "./supabase-admin";

export const MODEL = "claude-haiku-5-5";
const PRICE_PER_M = { input: 0.1, output: 0.5 }; // USD per million tokens (checked Nov 2026)
const BUDGET_USD = Number(process.env.AI_MONTHLY_BUDGET_USD ?? "15");

let client: Anthropic | null = null;
function claude() {
  const workspace = (process.env.ANTHROPIC_WORKSPACE_ID ?? "").trim();
  client ??= new Anthropic(workspace ? { defaultHeaders: { "anthropic-workspace-id": workspace } } : {});
  return client;
}

export async function overBudget(): Promise<boolean> {
  const start = new Date();
  start.setUTCDate(1);
  start.setUTCHours(0, 0, 0, 0);
  const rows = await select<{ cost_usd: string }>("ai_calls", { select: "cost_usd", created_at: `gte.${start.toISOString()}` });
  return rows.reduce((sum, r) => sum + Number(r.cost_usd), 0) >= BUDGET_USD;
}

/** Numbers in `answer` that don't appear anywhere in `facts`. */
export function inventedNumbers(answer: string, facts: string): string[] {
  const nums = (s: string) =>
    new Set((s.match(/\d[\d,]*(?:\.\d+)?/g) ?? []).map((n) => n.replace(/,/g, "").replace(/\.0+$/, "")));
  const allowed = nums(facts);
  return [...nums(answer)].filter((n) => !allowed.has(n));
}

const ADVICE = /\b(you should|i (would|recommend)|consider|good time to)\b[^.]{0,40}\b(buy|sell|hold|invest)/i;

export async function ask(system: string, facts: string, question: string): Promise<string | null> {
  const prompt = `Tremor's data:\n${facts}\n\nQuestion from a reader: ${question}`;
  for (let attempt = 0; attempt < 2; attempt++) {
    const res = await claude().messages.create({
      model: MODEL,
      max_tokens: 2000,
      system:
        system +
        (attempt ? "\nIMPORTANT: your last answer used a number that isn't in Tremor's data. Use only numbers from the data, or none." : ""),
      output_config: { effort: "low" },
      messages: [{ role: "user", content: prompt }],
    });
    const text = res.content.flatMap((b) => (b.type === "text" ? [b.text] : [])).join("").trim();
    const bad = inventedNumbers(text, prompt);
    const ok = res.stop_reason === "end_turn" && !!text && bad.length === 0 && !ADVICE.test(text);
    const cost = (res.usage.input_tokens * PRICE_PER_M.input + res.usage.output_tokens * PRICE_PER_M.output) / 1e6;
    await insert("ai_calls", [{
      purpose: "chat", model: MODEL, input_tokens: res.usage.input_tokens, output_tokens: res.usage.output_tokens,
      cost_usd: Number(cost.toFixed(6)), ok,
      note: ok ? null : bad.length ? `number check failed: ${bad.join(",")}` : `rejected (stop_reason=${res.stop_reason})`,
    }]);
    if (ok) return text;
  }
  return null;
}
