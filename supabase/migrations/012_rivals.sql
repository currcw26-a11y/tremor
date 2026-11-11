-- Rival drugs: what each trial's drug targets, and recent rival trials that failed (pipeline/tremor/rivals_job.py)
create table if not exists drug_mechanisms (       -- one row per drug name we've looked up (so we look it up once)
  name_norm   text primary key,
  name        text not null,
  chembl_id   text,                                -- null = not found in ChEMBL
  pref_name   text,
  targets     text[] not null default '{}',        -- plain target names, e.g. {PD-1}
  mechanism   text,
  checked_at  timestamptz not null default now()
);
create table if not exists trial_profiles (        -- what each tracked trial's drugs target, and its kind of cancer
  nct_id        text primary key references trials(nct_id) on delete cascade,
  targets       text[] not null default '{}',
  target_source jsonb,                             -- target -> 'chembl' or 'record' (named in the trial record)
  drug_ids      text[] not null default '{}',
  cancer_types  text[] not null default '{}',
  updated_at    timestamptz not null default now()
);
create table if not exists rival_failures (        -- industry cancer trials stopped in the last year because the drug didn't work or wasn't safe
  nct_id        text primary key,
  sponsor       text,
  title         text,
  why_stopped   text,
  stopped_on    date not null,
  targets       text[] not null default '{}',
  cancer_types  text[] not null default '{}',
  drug_ids      text[] not null default '{}',
  updated_at    timestamptz not null default now()
);
do $$ declare t text; begin
  foreach t in array array['drug_mechanisms', 'trial_profiles', 'rival_failures'] loop
    execute format('alter table %I enable row level security', t);
    execute format('drop policy if exists "public read" on %I', t);
    execute format('create policy "public read" on %I for select using (true)', t);
  end loop;
end $$;
