"use client";
// "Ask about this trial/company": answers come only from Tremor's own data. 10 questions a day.
import { useEffect, useState } from "react";
import { signIn, supabase, useUser } from "@/lib/supabase-browser";
import { SectionHead } from "./ui";

type QA = { question: string; answer: string };

const EXAMPLES = {
  trial: ["Why is this score what it is?", "What does this trial's main goal mean?", "When will we know the results?"],
  company: ["How much money does this company have left?", "Which of its trials looks most worrying?", "What are insiders doing?"],
};

export function AskBox({ nctId, ticker, kind }: { nctId?: string; ticker: string; kind: "trial" | "company" }) {
  const user = useUser();
  const [question, setQuestion] = useState("");
  const [history, setHistory] = useState<QA[]>([]);
  const [remaining, setRemaining] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // Show today's earlier questions about this same page
  useEffect(() => {
    if (!user) return;
    const today = new Date().toISOString().slice(0, 10);
    let q = supabase().from("chat_questions").select("question,answer").gte("asked_at", today).order("asked_at");
    q = nctId ? q.eq("nct_id", nctId) : q.eq("ticker", ticker).is("nct_id", null);
    q.then(({ data }) => setHistory((data ?? []) as QA[]));
  }, [user, nctId, ticker]);

  async function submit(text: string) {
    const q = text.trim();
    if (!q || busy) return;
    setBusy(true);
    setError(null);
    const { data } = await supabase().auth.getSession();
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${data.session?.access_token ?? ""}` },
      body: JSON.stringify(nctId ? { question: q, nct_id: nctId } : { question: q, ticker }),
    });
    const body = await res.json().catch(() => ({}));
    if (res.ok) {
      setHistory((h) => [...h, { question: q, answer: body.answer }]);
      setQuestion("");
    } else {
      setError(body.error ?? "Something went wrong. Please try again.");
    }
    if (typeof body.remaining === "number") setRemaining(body.remaining);
    setBusy(false);
  }

  return (
    <section>
      <SectionHead title={`Ask about this ${kind}`} />
      <p className="mt-3 text-sm text-muted">
        Answers use only Tremor&apos;s data about this {kind}, written by AI. Not investment advice.
      </p>

      {user === null && (
        <button
          onClick={() => signIn()}
          className="mt-4 rounded-md bg-foreground px-4 py-2 text-sm font-medium text-background transition-colors hover:bg-navy-2"
        >
          Sign in to ask a question
        </button>
      )}

      {user && (
        <>
          {history.length > 0 && (
            <ul className="mt-4 space-y-3">
              {history.map((h, i) => (
                <li key={i}>
                  <p className="font-semibold">{h.question}</p>
                  <p className="mt-1 whitespace-pre-line text-sm leading-relaxed">{h.answer}</p>
                </li>
              ))}
            </ul>
          )}
          {history.length === 0 && (
            <div className="mt-3 flex flex-wrap gap-2">
              {EXAMPLES[kind].map((e) => (
                <button key={e} onClick={() => submit(e)} disabled={busy}
                  className="rounded-md border border-line px-3 py-1.5 text-sm text-ink-2 transition-colors hover:border-foreground hover:text-foreground disabled:opacity-50">
                  {e}
                </button>
              ))}
            </div>
          )}
          <form
            className="mt-4 flex gap-2"
            onSubmit={(e) => {
              e.preventDefault();
              submit(question);
            }}
          >
            <input
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              maxLength={500}
              placeholder="Type a question…"
              className="min-w-0 flex-1 rounded-md border border-line bg-background px-3 py-2 outline-none transition-colors focus:border-foreground"
            />
            <button disabled={busy || !question.trim()} className="rounded-md bg-foreground px-4 font-medium text-background transition-colors hover:bg-navy-2 disabled:opacity-50">
              {busy ? "…" : "Ask"}
            </button>
          </form>
          {error && <p role="alert" className="mt-2 text-sm text-tremor">{error}</p>}
          <p className="mt-2 text-xs text-muted">
            {remaining != null ? `${remaining} of 10 questions left today.` : "10 questions a day."}
          </p>
        </>
      )}
    </section>
  );
}
