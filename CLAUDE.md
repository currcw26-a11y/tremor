# Tremor — Project Spec (Claude's memory file)


## What Tremor is

An early warning system for biotech stocks. It watches public data about cancer drug trials and emails users when something looks off before big news comes out. Pitch: "The Pentagon pizza index, but for cancer drug trials."

When a trial is in trouble, companies rarely say so right away, but clues show up first: quiet edits to the trial's official record (changing the main goal, cutting patients, pushing dates back), executives selling stock, a key executive quitting, hiring stopping, layoff notices, the FDA scheduling an advisory meeting, or a rival drug that works the same way failing. Tremor checks all of these every 4 hours, turns them into a 0 to 100 worry score for each trial, and explains every change in plain English.

## Who it's for

Beginner investors, starting with my classmates. Most have never bought a stock. Everything must make sense to them.

## Hard rules

1. Never tell anyone to buy or sell. Show what changed, what happened in similar past cases, and the possible upside and downside. Every user sees the same content for the same trial. Nothing is tailored to anyone's own money.
2. Code computes every number from real data. Claude only explains those numbers. Claude must never invent a statistic, prediction, or price target.
3. A "Not investment advice" note in the footer of every page and every email.
4. Plain English everywhere. Write for someone who has never bought a stock. Use "9 out of 14," not "64%." Use "typically," not "median." Explain or skip any finance or science term. Self-check: could a college freshman explain this back to a friend?
5. Be honest about uncertainty. Every breakdown shows how many past cases it's based on. Many trial edits are harmless paperwork, and the site should say so.

## Scope (version 1)

- Phase 2 and Phase 3 cancer (oncology) trials sponsored by companies traded on US stock exchanges.
- Matching trial sponsors to stock tickers is tricky, because names differ and partners sometimes run trials. Keep a sponsor-to-ticker lookup table. Claude can suggest matches, but I confirm each one before it's used for alerts, through a simple admin page or a CSV I edit.

## The worry score

- 0 to 100 for each trial, with a label and color: Calm (green), Shaky (yellow), Tremor (red). Start with cutoffs of 0 to 39, 40 to 69, and 70 to 100, kept in one config file.
- Rules-based and transparent for version 1, not machine learning. Each signal adds points, points fade over time, and a few events jump straight to red. Put every weight in one config file. Starting guesses, to tune later with the backtest:
  - Main goal (primary outcome) changed or removed: +25
  - Enrollment cut by 15% or more: +15
  - Completion date pushed back 3+ months: +10
  - Trial suspended, terminated, or withdrawn: straight to red
  - Results overdue (finished 12+ months ago, no results posted): +10
  - Insider selling cluster (2+ insiders selling within 30 days, not marked as pre-planned 10b5-1 trades): +10
  - Key executive leaves, like the chief medical officer or head of R&D (often an 8-K with item 5.02): +15
  - FDA advisory committee meeting scheduled for the drug: +10
  - Layoff notice filed by the company: +15
  - Clinical job postings drop sharply: +5
  - A rival trial with the same mechanism in the same cancer fails: +10
- Save every score change along with the signals behind it, so the site can show exactly why a score moved.

## Tremors and email alerts

A "tremor" is anything that could give users a head start before a big event. Triggers:
- Big score jump: 15+ points in one update (configurable)
- Critical single event: main goal changed, enrollment cut, trial stopped, key executive leaves
- Head start signals: new FDA advisory meeting, insider selling cluster, results date pushed back, results overdue, rival same-mechanism trial failing, layoff notice

Who gets what: each user gets tremors for trials on their watchlist, plus any "huge" tremor across all tracked trials (the score turns red or a critical event happens).

Timing: big tremors are emailed right away, in the run that finds them. Smaller changes go into one daily digest email.

