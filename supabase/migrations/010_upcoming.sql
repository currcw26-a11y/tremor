-- "Upcoming" calendar, refreshed daily by pipeline/tremor/upcoming_job.py:
--   fda_decision  FDA decision dates that companies announced in their own SEC filings
--   fda_meeting   FDA advisory committee meetings that mention one of the company's drugs
--   results_due   tracked trials whose main results are expected soon (the company's own estimate)
create table if not exists upcoming_events (
  id              bigint generated always as identity primary key,
  kind            text not null,
  ticker          text not null references companies(ticker) on delete cascade,
  nct_id          text references trials(nct_id) on delete cascade,
  event_date      date not null,
  date_precision  text not null,           -- 'day' or 'month' (only a month was given)
  title           text,
  quote           text,                    -- for FDA decisions: the company's own words around the date
  source_url      text,
  source_form     text,
  filed_at        date,
  dedupe_key      text not null unique,
  updated_at      timestamptz not null default now()
);
create index if not exists upcoming_events_date_idx on upcoming_events(event_date);
alter table upcoming_events enable row level security;
drop policy if exists "public read" on upcoming_events;
create policy "public read" on upcoming_events for select using (true);
