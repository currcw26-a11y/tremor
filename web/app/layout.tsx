import type { Metadata } from "next";
import { IBM_Plex_Mono, IBM_Plex_Sans, Newsreader } from "next/font/google";
import Link from "next/link";
import { UserMenu } from "./user-menu";
import "./globals.css";
import { SITE } from "@/lib/site";

// Newsreader (an editorial serif) for headlines, IBM Plex Sans for reading, Plex Mono for tickers, dates and numbers
const serif = Newsreader({ variable: "--font-newsreader", subsets: ["latin"], axes: ["opsz"], style: ["normal", "italic"] });
const sans = IBM_Plex_Sans({ variable: "--font-plex-sans", subsets: ["latin"], weight: ["400", "500", "600", "700"] });
const mono = IBM_Plex_Mono({ variable: "--font-plex-mono", subsets: ["latin"], weight: ["400", "500", "600"] });

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

function Mark({ className = "" }: { className?: string }) {
  return (
    <span className={`flex items-end gap-[3px] ${className}`} aria-hidden>
      <span className="h-3.5 w-[5px] rounded-full bg-calm" />
      <span className="h-[18px] w-[5px] rounded-full bg-shaky" />
      <span className="h-[22px] w-[5px] rounded-full bg-tremor" />
    </span>
  );
}

const NAV = [
  { href: "/trials", label: "Trials", phone: true },
  { href: "/changes", label: "Changes", phone: false },
  { href: "/upcoming", label: "Calendar", phone: true },
  { href: "/companies", label: "Companies", phone: false },
  { href: "/track-record", label: "Track record", phone: false },
  { href: "/learn", label: "Learn", phone: false },
];

const FOOTER = [
  {
    title: "Explore",
    links: [["/trials", "All trials"], ["/changes", "Latest changes"], ["/weekly", "Tremor Weekly"], ["/upcoming", "Calendar"], ["/companies", "Companies"], ["/track-record", "Track record"]],
  },
  {
    title: "Learn",
    links: [["/learn", "How biotech stocks move"], ["/how-it-works", "How the score works"], ["/glossary", "Words to know"]],
  },
  { title: "About", links: [["/privacy", "Privacy"], ["/terms", "Terms"]] },
];

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${serif.variable} ${sans.variable} ${mono.variable} h-full antialiased`}>
      <body className="flex min-h-full flex-col font-sans">
        <header className="sticky top-0 z-40 border-b border-line bg-background/90 backdrop-blur supports-[backdrop-filter]:bg-background/80">
          <nav className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-4 px-4 sm:px-6 lg:px-8">
            <Link href="/" className="group flex items-center gap-2.5">
              <Mark className="transition-transform duration-300 group-hover:-translate-y-px" />
              <span className="font-serif text-[1.6rem] font-semibold leading-none tracking-tight">Tremor</span>
            </Link>
            <div className="flex items-center gap-4 text-[15px] text-ink-2 sm:gap-6">
              {NAV.map((n) => (
                <Link key={n.href} href={n.href} className={`link-grow hover:text-foreground ${n.phone ? "" : "hidden md:inline"}`}>
                  {n.label}
                </Link>
              ))}
              <UserMenu />
            </div>
          </nav>
        </header>
        <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8 sm:px-6 lg:px-8 lg:py-12">{children}</main>
        <footer className="mt-16 bg-navy text-white/75">
          <div className="mx-auto grid max-w-6xl gap-10 px-4 py-12 sm:px-6 md:grid-cols-12 lg:px-8">
            <div className="md:col-span-5">
              <Link href="/" className="flex items-center gap-2.5 text-white">
                <Mark />
                <span className="font-serif text-2xl font-semibold tracking-tight">Tremor</span>
              </Link>
              <p className="mt-4 max-w-sm text-sm leading-relaxed">
                Tremor reads public records about cancer drug trials every four hours and explains what changed, in plain
                English. Data from ClinicalTrials.gov, the SEC, the Federal Register, and state layoff notices.
              </p>
            </div>
            {FOOTER.map((col) => (
              <div key={col.title} className="md:col-span-2">
                <p className="text-xs font-semibold uppercase tracking-[0.14em] text-white/50">{col.title}</p>
                <ul className="mt-3 space-y-2 text-sm">
                  {col.links.map(([href, label]) => (
                    <li key={href}>
                      <Link href={href} className="link-grow text-white/85 hover:text-white">
                        {label}
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
          <div className="border-t border-white/10">
            <p className="mx-auto max-w-6xl px-4 py-5 text-xs leading-relaxed sm:px-6 lg:px-8">
              <span className="font-semibold text-white">Not investment advice.</span> Tremor shows what changed in
              public records and what happened in similar past cases. It never tells anyone to buy or sell, and many
              trial edits turn out to be harmless paperwork.
            </p>
          </div>
        </footer>
      </body>
    </html>
  );
}
