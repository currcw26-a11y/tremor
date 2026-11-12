"""Tests for the Claude safety nets (no real Claude calls)."""
from types import SimpleNamespace

from tremor import ai, explain_job


def test_numbers_are_found():
    assert ai.numbers_in("Cut from 1,200 to 960 patients (20%) by 2027, phase 2.5") == {"1200", "960", "20", "2027", "2.5"}


def test_invented_numbers_are_caught():
    facts = "The planned number of patients went from 300 to 240 (20% fewer). Stage: Phase 3"
    assert ai.invented_numbers("They cut patients from 300 to 240, a 20% drop.", facts) == set()
    assert ai.invented_numbers("A 20% cut like this fails 64% of the time.", facts) == {"64"}


def test_cost_math():
    assert round(ai.cost(1_000_000, 0), 2) == 0.10
    assert round(ai.cost(0, 1_000_000), 2) == 0.50


class FakeClaude:
    def __init__(self, text):
        self.text = text
        self.messages = self

    def create(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(stop_reason="end_turn",
                               content=[SimpleNamespace(type="thinking"), SimpleNamespace(type="text", text=self.text)],
                               usage=SimpleNamespace(input_tokens=500, output_tokens=100))


def setup(monkeypatch, text, spent=0.0):
    fake = FakeClaude(text)
    logged = []
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    monkeypatch.setattr(ai, "_client", fake)
    monkeypatch.setattr(ai, "_spent_before_run", spent)
    monkeypatch.setattr(ai, "_spent_this_run", 0.0)
    monkeypatch.setattr(ai.db, "insert", lambda table, rows, returning=None: logged.extend(rows))
    return fake, logged


def test_good_answer_is_kept_and_logged(monkeypatch):
    fake, logged = setup(monkeypatch, "The company cut patients from 300 to 240.")
    out = ai.write("explanation", "sys", "from 300 to 240", essential=True)
    assert out == "The company cut patients from 300 to 240."
    assert fake.kwargs["model"] == "claude-haiku-5-5"
    assert logged[0]["ok"] is True and logged[0]["cost_usd"] > 0


def test_answer_with_made_up_number_is_rejected(monkeypatch):
    _, logged = setup(monkeypatch, "Trials like this fail 64% of the time.")
    assert ai.write("explanation", "sys", "from 300 to 240", essential=True) is None
    assert logged[0]["ok"] is False and "64" in logged[0]["note"]


def test_over_budget_skips_non_essential(monkeypatch):
    setup(monkeypatch, "ok", spent=ai.BUDGET_USD + 1)
    assert ai.write("chat", "sys", "facts", essential=False) is None
    assert ai.write("explanation", "sys", "facts", essential=True) == "ok"


def test_no_key_means_ai_is_off(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert ai.write("explanation", "sys", "facts", essential=True) is None


def test_facts_contain_the_numbers_claude_needs():
    change = {"change_type": "date_delayed", "field": "primary_completion_date", "old_value": "2027-07-05",
              "new_value": "2030-04-02", "details": {"months": 32.9}}
    trial = {"sponsor_name": "Amgen", "ticker": "AMGN", "title": "Study X", "phases": ["PHASE3"],
             "conditions": ["Lung Cancer"], "overall_status": "RECRUITING", "enrollment": 400}
    facts = explain_job.facts_for(change, trial)
    assert "about 33 months later" in facts and "April 2, 2030" in facts and "Phase 3" in facts


def test_stopped_trial_facts_include_the_companys_stated_reason():
    change = {"change_type": "trial_stopped", "old_value": "RECRUITING", "new_value": "TERMINATED"}
    trial = {"sponsor_name": "X", "ticker": "X", "title": "T", "phases": ["PHASE3"], "conditions": [], "enrollment": 5}
    assert 'stated reason for stopping, from the trial record: "Business reasons"' in explain_job.facts_for(change, trial, "Business reasons")
    assert "gives no reason" in explain_job.facts_for(change, trial, None)
