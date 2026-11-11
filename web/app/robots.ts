// robots.txt: search engines may read every public page; private and technical pages are left out.
import type { MetadataRoute } from "next";
import { SITE } from "@/lib/site";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: { userAgent: "*", allow: "/", disallow: ["/api/", "/auth/", "/settings", "/watchlist", "/unsubscribe"] },
    sitemap: `${SITE.url}/sitemap.xml`,
    host: SITE.url,
  };
}
