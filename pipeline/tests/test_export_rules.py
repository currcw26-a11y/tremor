import json

from tremor import export_rules


def test_website_shows_the_same_rules_as_the_config():
    # If this fails: run `python -m tremor.export_rules` (in pipeline/) and commit web/lib/score-rules.json
    assert json.loads(export_rules.OUT.read_text()) == export_rules.rules()


def test_website_welcome_email_matches_the_pipeline():
    # If this fails: run `python -m tremor.export_rules` (in pipeline/) and commit web/lib/welcome-email.json
    assert json.loads(export_rules.WELCOME_OUT.read_text()) == export_rules.welcome()
