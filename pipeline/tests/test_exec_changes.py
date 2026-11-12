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


def test_keeping_the_key_role_is_not_flagged():
    text = HEAD + "Mr. Mazzo resigned solely from the office of President, but he retained his position as Chief Executive Officer of the Company."
    assert find_key_departure(text) is None


def test_director_resigning_to_take_a_new_role_is_not_flagged():
    text = HEAD + "Diego Miralles resigned as a member of the Board, in connection with his appointment as Chief Medical Officer of Another Bio."
    assert find_key_departure(text) is None


def test_cmo_terminated_is_flagged():
    text = HEAD + "On August 1, 2026, Dr. Buck, the Company's Executive Vice President of R&D and Chief Medical Officer was terminated."
    assert find_key_departure(text)


def test_ceo_retiring_is_flagged():
    text = HEAD + "Mr. Paterson notified the Board of his decision to retire as President and Chief Executive Officer of the Company."
    assert find_key_departure(text)


def test_6k_news_release_with_a_key_departure():
    from tremor.exec_changes import find_key_departure
    text = ("Example Bio Announces Leadership Transition. PARIS, France, March 3, 2026 - Example Bio SA today announced "
            "that Dr. Jane Roe will step down as Chief Medical Officer, effective April 30, 2026. The company has begun a search.")
    assert "step down as Chief Medical Officer" in find_key_departure(text, whole=True)


def test_6k_false_alarms_are_ignored():
    from tremor.exec_changes import find_key_departure
    quote = ("“The response was durable: separation from placebo emerged early,” said Luc Truyen, M.D., "
             "Chief Medical Officer at Example Bio.")
    assert find_key_departure(quote, whole=True) is None                         # 'separation' means something else here
    old = "Mr. Doe has served as interim CEO since January 2025, following the resignation of our prior Chief Executive Officer, Dr. Smith."
    assert find_key_departure(old, whole=True) is None                           # a past role, not news
    assert find_key_departure("x " * 20_000 + "The Chief Executive Officer will resign.", whole=True) is None  # long report


def test_6k_succeeding_the_previous_holder_counts():
    from tremor.exec_changes import find_key_departure
    s = ("Innate also announced the appointment of Markus Jensen as Chief Medical Officer and member of the Executive "
         "Leadership Team, effective September 1, 2026, succeeding Sonia Quaratino.")
    assert find_key_departure(s, whole=True)
    assert find_key_departure("Example Bio appoints Jane Roe as Chief Medical Officer, a new role at the company.", whole=True) is None


def test_6k_succession_must_be_for_a_key_role():
    from tremor.exec_changes import find_key_departure
    s = "Example Bio appointed Ann Lee as Chairman of the Board, succeeding Tom Ray. Ms. Lee remains our Chief Executive Officer."
    assert find_key_departure(s, whole=True) is None
