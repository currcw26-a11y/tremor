from datetime import date

from tremor.sources import jobs, layoffs


def test_state_file_columns_found_by_keyword(tmp_path):
    f = tmp_path / "ca.csv"
    f.write_text("Notice Date,Effective,Received Date,Company,County,No. Of Employees,Layoff/Closure\n"
                 "10/01/2026,12/01/2026,10/02/2026,\"Example Therapeutics, Inc.\",San Mateo,52,Layoff Permanent\n"
                 "09/15/2026,,,Some Bakery LLC,Fresno,30,Closure\n")
    rows = layoffs.read_state_csv(f, "ca")
    assert rows[0] == {"state": "CA", "company_name": "Example Therapeutics, Inc.", "notice_date": date(2026, 10, 1),
                       "employees": 52, "location": "San Mateo"}


def test_only_recent_notices_from_tracked_companies_match():
    rows = [{"company_name": "Example Therapeutics, Inc.", "notice_date": date(2026, 10, 1)},
            {"company_name": "Example Therapeutics Inc", "notice_date": date(2024, 1, 1)},   # too old
            {"company_name": "Some Bakery LLC", "notice_date": date(2026, 10, 1)}]
    found = layoffs.match(rows, {"example": "EXMP"}, since=date(2025, 11, 1))
    assert [r["ticker"] for r in found] == ["EXMP"]


def test_dates_in_several_formats():
    assert layoffs.parse_date("10/01/2026") == date(2026, 10, 1)
    assert layoffs.parse_date("2026-10-01") == date(2026, 10, 1)
    assert layoffs.parse_date("Oct 1, 2026") == date(2026, 10, 1)
    assert layoffs.parse_date("") is None


def test_clinical_jobs_are_counted():
    js = [{"title": "Senior Clinical Trial Leader", "department": "Clinical Operations"},
          {"title": "Director, Regulatory Affairs", "department": ""},
          {"title": "Aseptic Manufacturing Technician", "department": "Operations"},
          {"title": "Medical Science Liaison (MSL)", "department": "Medical Affairs"},
          {"title": "Staff Accountant", "department": "Finance"}]
    assert jobs.count(js) == (5, 3)


def test_board_name_guesses():
    assert jobs.slug_candidates("Iovance Biotherapeutics, Inc.", "iovance")[:2] == ["iovancebiotherapeutics", "iovance"]


def test_generic_board_names_are_not_trusted_automatically():
    assert jobs.auto_confirm("ARVINAS, INC.", "arvinas", "Arvinas")                        # full name used
    assert jobs.auto_confirm("Kura Oncology, Inc.", "kuraoncology", "Kura Oncology")
    assert jobs.auto_confirm("Olema Pharmaceuticals, Inc.", "olema", "Olema Oncology")     # board name sounds like biotech
    assert not jobs.auto_confirm("Aura Biosciences, Inc.", "aura", "Aura")                 # a tech company
    assert not jobs.auto_confirm("Kodiak Sciences Inc.", "kodiak", "Kodiak")               # self-driving trucks
    assert not jobs.auto_confirm("Protagonist Therapeutics, Inc", "protagonist", "Protagonist")
