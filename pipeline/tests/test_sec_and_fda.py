from tremor.sources.federal_register import parse_meeting_date, safe_term, split_drug_names, useful_names
from tremor.sources.sec import parse_form4

FORM4 = """<?xml version="1.0"?>
<ownershipDocument>
  <issuer><issuerTradingSymbol>EXMP</issuerTradingSymbol></issuer>
  <reportingOwner>
    <reportingOwnerId><rptOwnerName>Doe Jane</rptOwnerName></reportingOwnerId>
    <reportingOwnerRelationship>
      <isDirector>0</isDirector><isOfficer>1</isOfficer><officerTitle>Chief Medical Officer</officerTitle>
    </reportingOwnerRelationship>
  </reportingOwner>
  <aff10b5One>{planned}</aff10b5One>
  <nonDerivativeTable>
    <nonDerivativeTransaction>
      <transactionDate><value>2026-10-01</value></transactionDate>
      <transactionCoding><transactionCode>S</transactionCode></transactionCoding>
      <transactionAmounts>
        <transactionShares><value>5000</value></transactionShares>
        <transactionPricePerShare><value>12.50</value></transactionPricePerShare>
        <transactionAcquiredDisposedCode><value>D</value></transactionAcquiredDisposedCode>
      </transactionAmounts>
    </nonDerivativeTransaction>
  </nonDerivativeTable>
  <footnotes>{footnote}</footnotes>
</ownershipDocument>"""


def test_form4_sale_is_parsed():
    [t] = parse_form4(FORM4.format(planned=0, footnote=""))
    assert t["insider_name"] == "Doe Jane"
    assert t["insider_title"] == "Chief Medical Officer"
    assert t["is_officer"] is True
    assert t["transaction_code"] == "S" and t["acquired_disposed"] == "D"
    assert t["shares"] == 5000 and t["price"] == 12.5
    assert t["is_10b5_1"] is False


def test_form4_preplanned_checkbox():
    [t] = parse_form4(FORM4.format(planned=1, footnote=""))
    assert t["is_10b5_1"] is True


def test_form4_preplanned_mentioned_in_footnote():
    note = '<footnote id="F1">Sold under a Rule 10b5-1 trading plan adopted May 2026.</footnote>'
    [t] = parse_form4(FORM4.format(planned=0, footnote=note))
    assert t["is_10b5_1"] is True


def test_meeting_date_is_read_from_text():
    assert parse_meeting_date("The meeting will be held on April 30, 2026, from 8:00 a.m.") == "2026-04-30"
    assert parse_meeting_date(None) is None


def test_generic_drugs_are_not_searched():
    assert useful_names(["Placebo", "Pembrolizumab", "EXB-101", "Lifileucel (LN-145)", "IL-2"]) == ["EXB 101", "Lifileucel"]  # "-" is a search command, so it becomes a space


def test_company_names_cleaned_for_search():
    from tremor.sec_job import _short_company_name
    assert _short_company_name("ELI LILLY & Co") == "Eli Lilly"
    assert _short_company_name("VERTEX PHARMACEUTICALS INC / MA") == "Vertex Pharmaceuticals"
    assert _short_company_name("Revolution Medicines, Inc.") == "Revolution Medicines"


def test_messy_drug_entries_are_split_and_cleaned():
    assert split_drug_names("Cisplatin 75mg/m2 + Pemetrexed") == ["Cisplatin", "Pemetrexed"]
    assert split_drug_names("Coformulated favezelimab/pembrolizumab") == ["favezelimab", "pembrolizumab"]
    assert split_drug_names("Adavosertib 150 mg BD + olaparib 200 mg BD .") == ["Adavosertib", "olaparib"]
    assert useful_names(["Chemotherapy: Carboplatin", "Belrestotug."]) == ["Belrestotug"]


def test_search_terms_never_contain_symbols():
    assert safe_term('Bad "name" / with + symbols^2') == "Bad name with symbols 2"


def test_everyday_words_are_not_drug_names():
    assert useful_names(["Background", "Treatment", "Study Drug", "Experimental Arm", "Lifileucel"]) == ["Lifileucel"]
