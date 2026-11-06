-- Tremor — Week 2: watchlists (stars). Each signed-in person can only see and change their OWN rows.

create table if not exists watch_trials (
  user_id    uuid not null default auth.uid() references auth.users(id) on delete cascade,
  nct_id     text not null references trials(nct_id) on delete cascade,
  created_at timestamptz not null default now(),
  primary key (user_id, nct_id)
);

create table if not exists watch_companies (
  user_id    uuid not null default auth.uid() references auth.users(id) on delete cascade,
  ticker     text not null references companies(ticker) on delete cascade,
  created_at timestamptz not null default now(),
  primary key (user_id, ticker)
);

do $$
declare t text;
begin
  foreach t in array array['watch_trials', 'watch_companies'] loop
    execute format('alter table %I enable row level security', t);
    execute format('drop policy if exists "own rows: read" on %I', t);
    execute format('drop policy if exists "own rows: add" on %I', t);
    execute format('drop policy if exists "own rows: remove" on %I', t);
    execute format('create policy "own rows: read" on %I for select to authenticated using (auth.uid() = user_id)', t);
    execute format('create policy "own rows: add" on %I for insert to authenticated with check (auth.uid() = user_id)', t);
    execute format('create policy "own rows: remove" on %I for delete to authenticated using (auth.uid() = user_id)', t);
  end loop;
end $$;
