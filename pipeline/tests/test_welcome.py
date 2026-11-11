from tremor import emails
from tremor.alert_job import welcome_due


def test_welcome_email_has_greeting_unsubscribe_and_no_advice():
    m = emails.welcome("Ada <script> Lovelace", "tok-1")
    assert m["subject"] == "Welcome to Tremor"
    assert "Hi Ada," in m["text"] and "&lt;script&gt;" not in m["html"] and "<script>" not in m["html"]
    assert "/unsubscribe?token=tok-1" in m["html"] and m["unsubscribe_url"].endswith("/api/unsubscribe?token=tok-1")
    assert "Not investment advice" in m["html"] and "Not investment advice" in m["text"]
    assert "{{" not in m["html"] + m["text"]
    words = m["text"].lower()
    assert " buy " not in words.replace("buy or sell", "") and "should" not in words


def test_greeting_without_a_name():
    assert emails.greeting(None) == "Hi," and emails.greeting("  ") == "Hi,"


def test_who_still_needs_a_welcome():
    people = [{"user_id": "a"}, {"user_id": "b", "welcome_sent_at": "2026-11-11"}, {"user_id": "c", "unsubscribed": True},
              {"user_id": "d"}]
    assert [p["user_id"] for p in welcome_due(people, {"d": 3})] == ["a"]   # d failed 3 times: stop trying
