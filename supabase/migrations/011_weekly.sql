-- Tremor Weekly: one short roundup per week, written from that week's data (pipeline/tremor/weekly_job.py)
create table if not exists weekly_issues (
  week_start  date primary key,          -- Monday the week began
  week_end    date not null,             -- the Sunday it ended
  title       text not null,
  body        text not null,             -- plain text; lines starting "## " are section titles, "- " are bullets
  written_by  text not null,             -- 'ai' (checked by code) or 'code' (fallback list)
  facts       jsonb,                     -- exactly what the writer was given
  created_at  timestamptz not null default now()
);
alter table weekly_issues enable row level security;
drop policy if exists "public read" on weekly_issues;
create policy "public read" on weekly_issues for select using (true);
