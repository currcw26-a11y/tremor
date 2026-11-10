-- Tremor — Week 4: the backtest ("when this happened before").
-- Public: the whole point is to show the evidence.

-- Things that happened to companies in the past: trial stopped / ran to completion, FDA decisions,
-- and the warning signs (insider selling, executives leaving, layoffs) we test.
create table if not exists past_events (
  id          bigint generated always as identity primary key,
  ticker      text not null references companies(ticker) on delete cascade,
  kind        text not null,      -- 'trial_stopped', 'trial_completed', 'layoffs', 'key_exec_departure', 'insider_selling_cluster'
  day         date not null,      -- when it happened (our best estimate)
  nct_id      text,               -- the trial, if it's about one
  detail      text,               -- e.g. the reason a trial was stopped
  stop_reason text,               -- 'safety_or_efficacy', 'business', 'enrollment', 'other' (stopped trials only)
  source_url  text,
  dedupe_key  text not null unique
);
create index if not exists past_events_ticker_idx on past_events(ticker, day);

-- One row per past warning sign, with what happened next (code-computed)
create table if not exists backtest_cases (
  id           bigint generated always as identity primary key,
  signal_type  text not null,
  ticker       text not null references companies(ticker) on delete cascade,
  signal_day   date not null,
  outcome      text not null,     -- 'bad' (a trial stopped within the window), 'fine', 'unknown' (too recent to tell)
  news_day     date,              -- the day the outcome became public (biggest stock move near it)
  move_pct     numeric,           -- close the day before news -> close the day after, in percent
  detail       text,
  unique (signal_type, ticker, signal_day)
);
create index if not exists backtest_cases_type_idx on backtest_cases(signal_type);

-- The summary the site shows ("9 of 14 went badly; typically fell about half")
create table if not exists backtest_summary (
  signal_type      text primary key,
  cases            integer not null,  -- resolved cases (bad + fine)
  bad              integer not null,
  fine             integer not null,
  typical_bad_move numeric,           -- median % move on the news day when it went badly
  typical_fine_move numeric,
  baseline_bad_share numeric,         -- how often bad news follows ANY random day, for comparison
  confidence       text not null,     -- 'low' (<10), 'medium' (10-29), 'high' (30+)
  computed_at      timestamptz not null default now(),
  notes            text
);

do $$
declare t text;
begin
  foreach t in array array['past_events', 'backtest_cases', 'backtest_summary'] loop
    execute format('alter table %I enable row level security', t);
    execute format('drop policy if exists "public read" on %I', t);
    execute format('create policy "public read" on %I for select using (true)', t);
  end loop;
end $$;
