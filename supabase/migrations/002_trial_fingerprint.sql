-- Tremor — Step 5: remember each trial's latest fingerprint, so a run only has to
-- download the old full record when a trial actually changed.
alter table trials add column if not exists content_hash text;
alter table trials add column if not exists latest_snapshot_id bigint references trial_snapshots(id);
