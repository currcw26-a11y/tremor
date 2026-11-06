-- Tremor — Week 2: Claude explanations + cost tracking

-- Each important change gets one explanation, written once and reused forever (that's the "cache").
alter table trial_changes add column if not exists explanation text;
alter table trial_changes add column if not exists explanation_model text;

-- Every Claude call is logged with its tokens and estimated cost, for the monthly budget cap.
create table if not exists ai_calls (
  id             bigint generated always as identity primary key,
  created_at     timestamptz not null default now(),
  purpose        text not null,             -- 'explanation', 'chat', 'weekly'...
  model          text not null,
  input_tokens   integer not null default 0,
  output_tokens  integer not null default 0,
  cost_usd       numeric(10, 6) not null default 0,
  ok             boolean not null default true,
  note           text                       -- e.g. 'number check failed', error message
);
create index if not exists ai_calls_month_idx on ai_calls(created_at desc);

-- Costs are private: security rules ON with no public read rule, so only the pipeline can see them.
alter table ai_calls enable row level security;
