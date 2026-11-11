-- Welcome email: when it was sent (set BEFORE sending, so nobody ever gets two).
-- The website sends it right after someone first signs in; the pipeline sends any it missed.
-- The 2 people already signed up get one too (left empty here on purpose).
alter table profiles add column if not exists welcome_sent_at timestamptz;
