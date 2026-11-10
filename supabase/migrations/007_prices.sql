-- Tremor — Week 4: daily closing prices (public), used to measure how stocks moved on news days.
create table if not exists prices (
  ticker  text not null references companies(ticker) on delete cascade,
  day     date not null,
  close   numeric not null,
  primary key (ticker, day)
);
create index if not exists prices_day_idx on prices(day);
alter table prices enable row level security;
drop policy if exists "public read" on prices;
create policy "public read" on prices for select using (true);
