"""Does the 8-K reader spot KEY executives leaving, and ignore everything else?"""
from tremor.exec_changes import find_key_departure

HEAD = ("Item 5.02 Departure of Directors or Certain Officers; Election of Directors; Appointment of "
        "Certain Officers; Compensatory Arrangements of Certain Officers. ")


def test_chief_medical_officer_resigning_is_flagged():
    text = HEAD + "On November 1, 2026, Jane Doe notified the Company of her resignation as Chief Medical Officer, effective November 15, 2026. Item 9.01 Exhibits."
    assert "Chief Medical Officer" in find_key_departure(text)


def test_head_of_rd_stepping_down_is_flagged():
    text = HEAD + "The Company announced that John Roe will step down as Head of Research and Development."
    assert find_key_departure(text)


def test_new_board_member_is_not_flagged():
    text = HEAD + "On October 30, 2026, the Board approved an increase in the size of the Board from ten to eleven members and appointed Aaron Martin."
    assert find_key_departure(text) is None


def test_cfo_retiring_is_not_a_key_executive():
    text = HEAD + "Keith Goldan will retire as the Company's Chief Financial Officer effective November 9, 2026."
    assert find_key_departure(text) is None


def test_director_leaving_to_be_ceo_elsewhere_is_not_flagged():
    text = HEAD + ("On October 28, 2026, Jennifer Davis, a director of AbbVie, notified the Board of her intent to "
                   "resign from the Board, in light of her recent appointment as Chief Executive Officer at Align Technology, Inc.")
    assert find_key_departure(text) is None


def test_new_chief_medical_officer_hired_is_not_flagged():
    text = HEAD + "The Board appointed Dr. Sam Lee as Chief Medical Officer, effective December 1, 2026."
    assert find_key_departure(text) is None
