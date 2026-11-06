-- =====================================================================
-- Tremor — Week 1 database layout
-- Paste this whole file into Supabase → SQL Editor → Run.
-- Safe to run more than once ("if not exists" everywhere).
-- =====================================================================

-- ---------- Companies we track (one row per stock ticker) ----------
create table if not exists companies (
  ticker        text primary key,              -- e.g. 'MRNA'
  name          text not null,                 -- official SEC name
  cik           text not null,                 -- SEC's ID number, 10 digits with leading zeros
  created_at    timestamptz not null default now()
);

-- ---------- Sponsor name → ticker lookup (synced from pipeline/data/sponsor_tickers.csv) ----------
-- Only rows with confirmed = true are used for tracking and alerts.
create table if not exists sponsor_tickers (
  sponsor_name  text primary key,              -- exactly as ClinicalTrials.gov spells it
  ticker        text references companies(ticker),
  confirmed     boolean not null default false,-- YOU confirm each match
  match_score   real,                          -- how confident the auto-matcher was (0-1)
  notes         text,
  updated_at    timestamptz not null default now()
);

-- ---------- Trials (the latest known version of each one) ----------
create table if not exists trials (
  nct_id                   text primary key,   -- ClinicalTrials.gov ID, e.g. 'NCT01234567'
  title                    text,
  sponsor_name             text,
  ticker                   text references companies(ticker),
  phases                   text[],             -- e.g. {PHASE2,PHASE3}
  overall_status           text,               -- RECRUITING, COMPLETED, TERMINATED...
  conditions               text[],             -- cancers studied
  interventions            text[],             -- drug names / codes
  primary_outcomes         jsonb,              -- the trial's main goal(s)
  enrollment               integer,            -- number of patients
  enrollment_type          text,               -- ESTIMATED or ACTUAL
  start_date               text,               -- kept as text: CT.gov dates are sometimes just "2026-03"
  primary_completion_date  text,
  completion_date          text,
  results_first_posted     text,
  last_update_posted       text,
  tracked                  boolean not null default false, -- true once sponsor is confirmed
  first_seen_at            timestamptz not null default now(),
  last_checked_at          timestamptz not null default now()
);
create index if not exists trials_ticker_idx on trials(ticker);

-- ---------- Snapshots: a saved copy of a trial's full record ----------
-- To stay inside the free 500 MB, we only save a new snapshot when the record actually changed
-- (detected by content_hash, a fingerprint of the record).
create table if not exists trial_snapshots (
  id                  bigint generated always as identity primary key,
  nct_id              text not null references trials(nct_id) on delete cascade,
  fetched_at          timestamptz not null default now(),
  last_update_posted  text,
  content_hash        text not null,
  data                jsonb not null,
  unique (nct_id, content_hash)
);
create index if not exists trial_snapshots_nct_idx on trial_snapshots(nct_id, fetched_at desc);

-- ---------- Changes found by comparing two snapshots ----------
create table if not exists trial_changes (
  id                  bigint generated always as identity primary key,
  nct_id              text not null references trials(nct_id) on delete cascade,
  detected_at         timestamptz not null default now(),
  change_type         text not null,           -- e.g. 'primary_outcome_changed', 'enrollment_cut', 'date_delayed', 'status_changed', 'paperwork'
  field               text,                    -- which part of the record changed
  old_value           jsonb,
  new_value           jsonb,
  is_paperwork        boolean not null default false, -- harmless edits (typos, contact info...)
  details             jsonb,                   -- extra numbers, e.g. {"percent_cut": 20}
  snapshot_before_id  bigint references trial_snapshots(id),
  snapshot_after_id   bigint references trial_snapshots(id)
);
create index if not exists trial_changes_nct_idx on trial_changes(nct_id, detected_at desc);
create index if not exists trial_changes_recent_idx on trial_changes(detected_at desc);

-- ---------- SEC filings (8-Ks, Form 4s, 10-Qs...) ----------
create table if not exists sec_filings (
  accession_number  text primary key,          -- SEC's unique ID for a filing
  ticker            text not null references companies(ticker),
  form              text not null,             -- '8-K', '4', '10-Q'...
  filed_at          date not null,
  items             text[],                    -- 8-K item codes, e.g. {5.02}
  url               text,
  description       text,
  created_at        timestamptz not null default now()
);
create index if not exists sec_filings_ticker_idx on sec_filings(ticker, filed_at desc);

-- ---------- Insider trades (one row per transaction line in a Form 4) ----------
create table if not exists insider_trades (
  id                bigint generated always as identity primary key,
  accession_number  text not null,
  line_number       integer not null,
  ticker            text not null references companies(ticker),
  insider_name      text,
  insider_title     text,
  is_officer        boolean,
  is_director       boolean,
  transaction_date  date,
  transaction_code  text,                      -- 'S' = sale on the market, 'P' = purchase...
  shares            numeric,
  price             numeric,
  acquired_disposed text,                      -- 'A' (got shares) or 'D' (gave up shares)
  is_10b5_1         boolean,                   -- pre-planned trade? (checkbox since April 2023)
  url               text,
  unique (accession_number, line_number)
);
create index if not exists insider_trades_ticker_idx on insider_trades(ticker, transaction_date desc);

-- ---------- FDA advisory committee meetings (from the Federal Register) ----------
create table if not exists fda_meetings (
  document_number   text primary key,
  title             text,
  publication_date  date,
  meeting_date      date,
  abstract          text,
  url               text,
  matched_drugs     text[],                    -- drug names we found that match our trials
  matched_tickers   text[],
  created_at        timestamptz not null default now()
);

-- ---------- Log of every pipeline run ----------
create table if not exists pipeline_runs (
  id           bigint generated always as identity primary key,
  started_at   timestamptz not null default now(),
  finished_at  timestamptz,
  status       text not null default 'running', -- running / success / failed
  stats        jsonb,                           -- counts, e.g. {"trials_fetched": 2400}
  error        text
);

-- =====================================================================
-- Security ("Row Level Security"): everyone can READ, nobody can WRITE
-- from the website. Only the pipeline (using the secret service-role key)
-- can write, because that key skips these rules.
-- =====================================================================
do $$
declare t text;
begin
  foreach t in array array['companies','sponsor_tickers','trials','trial_snapshots',
                           'trial_changes','sec_filings','insider_trades','fda_meetings','pipeline_runs']
  loop
    execute format('alter table %I enable row level security', t);
    execute format('drop policy if exists "public read" on %I', t);
    execute format('create policy "public read" on %I for select using (true)', t);
  end loop;
end $$;
