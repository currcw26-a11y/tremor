"use client";
// A button (not automatic on page load), so email scanners that open links can't unsubscribe people by accident.
import Link from "next/link";
import { useState } from "react";

export function UnsubscribeButton({ token }: { token: string }) {
  const [state, setState] = useState<"idle" | "working" | "done" | "error">("idle");

  async function go() {
    setState("working");
    const res = await fetch(`/api/unsubscribe?token=${encodeURIComponent(token)}`, { method: "POST" });
    setState(res.ok ? "done" : "error");
  }

  if (state === "done")
    return (
      <div className="rounded-xl border border-line bg-surface p-6">
        <p className="text-lg font-bold">You&apos;re unsubscribed.</p>
        <p className="mt-1 text-muted">Tremor won&apos;t email you anymore. Changed your mind? Turn emails back on in your{" "}
          <Link href="/settings" className="underline">alert settings</Link>.</p>
      </div>
    );
  return (
    <div className="rounded-xl border border-line bg-surface p-6">
      <p className="text-lg font-bold">Stop all Tremor emails?</p>
      <p className="mt-1 text-muted">You&apos;ll stop getting instant alerts and the daily digest.</p>
      <button onClick={go} disabled={state === "working"}
        className="mt-4 rounded-full bg-foreground px-5 py-2 font-semibold text-background disabled:opacity-60">
        {state === "working" ? "Unsubscribing…" : "Unsubscribe"}
      </button>
      {state === "error" && <p role="alert" className="mt-3 text-sm text-tremor">That link didn&apos;t work. Try the newest email, or change your alert settings.</p>}
    </div>
  );
}
