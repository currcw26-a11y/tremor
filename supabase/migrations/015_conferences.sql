-- Big cancer conferences on the calendar (from pipeline/data/conferences.csv, which the owner edits by hand).
-- A conference isn't about one company, so the calendar's ticker can now be empty; end_date holds the last day.
alter table upcoming_events alter column ticker drop not null;
alter table upcoming_events add column if not exists end_date date;
