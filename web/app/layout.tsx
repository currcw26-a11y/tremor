import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import { UserMenu } from "./user-menu";
import "./globals.css";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Tremor — early warnings for cancer drug trials",
  description: "Tremor watches public data about cancer drug trials and flags quiet changes before big news comes out.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col font-sans">
        <header className="border-b border-line bg-surface">
          <nav className="mx-auto flex max-w-3xl items-center justify-between px-4 py-4">
            <Link href="/" className="flex items-center gap-2 text-xl font-black tracking-tight">
              <span className="flex gap-0.5" aria-hidden>
                <span className="h-4 w-1.5 rounded-full bg-calm" />
                <span className="h-4 w-1.5 rounded-full bg-shaky" />
                <span className="h-4 w-1.5 rounded-full bg-tremor" />
              </span>
              Tremor
            </Link>
            <div className="flex items-center gap-4 text-sm font-semibold text-muted">
              <Link href="/trials" className="hover:text-foreground">
                Trials
              </Link>
              <Link href="/companies" className="hover:text-foreground">
                Companies
              </Link>
              <UserMenu />
            </div>
          </nav>
        </header>
        <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-8">{children}</main>
        <footer className="border-t border-line bg-surface">
          <div className="mx-auto max-w-3xl px-4 py-6 text-sm text-muted">
            <p className="font-semibold text-foreground">Not investment advice.</p>
            <p className="mt-1">
              Tremor shows what changed in public records. It never tells anyone to buy or sell. Many trial
              edits are harmless paperwork. Data from ClinicalTrials.gov, the SEC, and the Federal Register.
            </p>
          </div>
        </footer>
      </body>
    </html>
  );
}
