from collections import Counter

from tremor import matching
from tremor.matching import core_name, build_suggestions

COMPANIES = [
    {"cik": "1", "name": "REGENERON PHARMACEUTICALS, INC.", "ticker": "REGN", "exchange": "Nasdaq"},
    {"cik": "2", "name": "BRISTOL MYERS SQUIBB CO", "ticker": "BMY", "exchange": "NYSE"},
    {"cik": "3", "name": "Merck & Co., Inc.", "ticker": "MRK", "exchange": "NYSE"},
    {"cik": "4", "name": "Johnson & Johnson", "ticker": "JNJ", "exchange": "NYSE"},
    {"cik": "5", "name": "Example Therapeutics Inc", "ticker": "EXMP", "exchange": "Nasdaq"},
]


def test_core_name_drops_filler():
    assert core_name("Regeneron Pharmaceuticals, Inc.") == "regeneron"
    assert core_name("Bristol-Myers Squibb") == "bristol myers squibb"
    assert core_name("VERTEX PHARMACEUTICALS INC / MA") == "vertex"  # SEC state tag removed
    assert core_name("Example Corp /DE/") == "example"


def run(sponsors, tmp_path, monkeypatch):
    monkeypatch.setattr(matching, "SUGGESTIONS_CSV", tmp_path / "s.csv")  # don't touch the real file
    matched, unmatched = build_suggestions(Counter(sponsors), COMPANIES)
    return {r["sponsor_name"]: r["ticker"] for r in matched}, [r["sponsor_name"] for r in unmatched]


def test_matches_name_variants_and_aliases(tmp_path, monkeypatch):
    found, _ = run(["Regeneron Pharmaceuticals", "Bristol-Myers Squibb",
                    "Merck Sharp & Dohme LLC", "Janssen Research & Development, LLC"], tmp_path, monkeypatch)
    assert found == {"Regeneron Pharmaceuticals": "REGN", "Bristol-Myers Squibb": "BMY",
                     "Merck Sharp & Dohme LLC": "MRK", "Janssen Research & Development, LLC": "JNJ"}


def test_does_not_match_unrelated_or_generic_names(tmp_path, monkeypatch):
    found, unmatched = run(["Jiangsu HengRui Medicine Co., Ltd.", "Pharmaceutical Research Inc"], tmp_path, monkeypatch)
    assert found == {}
    assert len(unmatched) == 2


def test_your_confirmed_choice_is_never_overwritten(tmp_path, monkeypatch):
    csv_path = tmp_path / "s.csv"
    csv_path.write_text("sponsor_name,trials,ticker,sec_company_name,how_matched,score,confirmed,notes\n"
                        "Regeneron Pharmaceuticals,3,REGN,x,same name,100,no,wrong company\n")
    monkeypatch.setattr(matching, "SUGGESTIONS_CSV", csv_path)
    matched, _ = build_suggestions(Counter(["Regeneron Pharmaceuticals"]), COMPANIES)
    assert matched[0]["confirmed"] == "no"
    assert matched[0]["notes"] == "wrong company"


def test_picks_healthcare_company_when_names_collide(tmp_path, monkeypatch):
    monkeypatch.setattr(matching, "SUGGESTIONS_CSV", tmp_path / "s.csv")
    companies = [
        {"cik": "10", "name": "Vertex, Inc.", "ticker": "VERX", "exchange": "Nasdaq"},          # software
        {"cik": "11", "name": "VERTEX PHARMACEUTICALS INC / MA", "ticker": "VRTX", "exchange": "Nasdaq"},
        {"cik": "12", "name": "Frontier Group Holdings, Inc.", "ticker": "ULCC", "exchange": "Nasdaq"},  # airline
    ]
    healthcare = {"11"}
    matched, unmatched = build_suggestions(
        Counter(["Vertex Pharmaceuticals Incorporated", "Frontier Medicines Corporation"]),
        companies, is_healthcare=lambda cik: cik in healthcare)
    assert [(r["sponsor_name"], r["ticker"]) for r in matched] == [("Vertex Pharmaceuticals Incorporated", "VRTX")]
    assert [r["sponsor_name"] for r in unmatched] == ["Frontier Medicines Corporation"]


def test_alias_needs_whole_word(tmp_path, monkeypatch):
    found, _ = run(["ImmunoGenesis"], tmp_path, monkeypatch)
    assert found == {}
