"use client";
// Shows "3 hours ago". Worked out in the visitor's browser, so it's always current
// even though the page itself is cached.
import { useEffect, useState } from "react";
import { niceDate, timeAgo } from "@/lib/words";

export function TimeAgo({ iso, prefix = "" }: { iso: string | null; prefix?: string }) {
  const [text, setText] = useState(iso ? `on ${niceDate(iso)}` : "never");
  useEffect(() => {
    const update = () => setText(timeAgo(iso));
    update();
    const timer = setInterval(update, 60_000);
    return () => clearInterval(timer);
  }, [iso]);
  return (
    <time dateTime={iso ?? undefined} suppressHydrationWarning>
      {prefix}
      {text}
    </time>
  );
}
