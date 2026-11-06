# Tremor 🔴🟡🟢

**An early warning system for biotech stocks.** "The Pentagon pizza index, but for cancer drug trials."

Tremor watches public data about cancer drug trials (ClinicalTrials.gov, SEC filings, FDA notices),
gives each trial a 0–100 worry score, and emails users in plain English when something looks off.

> **Not investment advice.** Tremor shows what changed and what happened in similar past cases.
> It never tells anyone to buy or sell.

Built for a first-year seminar on fintech and big data.

## How it's organized

| Folder | What's in it |
|---|---|
| `pipeline/` | Python data collector. Runs every 4 hours on GitHub Actions. |
| `web/` | The website (Next.js + Tailwind), hosted on Vercel. |
| `supabase/` | The database layout (SQL). |
| `config/` | Score weights, color cutoffs, and alert rules, all in one file. |
| `CLAUDE.md` | The full project spec and progress checklist. |

## Secrets

Copy `.env.example` to `.env.local` and fill in real values. `.env.local` is never committed.
In the cloud, the same values go in **GitHub Actions secrets** (pipeline) and **Vercel environment variables** (website).

## ⏰ Reminder: GitHub's 60-day rule

GitHub turns off scheduled workflows in public repos after **60 days with no commits**.
If Tremor is still running after that, push any small commit (even a README edit) at least once a month,
or re-enable the workflow under the repo's **Actions** tab.
