import json

from tremor import export_rules


def test_website_shows_the_same_rules_as_the_config():
    # If this fails: run `python -m tremor.export_rules` (in pipeline/) and commit web/lib/score-rules.json
    assert json.loads(export_rules.OUT.read_text()) == export_rules.rules()
