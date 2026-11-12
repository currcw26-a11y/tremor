"""Reading 8-K item 5.02 text (and non-US companies' 6-Ks) to spot KEY executives leaving.

Item 5.02 is used for lots of things: new board members, pay changes, hires, and departures.
We only care when someone in a key role (see key_exec_titles in config/tremor.yaml) leaves.

Approach (simple and transparent): split the text into sentences and flag a sentence that has
BOTH a leaving word and a key title held at THIS company.
"""
import html
import re

from . import config

LEAVING = re.compile(
    r"\b(resign\w*|retire\w*|retirement|depart\w*|step(?:s|ped|ping)? down|terminat\w*|"
    r"separat\w*|will leave|no longer serv\w*|ceas\w* to serve|transition\w* out)\b", re.I)
# Words right before a title that mean the person is KEEPING or TAKING that role
KEEPING = re.compile(r"\b(appoint\w*|retain\w*|remain\w*|continu\w*|named|elect\w*|promot\w*|hired|join\w*)\b"
                     r"[^.;]{0,45}$", re.I)
# 6-Ks (non-US companies) carry every kind of news, so the check is stricter there:
NEWS_MAX_CHARS = 30_000   # only short news releases; long reports mostly retell old changes
STRICT_LEAVING = re.compile(r"\b(resign\w*|retir\w*|step(?:s|ped|ping)? down|depart\w*|will leave|transition\w* out|"
                            r"will transition (?:to|into))\b", re.I)
# "appointed X as Chief Medical Officer, succeeding Y": the title is changing hands, so Y is leaving it
SUCCESSION = re.compile(r"\bsucceed(?:s|ing)\s+(?:(?:Dr|Mr|Ms|Mrs|Prof)\.?\s+)?[A-Z][a-z]", re.I)
PAST_ROLE = re.compile(r"\b(prior|former|previous|predecessor)\s*$", re.I)   # "our prior Chief Executive Officer"
MAX_SENTENCE = 350        # longer "sentences" are tables run together
HEADER = re.compile(r"departure of directors or (certain )?officers[^.]*\.", re.I)


def html_to_text(raw: str) -> str:
    text = re.sub(r"(?is)<(script|style).*?</\1>", " ", raw)
    text = html.unescape(re.sub(r"<[^>]+>", " ", text))
    return " ".join(text.split())


def item_502_section(text: str) -> str:
    """The part of the 8-K under 'Item 5.02', up to the next item (or 4,000 characters)."""
    m = re.search(r"item\s*5\.02", text, re.I)
    if not m:
        return text[:4000]
    rest = text[m.end():]
    nxt = re.search(r"item\s*\d\.\d\d", rest, re.I)
    return rest[: nxt.start() if nxt else 4000][:4000]


def _title_at_this_company(sentence: str, title: str) -> bool:
    """Is someone LEAVING this title at THIS company? False for 'CEO at Align Technology',
    'retained his position as CEO', or 'appointed Chief Medical Officer'."""
    for m in re.finditer(re.escape(title), sentence, re.I):
        before = sentence[max(0, m.start() - 60): m.start()]
        if KEEPING.search(before):
            continue  # "retained his position as CEO", "appointed Chief Medical Officer": not leaving
        after = sentence[m.end(): m.end() + 40]
        if re.match(r"\s+(at|of)\s+(?!the company|the registrant|our|its)[A-Z]", after):
            continue  # a title at some other company
        return True
    return False


def find_key_departure(text: str, whole: bool = False) -> str | None:
    """The sentence describing a key executive leaving, or None.
    whole=True is for 6-Ks from non-US companies: no 'Item 5.02' to jump to, so it reads the whole (short)
    news release, with stricter leaving words and no past roles."""
    if whole and len(text) > NEWS_MAX_CHARS:
        return None
    section = HEADER.sub(" ", text if whole else item_502_section(text))
    titles = config.load()["key_exec_titles"]
    leaving = STRICT_LEAVING if whole else LEAVING
    for sentence in re.split(r"(?<=[.;])\s+(?=[A-Z])", section):
        succ = SUCCESSION.search(sentence) if whole and len(sentence) <= MAX_SENTENCE else None
        if succ and any(re.search(r"\bas\s+(?:the\s+)?(?:new\s+)?" + re.escape(t), sentence[:succ.start()], re.I) for t in titles):
            return sentence.strip()[:500]   # "named X as Chief Medical Officer, succeeding Y"
        if not leaving.search(sentence) or (whole and len(sentence) > MAX_SENTENCE):
            continue
        for t in titles:
            if not _title_at_this_company(sentence, t):
                continue
            if whole and all(PAST_ROLE.search(sentence[max(0, m.start() - 20):m.start()])
                             for m in re.finditer(re.escape(t), sentence, re.I)):
                continue
            return sentence.strip()[:500]
    return None