- Bundle all of a user's tremors from one run into a single email.
- Users sign in once with Google and never need to log in again. Everything runs on its own after that.
- One-click unsubscribe link in every email, plus settings to turn off the digest or instant alerts.
- Send email through Resend's free plan: 100 emails a day, 3,000 a month. Track the count and never go over. If we get close, skip digests before skipping instant alerts.
- Each email includes what changed, the score before and after, why it matters in plain English, the upside/downside breakdown, and a "what to check next" list (links to the exact trial record changes, the SEC filing, and the company's next expected event). Never "buy" or "sell."
- Text messages are a later feature. Design the alert code so another channel can be added.

Example alert (fake company, fake numbers). This is the tone and level I want:

> 🔴 Tremor: Example Bio
> What happened: Example Bio quietly changed its big cancer drug study to make it easier to call a success, and cut the number of patients by 20%.
> Why that's a red flag: companies don't usually lower the bar unless they're worried about clearing it.
> When this happened before: 14 companies made similar changes. For 9 of them the results disappointed, and the stock typically lost about half its value the day the news came out. For the other 5 the results were fine, and the stock typically went up about 20%.
> How big a deal is this for them: huge. This is basically the company's only big drug.
> Money left: about 8 months. If the drug fails, they'll likely need to sell more shares to raise cash, which usually makes each share worth less.
> How sure are we: medium. 14 past examples is a decent number, but not a lot.
> When we'll find out: results are expected early next year.

## Upside/downside breakdown

Code computes it from past cases, and Claude explains it:
- Similar past cases: past trials with the same kind of signal. How many were followed by bad news (trial failed, stopped, or rejected by the FDA) versus fine results.
- The typical stock move when the news came out, for both outcomes. Measure from the close the day before the news to the close the day after.
- How much rides on it: is this the company's main drug, or one of many?
- Money left: months of cash, from SEC financial data (cash divided by the recent spending rate).
- Confidence: low under 10 cases, medium for 10 to 29, high for 30 or more. Always show the count.
- Next expected event: the results date or FDA decision date, if known.
- Show the past cases as a row of dots (red = went badly, green = fine).

## Pages

Public, no login:
1. Home feed: latest tremors and biggest score moves, newest first
2. Trial page: score, score history chart, every change with a plain-English explanation, the upside/downside breakdown, and links to the sources. A "Show details" button expands the technical version.
3. Company page: all its tracked trials, insider trades, filings, job and layoff signals, and cash left
4. Track record page: every past flag and what happened next, hits and misses. This is what proves Tremor works.
5. How the score works: every rule and weight, written simply
6. How biotech stocks move: a 2-minute explainer for beginners

Logged in (Google sign-in):
7. Watchlist: star trials or companies
8. Alert settings
9. AI chat: ask about any tracked trial or company. Answers come from Tremor's own data (pass the relevant records to Claude) and follow the same hard rules. Limit: 10 questions per user per day.

Also:
- Tap-to-learn: any unavoidable term (Phase 3, insider, FDA advisory committee, enrollment) gets a small popup explanation.
- "Tremor Weekly": a weekly roundup Claude writes from that week's data, shown on the home page. Lower priority (Week 5).

## Look and feel

Modern startup: clean, bold, and confident, like a real product. Light or dark is your call, but it has to look great on a phone, since most people will open it from an email. Score badges are the visual center. Not cluttered.

## Tech stack (all free tiers)

- Website: Next.js (App Router, TypeScript) and Tailwind, hosted on Vercel's free plan. I'll buy a domain.
- Database and Google login: Supabase free plan (Postgres plus Supabase Auth with Google).
- Data pipeline: Python, in a /pipeline folder, run by GitHub Actions every 4 hours. Vercel's free plan only allows once-a-day scheduled jobs, so the schedule lives on GitHub. The repo will be public, so Actions minutes are free. GitHub disables scheduled workflows in public repos after 60 days with no repo activity, so remind me about that.
- Email: Resend free plan.
- AI: the Claude API with my key. Use the cheapest model that does the job well (claude-haiku-5-5) for explanations, alert text, and chat. Check Anthropic's docs for current model names and prices before coding.
- Each pipeline run: fetch new data, save snapshots, find differences, update signals and scores, call Claude only for things that actually changed, send instant alerts, and (once a day) send digests.

## Keeping costs down

- Only call Claude when something actually changed. Cache every explanation.
- Log the tokens and estimated cost of every Claude call in a table. Add a monthly budget cap (an env var, default $15). When it's reached, stop non-essential AI calls (chat, weekly roundup) and keep alerts working with shorter text.
- Chat limit: 10 questions per user per day.

## Data sources

All free. Send a User-Agent header with "Tremor" plus a contact email (from a CONTACT_EMAIL env var) to the SEC and the job boards. Cache everything and keep request rates polite.

Week 1 sources (core):
- ClinicalTrials.gov API v2: https://clinicaltrials.gov/api/v2/studies. No key. No published rate limit, so cache and back off on errors. Up to 1,000 studies per page, paged with pageToken. Check /api/v2/version to see if new data has posted. Tremor catches edits by saving its own snapshot of each tracked trial every run and diffing it against the last one.
- SEC EDGAR (no key, max 10 requests per second, User-Agent required):
  - Ticker lookup: https://www.sec.gov/files/company_tickers.json
  - Filings list: https://data.sec.gov/submissions/CIK##########.json. 8-Ks come tagged with item codes, like 5.02 for executive changes.
  - Insider trades: Form 4 XML from the EDGAR archives. Read each filing's index first, since filenames vary. Since April 2023, Form 4 has a checkbox for pre-planned 10b5-1 trades.
  - Financials: https://data.sec.gov/api/xbrl/companyfacts/CIK##########.json (cash, spending, shares outstanding)
  - Full-text search: https://efts.sec.gov/LATEST/search-index?q= (find filings that mention a drug code)
  - EDGAR posts filings on business days from 6 a.m. to 10 p.m. Eastern.
- Federal Register API: https://www.federalregister.gov/api/v1/documents.json with conditions[agencies][]=food-and-drug-administration, conditions[type][]=NOTICE, and conditions[term]=advisory committee. No key. The FDA must post these at least 15 days before the meeting.

Week 3 sources (more signals):
- Job boards (public JSON, no key): Greenhouse https://boards-api.greenhouse.io/v1/boards/{board}/jobs, Lever https://api.lever.co/v0/postings/{site}?mode=json, Ashby https://api.ashbyhq.com/posting-api/job-board/{board}. Find board names from company careers pages. Check once or twice a day. Use Greenhouse's first_published date, not updated_at.
- Layoff notices: the warn-scraper Python package (covers 39 states, but not Massachusetts, North Carolina, or Pennsylvania), plus the Massachusetts weekly WARN CSV from mass.gov.

Week 4 sources (prices, backtest, rivals):
- openFDA (a free key raises the daily cap from 1,000 to 120,000 requests): Drugs@FDA https://api.fda.gov/drug/drugsfda.json for approval history, and rejection letters https://api.fda.gov/transparency/crl.json. The rejection letters aren't a live signal; use them to learn what problems lead to rejections.
- Financial Modeling Prep (free key): up to 5 years of daily prices, 250 calls a day. Pull history once, store it, and never re-pull it.
- Massive, formerly Polygon.io (free key): daily closing prices, 5 calls a minute.
- Avoid yfinance. It's unofficial and breaks without warning.
- Trial version history for the backtest: ClinicalTrials.gov has no official history API. The site's Record History tab and tools like the cthist R package can get past versions. Use these only for the backtest, never for live alerts.
- AACT (free account): all of ClinicalTrials.gov as a Postgres database, handy for bulk historical queries.
- "When did the news break": combine the 8-K date, the date results posted, and the day of the biggest stock move.
- Rival drugs: ChEMBL mechanism API https://www.ebi.ac.uk/chembl/api/data/mechanism, Open Targets GraphQL https://api.platform.opentargets.org/api/v4/graphql (known drugs for a disease), and the NCI Thesaurus API https://api-evsrest.nci.nih.gov/api/v1 (cancer drug names and definitions). If a new drug isn't in any database, Claude labels its mechanism from the trial description, and the site marks it "unconfirmed."

Known gaps: there's no free source for FDA decision dates (have Claude pull them from company SEC filings), big cancer conference dates (I'll enter these by hand), or press release wires (use 8-Ks instead).

