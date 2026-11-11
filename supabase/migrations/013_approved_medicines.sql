-- Medicines each tracked company already has FDA approval for (pipeline/tremor/approvals_job.py, weekly, openFDA Drugs@FDA)
create table if not exists approved_medicines (
  application_number text primary key,             -- e.g. NDA208692 or BLA125514
  ticker             text not null references companies(ticker) on delete cascade,
  sponsor_name       text not null,                -- the FDA's name for the company (pipeline/data/fda_sponsors.csv)
  brand_name         text not null,
  ingredient         text,
  approved_on        date not null,                -- first approval of the original application
  still_sold         boolean not null default true,
  updated_at         timestamptz not null default now()
);
create index if not exists approved_medicines_ticker on approved_medicines (ticker);
alter table approved_medicines enable row level security;
drop policy if exists "public read" on approved_medicines;
create policy "public read" on approved_medicines for select using (true);
