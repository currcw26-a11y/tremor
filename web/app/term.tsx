"use client";
// Tap-to-learn: a dotted underline that opens a short plain-English definition.
import Link from "next/link";
import { useId, useLayoutEffect, useRef, useState } from "react";
import { GLOSSARY, type GlossaryId } from "@/lib/glossary";

const WIDTH = 256; // px; the popup is moved left if it would run off the screen

export function Term({ id, children }: { id: GlossaryId; children?: React.ReactNode }) {
  const g = GLOSSARY[id];
  const [open, setOpen] = useState(false);
  const [shift, setShift] = useState(0);
  const wrap = useRef<HTMLSpanElement>(null);
  const popId = useId();

  useLayoutEffect(() => {
    if (!open) return;
    const r = wrap.current?.getBoundingClientRect();
    // clientWidth, not innerWidth: on phones innerWidth can grow to include the popup itself
    const screen = document.documentElement.clientWidth;
    if (r) setShift(Math.min(0, screen - 16 - Math.min(WIDTH, screen - 32) - r.left));
    const outside = (e: PointerEvent) => {
      if (!wrap.current?.contains(e.target as Node)) setOpen(false);
    };
    const esc = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("pointerdown", outside);
    document.addEventListener("keydown", esc);
    return () => {
      document.removeEventListener("pointerdown", outside);
      document.removeEventListener("keydown", esc);
    };
  }, [open]);

  return (
    <span ref={wrap} className="relative inline">
      <button
        type="button"
        aria-expanded={open}
        aria-controls={popId}
        onClick={() => setOpen((o) => !o)}
        className="cursor-help underline decoration-muted decoration-dotted decoration-2 underline-offset-4 [font:inherit] [letter-spacing:inherit]"
      >
        {children ?? g.term}
      </button>
      {open && (
        <span
          id={popId}
          role="dialog"
          aria-label={g.term}
          style={{ left: shift, width: WIDTH }}
          className="absolute top-full z-30 mt-1.5 block max-w-[calc(100vw-2rem)] rounded-lg bg-surface p-3 text-left text-sm font-normal normal-case leading-relaxed tracking-normal text-foreground shadow-lg"
        >
          <span className="block font-bold">{g.term}</span>
          <span className="mt-1 block">{g.text}</span>
          <Link href={`/glossary#${id}`} className="mt-2 block text-xs text-muted underline">
            All terms
          </Link>
        </span>
      )}
    </span>
  );
}
