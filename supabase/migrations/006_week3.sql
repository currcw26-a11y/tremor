-- =====================================================================
-- Tremor — Week 3: money left, alert settings, alerts, email log, chat, jobs, layoffs
-- One paste: Supabase → SQL Editor → New query → Run. Safe to run twice.
-- =====================================================================

-- ---------- Money left (from SEC financial reports) ----------
alter table companies add column if not exists cash_usd numeric;            -- cash + short-term investments
alter table companies add column if not exists monthly_burn_usd numeric;    -- cash used by operations per month (positive = spending)
alter table companies add column if not exists runway_months numeric;       -- cash / monthly burn; null if not burning cash
alter table companies add column if not exists finances_as_of date;         -- date of the balance sheet
alter table companies add column if not exists burn_period_months numeric;  -- how many months the spending rate covers
alter table companies add column if not exists finances_form text;          -- e.g. 10-Q

-- ---------- Each signed-in person's alert settings ----------
create table if not exists profiles (
  user_id           uuid primary key references auth.users(id) on delete cascade,
  email             text not null,
  name              text,
  instant_alerts    boolean not null default true,
  daily_digest      boolean not null default true,
  unsubscribed      boolean not null default false,   -- one-click unsubscribe turns off everything
  unsubscribe_token uuid not null default gen_random_uuid() unique,
  created_at        timestamptz not null default now()
);
alter table profiles enable row level security;
drop policy if exists "own profile: read" on profiles;
drop policy if exists "own profile: change" on profiles;
create policy "own profile: read" on profiles for select to authenticated using (auth.uid() = user_id);
create policy "own profile: change" on profiles for update to authenticated using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- Create a profile automatically when someone signs in for the first time
create or replace function public.create_profile_for_new_user() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  insert into public.profiles (user_id, email, name)
  values (new.id, new.email, coalesce(new.raw_user_meta_data->>'full_name', new.raw_user_meta_data->>'name'))
  on conflict (user_id) do nothing;
  return new;
end $$;
drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created after insert on auth.users
  for each row execute function public.create_profile_for_new_user();
-- Profiles for people who already signed in
insert into profiles (user_id, email, name)
select id, email, coalesce(raw_user_meta_data->>'full_name', raw_user_meta_data->>'name') from auth.users
on conflict (user_id) do nothing;

-- ---------- Tremors (alert-worthy events). Public: the site can show them. ----------
create table if not exists alerts (
  id           bigint generated always as identity primary key,
  nct_id       text not null references trials(nct_id) on delete cascade,
  ticker       text,
  detected_at  timestamptz not null default now(),
  kind         text not null,              -- 'critical', 'big_jump', 'head_start'
  is_huge      boolean not null default false,  -- goes to everyone, not just watchers
  instant      boolean not null default false,  -- email right away vs. daily digest
  headline     text not null,              -- code-written fact sentence
  explanation  text,                       -- Claude-written, checked
  old_score    integer,
  new_score    integer,
  details      jsonb,                      -- links and facts for the email
  dedupe_key   text not null unique        -- so the same event is never alerted twice
);
create index if not exists alerts_recent_idx on alerts(detected_at desc);
alter table alerts enable row level security;
drop policy if exists "public read" on alerts;
create policy "public read" on alerts for select using (true);

-- ---------- Who was sent what (private) ----------
create table if not exists alert_deliveries (
  user_id   uuid not null references auth.users(id) on delete cascade,
  alert_id  bigint not null references alerts(id) on delete cascade,
  channel   text not null default 'email',  -- room for 'sms' later
  mode      text not null,                  -- 'instant' or 'digest'
  status    text not null default 'pending',-- 'pending', 'sent', 'skipped'
  sent_at   timestamptz,
  primary key (user_id, alert_id, channel)
);
alter table alert_deliveries enable row level security;

-- One row per email actually sent, to stay under Resend's free limits (private)
create table if not exists email_log (
  id         bigint generated always as identity primary key,
  sent_at    timestamptz not null default now(),
  kind       text not null,                  -- 'instant', 'digest', 'test'
  user_id    uuid references auth.users(id) on delete set null,
  provider_id text,
  ok         boolean not null default true,
  note       text
);
create index if not exists email_log_sent_idx on email_log(sent_at desc);
alter table email_log enable row level security;

-- ---------- AI chat questions (each person sees only their own) ----------
create table if not exists chat_questions (
  id        bigint generated always as identity primary key,
  user_id   uuid not null references auth.users(id) on delete cascade,
  asked_at  timestamptz not null default now(),
  question  text not null,
  answer    text,
  nct_id    text,
  ticker    text
);
create index if not exists chat_questions_user_idx on chat_questions(user_id, asked_at desc);
alter table chat_questions enable row level security;
drop policy if exists "own questions: read" on chat_questions;
create policy "own questions: read" on chat_questions for select to authenticated using (auth.uid() = user_id);

-- ---------- Job postings and layoff notices (public) ----------
create table if not exists job_boards (
  ticker    text primary key references companies(ticker) on delete cascade,
  provider  text not null,     -- 'greenhouse', 'lever', 'ashby'
  board     text not null,     -- the company's board name on that site
  confirmed boolean not null default false
);
create table if not exists job_counts (
  ticker        text not null references companies(ticker) on delete cascade,
  day           date not null,
  total_jobs    integer not null,
  clinical_jobs integer not null,
  primary key (ticker, day)
);
create table if not exists layoff_notices (
  id          bigint generated always as identity primary key,
  ticker      text references companies(ticker) on delete cascade,
  state       text not null,
  company_name text not null,
  notice_date date,
  employees   integer,
  location    text,
  source      text,
  dedupe_key  text not null unique,
  created_at  timestamptz not null default now()
);
do $$
declare t text;
begin
  foreach t in array array['job_boards', 'job_counts', 'layoff_notices'] loop
    execute format('alter table %I enable row level security', t);
    execute format('drop policy if exists "public read" on %I', t);
    execute format('create policy "public read" on %I for select using (true)', t);
  end loop;
end $$;