## Build plan

- Week 1, foundation: repo, Supabase project and database schema, the pipeline for ClinicalTrials.gov (fetch, snapshot, diff), SEC, and Federal Register, running on GitHub Actions every 4 hours. A basic site that lists tracked trials. Checkpoint: I can see real trials and real detected changes.
- Week 2, brains and pages: scoring engine, Claude explanations, home feed, trial pages, company pages, Google sign-in, watchlist. Checkpoint: a classmate can sign in and star a trial.
- Week 3, alerts and launch: instant alerts and daily digest through Resend, unsubscribe, alert settings, AI chat with limits, job boards and layoff notices, cash runway. Deploy to Vercel on my domain. Checkpoint: real emails arrive on their own. This is the "fully working" milestone.
- Week 4, proof: price data, backtest, track record page, upside/downside breakdown with the dot visuals, rival drugs.
- Week 5, polish: design pass, tap-to-learn glossary, explainer pages, Tremor Weekly, mobile testing, and fixing bugs my classmates find.

If we fall behind, protect Weeks 1 to 3 first. A working site with alerts beats a half-finished one with every feature.

## Progress

- [x] Project folder created and spec saved to CLAUDE.md (Nov 5, 2026)
- [x] Week 1 plan approved (Nov 6, 2026)
- [x] Step 1: GitHub repo created and first push
- [x] Step 2: Supabase project + database schema
- [x] Step 3: Fetch cancer trials from ClinicalTrials.gov (4,535 trials, 1,234 sponsors on Nov 6)
- [x] Step 4: Sponsor → ticker matching (215 sponsors confirmed Nov 6; Roche, Daiichi, Bayer, Astellas excluded as OTC-only)
- [x] Step 5: Snapshot + diff (with tests) — first real run Nov 6: 1,669 trials snapshotted; end-to-end test caught a staged edit
- [x] Step 6: SEC filings, insider trades, FDA meetings (Nov 6: 4,218 filings, 3,719 insider trade lines, 174 exec-change 8-Ks; FDA search verified on 3 years of history)
- [x] Step 7: GitHub Actions every 4 hours (first run green Nov 6; secrets SUPABASE_URL, SUPABASE_SECRET_KEY, CONTACT_EMAIL)
- [x] Step 8: Basic website listing trials and changes (Next.js 16 in /web: home, /trials search, /trials/[nct]; runs locally, deploys to Vercel in Week 3)
- [x] Week 1 checkpoint: real changes detected Nov 6 (47 changes in 40 trials, incl. Novartis JDQ443 trial terminated, Amgen tarlatamab delayed 33 months)
- [x] Site live at https://tremor-ecru.vercel.app (Vercel project root = web/, env vars NEXT_PUBLIC_SUPABASE_URL + NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY as Config). Custom domain later: Vercel → Settings → Domains.
- [x] Week 2 plan approved (Nov 6)
- [x] Week 2 step 1: worry score engine (config/tremor.yaml, pipeline/tremor/scoring.py, score_job.py; 8-K 5.02 reader). Day-one result: 1 red (NVS stopped trial), 0 yellow, rest calm.
- [x] Week 2 step 2: Claude explanations (claude-haiku-5-5, effort low; ai_calls cost log; $15/mo cap via AI_MONTHLY_BUDGET_USD; number check rejects any digit not in the facts). Key is workspace-scoped, lives only in GitHub secrets (and Vercel later for chat). ~$0.0001-0.0003 per explanation.
- [x] Week 2 step 3: home feed (biggest worries + latest important changes, minor hidden behind ?minor=1)
- [x] Week 2 step 4: trial pages (big badge, 'Why this score' reasons summing to total, step chart with table view, Show details)
- [x] Week 2 step 5: company pages (/companies list + /companies/[ticker]: company-wide signals, trials, exec departures, insider trades w/ pre-planned flag, filings; cash runway placeholder until Week 3)
- [x] Week 2 step 6: Google sign-in + watchlist (Nov 9: works on phone; Google Cloud project owned by personal Gmail clivebeto222@gmail.com, published; /privacy and /terms pages added). Auth is client-side (lib/supabase-browser.ts) so public pages stay cached; /auth/callback route swaps the code for a session cookie.
- [x] Week 2 step 6 verified Nov 9: owner signed in on phone and starred a trial (row saved). Still to do: a classmate tries it.
- [x] Week 3 plan approved (Nov 9). Email "when this happened before" section omitted until Week 4 backtest. Domain purchase postponed to the end; until then Resend only delivers to the Resend account owner's email.
- [x] Week 3: cash runway (pipeline/tremor/runway.py, daily) + migration 006 written (profiles, alerts, deliveries, email_log, chat, jobs, layoffs, unsubscribe_by_token RPC)
- [x] Week 3: alert engine (alerts.py rules, emails.py render + Resend channel, alert_job.py; first run records 'baseline' alerts without emailing; test email via workflow input send_test_email) + /settings, /unsubscribe, /api/unsubscribe (one-click)
- [x] Week 3: migration 006 run (Nov 9); first alert run recorded 167 baseline tremors, emailed nobody
- [x] Domain live: https://www.tremoralerts.com (Vercel primary; apex redirects to www). Porkbun DNS: A @ 216.198.79.1, CNAME www, Resend records (resend._domainkey, send, rsend, _dmarc p=none); parking ALIAS/CNAME + URL forward deleted; Porkbun MX forwarding kept.
- [x] Google OAuth branding VERIFIED (Nov 9) via Search Console domain property for tremoralerts.com; consent screen shows "Tremor". Authorized domains: tremoralerts.com, qlzylutucbzuwhirodys.supabase.co (+ vercel.app).
- [x] Week 3: new domain wired into Supabase, Google sign-in, RESEND_API_KEY secret added. Nov 9: first REAL instant alert delivered (CLLS UCART22 main goal changed) + test preview, but FROM onboarding@resend.dev because Resend says tremoralerts.com is NOT verified yet. Code defaults to alerts@tremoralerts.com and falls back to the test sender while unverified (only reaches the Resend account owner).
- [x] Resend domain verified (Nov 9); test email sent from alerts@tremoralerts.com with no fallback. Emails can now reach anyone.
- [x] Week 3: money left on company pages (Nov 9). runway.py reads every cash label on the newest date and takes the largest (MAIA reported $0 under the usual label); site notes later S-1/S-3/424B5 filings ('may have more cash now'). 182/196 companies have data; 55 under 12 months (real: many small caps).
- [x] Week 3: AI chat (Nov 10): /api/chat route + AskBox on trial & company pages; signed-in only, 10/day (chat_questions), monthly budget via ai_calls, Tremor-data-only context (lib/server/chat-context.ts), number check + advice regex, one retry. Vercel env: ANTHROPIC_API_KEY + SUPABASE_SECRET_KEY as Secret.
- [x] Week 3: job boards (pipeline/data/job_boards.csv: 30 confirmed after checking job titles; 6 rejected as different companies: Aura, Crescent, Kodiak, Protagonist, Bolt, Innate) + state layoff notices (warn-scraper, 10 states, daily; Massachusetts blocks bots so it's excluded) + company page Hiring/Layoff sections. Job-drop signal needs ~2 weeks of daily counts before it can fire.
- [x] Layoff scraping verified in GitHub (Nov 10): 25,441 notices from 8 states; TX and CO scrapers broken upstream in warn-scraper (skipped automatically). Matching tightened after 3 wrong-company matches (Compass Group, Compass Inc., Obsidian); those rows + 1 un-emailed alert removed. Workflow input force_daily runs daily steps on demand.
- [x] Week 4: prices (Massive daily + Tiingo long history back to 2016, resumable at 50/hour), migrations 007 (prices) + 008 (past_events, backtest_cases, backtest_summary), backtest v1 (pipeline/tremor/backtest.py + backtest_job.py, smaller companies only). First result Nov 10: layoffs 12/92 and exec departures 23/177 followed by a trial stop within 12 months vs ~1 in 16 random dates (baseline needs per-company start fix). Price-move part NOT trustworthy yet (biggest-move-in-window picks unrelated jumps); next: find announcement day via EDGAR full-text search. Nothing published on the site yet.
- [x] Week 4: backtest v2 (Nov 10): announcement day = company 8-K that mentions the drug AND uses results/stop wording (SEC full-text search; earnings 8-Ks item 2.02 skipped; same announcement counted once); random-day comparison starts per company at first price; stop reasons ignore 'not related to safety'; future stop dates use last update. Tiingo history for 148/196 companies (rest are recent listings). Results: random month 8%; layoffs 11/90 (12%), exec departures 20/177 (11%) followed by a trial stop within 12 months. So only ~1.5x random, weaker than v1 suggested. Stock moves measurable for only 34 of 212 stops (typically about 0: most stops are business decisions); safety/efficacy stops measured 4 (e.g. SNGX -76%). Proposal: show price moves only with 10+ measured cases, else 'not enough cases yet'.
- [x] Week 4: upside/downside breakdown (Nov 10): pipeline/tremor/outlook.py writes fixed-template sentences (no AI) into trials.outlook (score_job, every run) and backtest_summary.extra.plain (backtest_job); migration 009 run. Trial pages: 'Upside and downside' section with dots (red diamond = trial stopped within a year, green circle = none), how sure, stakes, money left, when we'll find out. Emails: 'When this happened before' + 'How sure are we' rows. /track-record page: own alerts ('too early to tell' until Nov 2027) + 'If Tremor had existed' with every case + limits. Stock moves shown only with 10+ measured cases. backtest_job runs monthly (.github/workflows/backtest.yml, 2nd of each month 9:41 UTC, shares the pipeline lock; also "Run workflow" by hand; locally: python -m tremor.backtest_job ~5 min with cache).
- [x] Competitor upgrade 1: /upcoming calendar (Nov 10). pipeline/tremor/upcoming_job.py (daily) rebuilds upcoming_events (migration 010 run): FDA decision dates read by regex from companies' newest 8-K/10-Q/10-K (sources/fda_dates.py: date must come right AFTER 'PDUFA date'/'target action date'; dates a newer filing says were approved early are dropped), FDA advisory meetings, results due in next 6 months. First run: 24 FDA dates (all hand-checked), 169 results due. Nav: Trials · Upcoming (Companies + Track record in footer on phones).
- [x] Competitor upgrade 2: 'coming up' reminders (Nov 10). alerts.coming_up() makes kind='coming_up' alert rows from upcoming_events about 30 and 7 days before (month-only dates: when the month starts); one dedupe key per stage. Watchers only (trial or its company), daily digest, fixed wording (no AI), email block with the company's own words + money left + links. Created on daily runs in alert_job. Dry run Nov 10: 30 reminders due, 0 emails (no watcher of those yet). Settings text mentions reminders.
- [x] Competitor upgrade 3: before/after view of record edits (Nov 10). web/lib/diff.ts (word-level diff ignoring capitalization; main goals paired old->new by word overlap >= 0.4 into removed/reworded/added) + web/app/change-diff.tsx ('See exactly what changed' on trial pages only, for main-goal, patient-count and paperwork edits; dates/status already show before -> after in the headline). Patient counts explain planned -> final count. Paperwork shows edited sections in plain words (we don't store their text) + link to the official history.
- [x] Competitor upgrade 4: evidence-based weights (Nov 11, owner decided via 3 questions). layoffs 15->10, key_exec_departure 15->10 (each only ~1.5x a random day); NEW repeat_exec_departure +10 when a second key executive leaves within 182 days (backtest 5/20 = 1 in 4 vs 1 in 13; scoring.repeat_departure, also in backtest + outlook + track record). Layoffs+exec together did NOT predict more (5/58). Stopped trials stay red but the breakdown leads with the company's stated reason (whyStopped read from the latest snapshot by score_job, sorted by backtest.stop_reason) + typical move for that reason when 10+ cases (business stops: typically fell ~5%, 15 cases). Result: 202 scores lowered, 0 colors changed. Record-edit and insider weights unchanged until Tremor has its own history.
- [x] Week 5 (early): non-cancer cleanup + How the score works (Nov 11). clinicaltrials.is_cancer_trial (CANCER_TEXT + capital-only CANCER_CODES; keeps meningioma/schwannoma/neurofibroma/chemo side effects) applied in trials_job: 98 trials untracked (MS 'Secondary Progressive' matched 'metastatic' synonym, warts, HPV vaccines, myasthenia, eye disease...), 1,571 tracked. Home feed changes filter trials.tracked; calendar only for companies with tracked trials (21 FDA dates). /how-it-works page reads web/lib/score-rules.json, exported from config by `python -m tremor.export_rules` (test fails if out of sync: re-run after any weight change), plus evidence from backtest_summary. Linked from footer + trial pages.
- [x] Week 5: tap-to-learn + explainer (Nov 11). web/lib/glossary.ts (22 plain definitions, no statistics) + web/app/term.tsx (<Term id=...>: dotted underline, popup measured with documentElement.clientWidth in useLayoutEffect so it never runs off a phone screen; closes on outside tap/Escape) + /glossary page ('Words to know'). Terms placed on trial page (Phase, Patients, main goal), company page (Money left, insiders, 10b5-1, SEC filings, layoff notices, dilution), calendar (PDUFA, advisory meetings). /learn 'How biotech stocks move' (7 short steps; only Tremor's own numbers: Soligenix -76%, exec-departure fine count read live). Home links to the guide; footer links all explainer pages.
- [x] Week 5: Google search visibility + own icon (Nov 11). Next.js default 'N' favicon replaced (owner disliked it): app/icon.svg (three score-color bars, same as header), app/apple-icon.tsx (180px home-screen), app/opengraph-image.tsx (share card). Root metadata: metadataBase, title template '%s · Tremor', description; NO canonical/og:url in layout (it would leak to every page). Per-page titles/descriptions/canonicals; trial + company pages via generateMetadata (cached getTrial/getCompany) and must re-list images: '/opengraph-image' (page openGraph replaces the inherited one). app/sitemap.ts (1,754 URLs: pages + companies with tracked trials + tracked trials, lastModified = record's last update) via lib/sitemap-data.ts; app/robots.ts disallows /api /auth /settings /watchlist /unsubscribe (also noindex). Owner to submit sitemap in Search Console.
- [x] REDESIGN live (Nov 11; built on branch `redesign`, previewed on Vercel, owner said 'go live', fast-forwarded into main). Done: fonts Newsreader (serif headings) + IBM Plex Sans/Mono; palette white/cool gray #f5f7f9/navy ink #0b1626, navy footer #0d2240; score colors calm #18794e, shaky #d4900a marks + #8a5a00 text (BANDS.color vs .mark), tremor #b4232c (validated); max-w-6xl; sticky header; motion (link-grow, nudge, rise, scale slide-in) off under prefers-reduced-motion; app/ui.tsx SectionHead + Facts. Home slimmed after owner said it was crowded (intro + 3 calendar dates + 4 worries); Latest changes moved to new /changes page (nav 'Changes'). Every page converted: ruled lists instead of gray cards, serif titles, two columns on wide screens (trials list + score guide, companies table w/ money left, company page w/ side money/hiring/layoffs, calendar FDA | results, track record backtest | own alerts, glossary + learn side tables of contents), plain rectangular buttons. Emails restyled to match (emails.py _block_html). Pitfalls: grid columns need minmax(0,1fr)/grid-cols-1; hidden absolute popups must be display:none on phones. Vercel Preview env vars enabled Nov 11 (only the two NEXT_PUBLIC ones).
- [x] Tremor Weekly (Nov 11): pipeline/tremor/weekly.py (pure: week_bounds = last full Mon-Sun, facts_text, acceptable = has '## ' sections + no buy/sell/hold words, fallback_body written by code) + weekly_job.py (gather: important record changes, company-wide critical alerts, score rises >= 5, FDA dates + results due in next 14 days; ai.write essential=False with number check, 1 retry, else code fallback; upsert weekly_issues). Runs on daily runs, writes once per week. Migration 011 (weekly_issues). Site: /weekly (latest + 'All issues' side list) and /weekly/[week]; home link 'This week's roundup'; footer + sitemap. Company short names fixed (AstraZeneca, legal endings dropped).
- [x] Week 4: rival drugs (Nov 11). Migration 012 (drug_mechanisms, trial_profiles, rival_failures). sources/chembl.py (exact name/synonym match only; salts use parent; `approved` = max_phase 4) + sources/targets.py (~60 target word patterns, gene-symbol map, 21 cancer kinds, BACKBONE partner targets) + rivals_job.py (daily): 1,057/1,571 trials have targets (800 from ChEMBL, rest from record words); trial pages show 'Drug targets'. Rival failure = industry cancer trial stopped for safety/efficacy, dated by its END date (not a later record edit), within 365 days, counting only the NEW drug's targets (approved partners like pembrolizumab excluded; unknown drugs use record words minus BACKBONE). scoring.rival_signals: same target + same cancer kind + different drug, newest only, +10. First real result: 1 rival failure (SignalChem AXL, lung), 0 trials flagged. No AI mechanism guessing (spec's 'Claude labels unconfirmed' skipped: deliberate, explained to owner). Environment allows www.ebi.ac.uk + api.platform.opentargets.org. FIXES found on the way: backtest.stop_reason rewritten (GOAL_MISSED phrases checked first; negations now erase the rest of the sentence, e.g. 'not prompted by any safety or efficacy concerns'; bare 'safety'/'efficacy' no longer count) -> past stops re-sorted: safety/efficacy 26->22, business 88->93 (typically -4%, 16 cases); signal results unchanged. db._send retries dropped connections (a Supabase idle disconnect after the long ChEMBL step crashed the Nov 11 alert step; no alerts/emails were affected). A scheduled run at 06:48 used the first, buggy rival list: 576 fake score_history rows deleted.
- [x] Week 4: FDA approval history (Nov 11). Environment allows api.fda.gov (no key; ~100 requests/week, under the 1,000/day keyless cap). sources/openfda.py (core() name cleanup: FDA abbreviations PHARMS/THERAPS + legal endings; approved_medicines = NDA/BLA with ORIG AP, generics (ANDA) skipped) + approvals_job.py (weekly via run.py daily list, skips itself; `--scan` suggests names for new companies) + pipeline/data/fda_sponsors.csv (confirmed/suggested/rejected/none; exact core-name = auto-confirmed, others checked by hand: rejected MERCK KGAA, PRECISION DOSE etc., MAIA PHARMS (different company despite same name); added subsidiaries Janssen, Pharmacyclics, Seagen, Onyx, Celgene, Genzyme, GlaxoSmithKline, Altor, Loxo, MSD). Migration 013 (approved_medicines) run. First load: 42 companies, 1,238 approvals, 630 still sold. Company page side section 'FDA-approved medicines' (count on market, newest 6 + 'N more', brand versions folded together) + glossary term approved_medicine. outlook.stakes adds 'It also has N FDA-approved medicine(s) on the market, so this trial isn't its only hope.' for companies under 15 trials. NEVER claim 'no approved medicines': Drugs@FDA leaves out cell/gene therapies + vaccines (CBER), e.g. Iovance Amtagvi, Autolus Aucatzyl; page says 'None found in the FDA's drug database' + that note. CRL (rejection letter) data not used yet (idea: 'Why the FDA says no' on /learn).
- [x] Welcome email (Nov 11, owner asked). One template in pipeline/tremor/emails.py (welcome_template: {{GREETING}} + {{UNSUBSCRIBE_URL}}; what you'll get, get started links, settings, not-advice footer, unsubscribe + List-Unsubscribe header) exported with score rules to web/lib/welcome-email.json (`python -m tremor.export_rules`; test fails if out of sync; website/pipeline output verified identical). Website sends it right after sign-in: app/auth/callback/route.ts -> after(() => sendWelcome(userId)) in web/lib/server/welcome.ts (claims profiles.welcome_sent_at with PATCH ... is.null so nobody gets two; checks Resend daily/monthly limits from email_log; on failure releases the claim). Needs RESEND_API_KEY in Vercel (Secret). Backup: run.py 'welcome' step (alert_job.send_welcomes) every 4 hours sends any missed, gives up after 3 failed tries. email_log kind 'welcome'. Migration 014 (profiles.welcome_sent_at); the 2 people signed up before it get one too.
- [x] Welcome email verified (Nov 12): owner's sign-in got it from the website 1 second after sign-up (that was an accidental second Google account; deleted on request via Supabase admin API). The 2 earlier accounts get theirs from the pipeline backup.
- [x] Week 5: phone check (Nov 12). Playwright audit of 21 pages at 360px and 390px (scratchpad script: width overflow, text < 12px, tap targets < 24px): no page scrolls sideways. Fixed: `.tap` / `.tap-sm` CSS (invisible bigger touch area via ::after) on header nav, glossary terms, small source links, section 'See all' links, track-record ticker links; footer links inline-block py-2; home links py-2; calendar/home date labels 11.5px. Content bugs found on the way: AI summary of a stopped trial said 'the company hasn't said why' though whyStopped exists -> explain_job.facts_for now includes the stated reason (stated_reasons() reads latest snapshot) and the NVS summary was cleared to be rewritten; outlook.compare_words now says 'about 3 times as often' (was 'about twice ..., or more'), backtest plain text regenerated; fda_dates.quote stays inside the date's own sentence/bullet (Corcept quote ran into an unrelated quote).
- [x] 'When the FDA says no' (Nov 12): pipeline/tremor/crl.py sorts the FDA's 458 published complete response letters (openFDA /transparency/crl) by the FDA's own section headings (+ a few unmistakable phrases): making (factory inspection, product quality, device) vs evidence (clinical, nonclinical, statistics); safety-update + labeling sections ignored (routine). Writes web/lib/fda-letters.json (run `python -m tremor.crl` now and then and commit; not scheduled). Result: 305 making, 173 evidence, 91 both, 71 neither; 309/458 approved later; 146 of 149 not-yet-approved were sent 2024+. NO cancer-only stats: most unapproved letters lack the FDA office field, so office-based subsets are biased. /learn step 5 'When the FDA says no' (8 steps now) + glossary term crl; Learn 'Coming up' link renamed Calendar.
- [x] Cancer conference dates (Nov 12; spec: 'I'll enter these by hand'). pipeline/data/conferences.csv (name, starts, ends, city, about, url, confirmed, checked_from) loaded daily by upcoming_job.conferences() as kind='conference' (ticker NULL, end_date; only confirmed=yes, not over, within a year). Migration 015 (ticker nullable + end_date) run Nov 12; 6 conferences loaded. Calendar page section 'Big cancer conferences'; Weekly 'coming up' mentions them; reminders skip them (no company). Pre-filled from official sites Nov 12: SABCS Dec 8-11 2026, ASH Dec 12-15 2026, ASCO GI Jan 21-23 2027, ASCO GU Feb 11-13 2027 (moscone.com), AACR Apr 2-7 2027, ASCO Jun 4-8 2027; ESMO Sep 17-21 2027 confirmed=no (third-party only). Owner adds next year's dates by editing the CSV on GitHub.
- [x] Non-US company filings + readable AI dates (Nov 12, from the scrapped polish pass, data-only): sources/sec.KEEP_FORMS adds 6-K, 6-K/A, 20-F, 40-F, F-1, F-3 (backfilled 509 filings; web/lib/filings.ts names them; F-1/F-3 count as share sales in money-left). Key-executive departures from 6-Ks added the same day (see next entry). explain_job._nice gives Claude 'November 10, 2026' instead of '2026-11-10'; web tidyDates() fixes older summaries at render.
- [x] Key executives leaving non-US companies (Nov 12): sec_job.check_6k_departures reads each new 6-K's documents (cover + exhibits via the filing's index.json; skips index pages, the bundled .txt, R*.htm, files > 1.5 MB) with exec_changes.find_key_departure(text, whole=True): only news releases <= 30,000 chars (long reports retell old changes), stricter leaving words (resign/retire/step down/depart/will leave/transition out/will transition to|into; NOT 'separation'/'terminated'), sentences <= 350 chars (tables), no 'prior/former/previous' roles, plus succession ('named X as <key title>, succeeding Y'). score_job now reads 6-K + 8-K filings. Dry runs on 502 6-Ks: loose version 7 hits (6 false: tables, old news, 'separation from placebo'); final version 2 hits, both real (BNTX CMO Türeci, IPHA CMO Quaratino succeeded) -> recorded as BASELINE alerts (old news, no email). Lesson: whenever a back-fill creates signals for old events, insert their alerts as baseline before the next run, or everyone gets an instant 'critical' email.
- [x] Score tuning (Nov 12, owner chose via 3 questions): primary_outcome_changed 25->40 and enrollment_cut 15->40 (final-count cuts still x0.5), so either critical event shows Shaky on its own; insider_selling_cluster kept at 10 (untested). Why: before, 1,570 calm / 0 shaky / 1 tremor, and a 'critical' main-goal change showed green 'Calm 25' while its email was marked red. Simulated cutoffs 25/60 instead: also turned noise combos (layoffs + insider selling) yellow, so weights not cutoffs. Judgment call, not backtested (no record history before Nov 6). Result: GILD 40 + CLLS 48 shaky, PFE 39 (just under, points fading), REGN 34; history rows tagged reason 'scoring rule changed'; no jumps reached 15 so no alerts/emails. /how-it-works 'How the points were chosen' explains it; score-rules.json re-exported.
- [ ] Week 3 checkpoint: classmates sign up and receive alerts on their own (also completes Week 2 checkpoint)

## Design direction (owner feedback, Nov 11, 2026) — applies to ALL future UI work

The old site looked AI-built ("looks like every AI site with things switched around", compared with DataLookout). The owner wants it to feel human-designed, more like Goldman Sachs' site than a typical AI landing page. The Nov 11 redesign follows these rules; keep following them for all new UI. Owner also found the first redesigned home page too crowded: keep the home page short and move detail to its own tab.
- No "punchy" emphasis. Don't highlight words in color inside headlines (like red "cancer drug trials"), don't stack bold claims, don't put a gray subtitle under every heading, don't push every fact at the reader at once. Let hierarchy come from typography and layout, calmly.
- Use the screen. The narrow centered column (max-w-3xl) leaves about two-thirds of a desktop empty. Use wider, purposeful layouts (asymmetric grids, side columns, data shown at real density) while staying great on phones.
- New color scheme (owner dislikes the current stone/beige look). Keep green/yellow/red ONLY for the score meaning (spec requires Calm green / Shaky yellow / Tremor red, always with word + shape), but retune shades and build a more distinctive palette around them; re-validate contrast and colorblind safety.
- Break out of the generic AI template: fewer bordered rounded-xl cards and pill badges, no stat-tile row, no "New to X? ->" pill buttons, consider an editorial type pairing (serif display + clean sans) instead of default Geist everywhere.
- Small interactions make it feel crafted: subtle hover states, gentle transitions/animations, small hover/tap previews. Keep them quick and respect prefers-reduced-motion.
- Nov 12: owner REJECTED a 'polish' pass (branch `polish`, not merged) that swapped the mono uppercase labels for sentence case, removed the little → arrows and tightened spacing: 'made it more AI looking'. KEEP the current look as is: mono/uppercase small labels, the → arrows (incl. nudge), current spacing. Don't restyle without asking first.

## Notes for later weeks

- Choices beyond spec (in config, user OK'd by not objecting, Nov 6): big companies (15+ trials) get x0.5 on company-wide signals; final-count enrollment cuts get x0.5; 8-K item 2.05 counts as layoffs; only the most recent insider cluster per company counts.
- Week 2 scoring: an FDA meeting that matches only a company NAME (e.g. Novartis at a heart-drug panel) must not raise a cancer trial's score. Only count matches on the trial's own drug names.
- Week 2 scoring: most insider sales are pre-planned 10b5-1 trades (1,251 of 1,707 open-market sales on Nov 6). Only count the rest, per the spec.
- Enrollment changes from ESTIMATED to ACTUAL at the end of a trial are common; details store old_type/new_type so scoring can treat them more gently.
- Cloud session: the "tremor" environment allows clinicaltrials.gov, www.sec.gov, data.sec.gov, efts.sec.gov, www.federalregister.gov, plus the Supabase host via a saved credential. Run local scripts with SUPABASE_SECRET_KEY=sb_secret_proxy-injected (the proxy swaps in the real key).
- Big UI changes: build on a branch and share the Vercel preview (Preview env vars are enabled) before merging to main.
- Website (web/): Next.js 16 with Cache Components. Data functions use 'use cache' + cacheLife; anything reading searchParams/params sits inside <Suspense>; Date.now() only in client components (app/time-ago.tsx). Read web/node_modules/next/dist/docs before using new APIs. On this cloud machine run builds with NODE_USE_ENV_PROXY=1.
- Score colors validated with the dataviz palette checker (redesign, Nov 11): calm #18794e, shaky #d4900a (marks; #8a5a00 for text), tremor #b4232c (all pass). Always pair color with word + shape (circle/triangle/diamond). Chart band edges 40/70 are duplicated in web/app/score-chart.tsx; keep in sync with config/tremor.yaml.
- Domain: tremoralerts.com bought at Porkbun on Nov 9, 2026 (WHOIS privacy on, AUTO-RENEW OFF: expires Nov 9, 2027, renewal ~$11.81). Remind the owner before then.
- Google Search: sitemap + metadata done Nov 11. Search Console (verified domain property tremoralerts.com) -> Sitemaps -> https://www.tremoralerts.com/sitemap.xml. Favicon in Google results updates slowly. Nov 12: owner submitted the sitemap (full URL needed for a domain property; 'Couldn't fetch' at first, then Success, 1,757 pages discovered); home page already indexed ('URL is on Google').
- Privacy page promises account deletion within 7 days of an email request to clivebeto222@gmail.com (contact email in web/lib/site.ts).
- GitHub Actions sometimes fails to start a run ("Internal server error", 0 jobs). That's GitHub's side; the next run works. Not a Tremor bug.
- DATA SOURCE CHANGES (Nov 10, verified by testing): DROPPED cthist + ClinicalTrials.gov record history (history API returns 403 to automated clients); AACT snapshots (login-only, GB-sized; optional manual later); Massachusetts WARN (mass.gov returns 'Not allowed' to bots; don't work around); Financial Modeling Prep (free plan no longer covers small-cap tickers, legacy v3 closed to new accounts). Massive (Polygon) is now the main price source (free key, 5 calls/min; grouped-daily endpoint = 1 call per day for all US stocks); Tiingo is the fallback if Massive's free history is too short. warn-scraper covers PA now, not NC; TX and CO scrapers broken upstream. Backtest Part A only (SEC signals + trial stops); record-edit signals show 'not enough past cases yet' and build Tremor's own history from Nov 6, 2026.
- Supabase free plan: 500 MB data limit (Nov 10: 62 MB used; RAM ~59% is normal Postgres caching on Nano). Biggest growth = trial_snapshots. If database passes ~350 MB, add cleanup that keeps only the newest + change-linked snapshots. Nov 12 check: snapshots are saved only when a record changes: 1,842 rows (~39 KB each before compression), growing ~30/day (~1 MB/day raw, less after Postgres compression); prices 336k rows (+~200/day). Estimate: well under 350 MB for about a year. Re-check the real size in Supabase (Project Settings -> Usage) about monthly.
- The Federal Register's full-text pages block bots; use the API's search (conditions[term]) instead.
- COMPETITORS (researched Nov 10): catalyst calendars (RTTNews, BiopharmaWatch, Fintel, BioPharmCatalyst w/ AI chatbot), trial-record diff tools (DataLookout $29/mo, Apify actors), prediction platforms (CatalystAlert claims 77.8% unverified; ClinicalTrialRank; GATC Derisq; AppliedXL+Bain for pharma). Tremor's edge: beginners, plain English, free, combines record edits + company signals, publishes its misses, no 'probability' claims. Plan to learn from them (owner said 'make it better than all of them'): 1) Upcoming calendar (FDA decision dates read by regex from filings, advisory meetings, results due) 2) 'coming up' watchlist emails 3) clearer before/after view of record edits 4) evidence-based weights.
- FUTURE SUBSCRIPTION (~$15/mo, owner's idea Nov 10; not now). Before charging: Vercel Hobby is non-commercial only (needs Pro ~$20/mo); Tiingo + Massive free data are personal-use (need commercial data plans); Resend free 3,000/mo cap; Supabase free pauses idle projects; investment-adviser rules: Tremor relies on being an impersonal publication (same content for everyone, no personal advice), so get a lawyer/school business clinic to confirm; payments (Stripe), refunds, taxes, updated Terms. Budget ~$50-100/mo running costs once paid. Strongest selling point = a real track record.
