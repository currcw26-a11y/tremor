-- Week 4: the upside/downside breakdown ("When this happened before")
alter table backtest_summary
  add column if not exists bad_moves int,    -- how many bad-news cases had a measurable stock move
  add column if not exists fine_moves int,
  add column if not exists extra jsonb;      -- e.g. trial stops by reason
alter table trials add column if not exists outlook jsonb;  -- computed by the pipeline (pipeline/tremor/outlook.py)
