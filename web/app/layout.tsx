import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import { UserMenu } from "./user-menu";
import "./globals.css";
import { SITE } from "@/lib/site";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

const DESCRIPTION =
  "Free early warnings for cancer drug trials, in plain English. Tremor watches trial records, SEC filings and FDA notices and gives every trial a 0-100 worry score. Not investment advice.";

export const metadata: Metadata = {
  metadataBase: new URL(SITE.url),
  title: { default: "Tremor: early warnings for cancer drug trials", template: "%s · Tremor" },
  description: DESCRIPTION,
  applicationName: "Tremor",
  // No canonical or og:url here: pages inherit layout metadata, so each page sets its own address
  openGraph: { type: "website", siteName: "Tremor", locale: "en_US" },
  twitter: { card: "summary_large_image" },
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
            <div className="flex items-center gap-3 text-sm font-semibold text-muted sm:gap-4">
              <Link href="/trials" className="hover:text-foreground">
                Trials
              </Link>
              <Link href="/upcoming" className="hover:text-foreground">
                Upcoming
              </Link>
              <Link href="/companies" className="hidden hover:text-foreground sm:inline">
                Companies
              </Link>
              <Link href="/track-record" className="hidden hover:text-foreground sm:inline">
                Track record
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
            <p className="mt-3 flex flex-wrap gap-x-4 gap-y-1">
              <Link href="/companies" className="underline">
                Companies
              </Link>
              <Link href="/track-record" className="underline">
                Track record
              </Link>
              <Link href="/how-it-works" className="underline">
                How the score works
              </Link>
              <Link href="/learn" className="underline">
                How biotech stocks move
              </Link>
              <Link href="/glossary" className="underline">
                Words to know
              </Link>
              <Link href="/privacy" className="underline">
                Privacy
              </Link>
              <Link href="/terms" className="underline">
                Terms
              </Link>
            </p>
          </div>
        </footer>
      </body>
    </html>
  );
}
