// sitemap.xml: every public page, so Google can find all of them (submitted in Google Search Console).
import type { MetadataRoute } from "next";
import { SITE } from "@/lib/site";
import { sitemapData } from "@/lib/sitemap-data";

const PAGES = ["", "/trials", "/companies", "/upcoming", "/track-record", "/how-it-works", "/learn", "/glossary", "/privacy", "/terms"];

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const { trials, tickers } = await sitemapData();
  return [
    ...PAGES.map((path) => ({ url: `${SITE.url}${path}`, changeFrequency: "daily" as const, priority: path ? 0.7 : 1 })),
    ...tickers.map((t) => ({ url: `${SITE.url}/companies/${t}`, changeFrequency: "daily" as const, priority: 0.6 })),
    ...trials.map((t) => ({
      url: `${SITE.url}/trials/${t.nct_id}`,
      // the last time the official record changed (a date we know is real, not "today")
      ...(t.last_update_posted && /^\d{4}-\d{2}-\d{2}$/.test(t.last_update_posted) ? { lastModified: t.last_update_posted } : {}),
      changeFrequency: "daily" as const,
      priority: 0.5,
    })),
  ];
}
