-- Tremor — Week 2: worry scores
-- Current score lives on each trial; every meaningful score change is saved in score_history
-- together with the signals behind it, so the site can show exactly why a score moved.

alter table trials add column if not exists score integer not null default 0;
alter table trials add column if not exists score_label text not null default 'calm';
alter table trials add column if not exists score_breakdown jsonb;
alter table trials add column if not exists score_updated_at timestamptz;
create index if not exists trials_score_idx on trials(score desc);

create table if not exists score_history (
  id            bigint generated always as identity primary key,
  nct_id        text not null references trials(nct_id) on delete cascade,
  computed_at   timestamptz not null default now(),
  old_score     integer,
  new_score     integer not null,
  old_label     text,
  new_label     text not null,
  breakdown     jsonb not null,           -- the signals and their points at this moment
  reason        text                      -- e.g. 'new signal', 'points faded'
);
create index if not exists score_history_nct_idx on score_history(nct_id, computed_at desc);
create index if not exists score_history_recent_idx on score_history(computed_at desc);

-- 8-K item 5.02 covers people joining AND leaving. We read the text and store what we found.
alter table sec_filings add column if not exists key_exec_departure boolean;
alter table sec_filings add column if not exists departure_details text;

alter table score_history enable row level security;
drop policy if exists "public read" on score_history;
create policy "public read" on score_history for select using (true);
