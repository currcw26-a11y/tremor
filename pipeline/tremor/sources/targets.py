"""What a cancer drug targets, and what kind of cancer a trial is in, read from words in the trial record.

Used for the "rival drug failed" signal: two trials are rivals when their drugs hit the same target
in the same kind of cancer. No AI: these are fixed word lists, so every match can be shown and checked.
"""
import re

# Canonical target name -> pattern. Only specific names; broad words like "antibody" never count.
TARGETS = {
    "PD-1": r"\bpd-?1\b|programmed (cell )?death[- ](protein )?1\b",
    "PD-L1": r"\bpd-?l1\b|programmed death[- ]ligand[- ]1",
    "CTLA-4": r"\bctla-?4\b",
    "TIGIT": r"\btigit\b",
    "LAG-3": r"\blag-?3\b",
    "TIM-3": r"\btim-?3\b",
    "HER2": r"\bher-?2\b|\berbb2\b",
    "HER3": r"\bher-?3\b|\berbb3\b",
    "EGFR": r"\begfr\b",
    "KRAS G12C": r"\bkras[ -]?g12c\b|\bg12c\b",
    "KRAS G12D": r"\bkras[ -]?g12d\b|\bg12d\b",
    "BRAF": r"\bbraf\b",
    "MEK": r"\bmek ?1?/?2?\b(?! ?kinase kinase)",
    "ALK": r"\balk\b(?![- ]?positive lymphoma)",
    "ROS1": r"\bros-?1\b",
    "RET": r"\bret\b(?=[- ](fusion|inhibitor|mutant|altered|positive))",
    "MET": r"\bc-?met\b|\bmet\b(?=[- ](exon|amplif|inhibitor|fusion))",
    "FGFR": r"\bfgfr ?[1-4]?\b",
    "NTRK": r"\bntrk\b|\btrk\b",
    "PI3K": r"\bpi3k\b|\bpik3ca\b",
    "AKT": r"\bakt\b",
    "mTOR": r"\bmtor\b",
    "CDK4/6": r"\bcdk ?4/6\b|\bcdk4\b|\bcdk6\b",
    "PARP": r"\bparp\b",
    "BCL-2": r"\bbcl-?2\b",
    "BTK": r"\bbtk\b|bruton",
    "CD19": r"\bcd19\b",
    "CD20": r"\bcd20\b",
    "CD22": r"\bcd22\b",
    "CD38": r"\bcd38\b",
    "CD30": r"\bcd30\b",
    "CD33": r"\bcd33\b",
    "CD123": r"\bcd123\b",
    "CD79b": r"\bcd79b\b",
    "CD47": r"\bcd47\b",
    "CD70": r"\bcd70\b",
    "BCMA": r"\bbcma\b",
    "GPRC5D": r"\bgprc5d\b",
    "FcRH5": r"\bfcrh5\b",
    "DLL3": r"\bdll-?3\b",
    "TROP2": r"\btrop-?2\b",
    "Nectin-4": r"\bnectin-?4\b",
    "B7-H3": r"\bb7-?h3\b",
    "B7-H4": r"\bb7-?h4\b",
    "Claudin 18.2": r"\bclaudin[- ]?18\.?2\b|\bcldn18\.?2\b",
    "Folate receptor alpha": r"\bfolate receptor[- ]alpha\b|\bfr[α-]?alpha\b|\bfolr1\b",
    "CEACAM5": r"\bceacam5\b",
    "VEGF": r"\bvegf(r ?[1-3]?)?\b",
    "HIF-2α": r"\bhif-?2\b",
    "IDH1": r"\bidh1\b",
    "IDH2": r"\bidh2\b",
    "FLT3": r"\bflt-?3\b",
    "Menin": r"\bmenin\b",
    "KIT": r"\bc-?kit\b",
    "Androgen receptor": r"\bandrogen receptor\b",
    "Estrogen receptor": r"\bestrogen receptor\b|\bserd\b",
    "PSMA": r"\bpsma\b",
    "Somatostatin receptor": r"\bsstr2?\b|\bsomatostatin receptor\b",
    "EZH2": r"\bezh2\b",
    "WEE1": r"\bwee-?1\b",
    "ATR": r"\batr\b(?=[- ]inhibitor)",
    "SHP2": r"\bshp-?2\b",
    "GD2": r"\bgd2\b",
    "Mesothelin": r"\bmesothelin\b",
    "PRMT5": r"\bprmt5\b",
    "KAT6": r"\bkat6a?\b",
    "AXL": r"\baxl\b",
}
_TARGET_RE = {k: re.compile(v, re.I) for k, v in TARGETS.items()}

# Targets of approved drugs that are often given ALONGSIDE a new drug (like pembrolizumab for PD-1). When a trial
# fails, a target named only in its record text and in this list is probably the partner drug's, so it doesn't count.
BACKBONE = {"PD-1", "PD-L1", "CTLA-4", "VEGF", "HER2", "EGFR", "CDK4/6", "Estrogen receptor", "Androgen receptor",
            "CD20", "CD38", "BTK", "BCL-2", "PARP", "mTOR"}

# Gene symbols ChEMBL reports -> the same canonical names, so both sources speak one language
SYMBOLS = {
    "PDCD1": "PD-1", "CD274": "PD-L1", "CTLA4": "CTLA-4", "TIGIT": "TIGIT", "LAG3": "LAG-3", "HAVCR2": "TIM-3",
    "ERBB2": "HER2", "ERBB3": "HER3", "EGFR": "EGFR", "BRAF": "BRAF", "MAP2K1": "MEK", "MAP2K2": "MEK", "ALK": "ALK",
    "ROS1": "ROS1", "RET": "RET", "MET": "MET", "FGFR1": "FGFR", "FGFR2": "FGFR", "FGFR3": "FGFR", "FGFR4": "FGFR",
    "NTRK1": "NTRK", "NTRK2": "NTRK", "NTRK3": "NTRK", "PIK3CA": "PI3K", "PIK3CD": "PI3K", "AKT1": "AKT", "MTOR": "mTOR",
    "CDK4": "CDK4/6", "CDK6": "CDK4/6", "PARP1": "PARP", "PARP2": "PARP", "BCL2": "BCL-2", "BTK": "BTK", "CD19": "CD19",
    "MS4A1": "CD20", "CD22": "CD22", "CD38": "CD38", "TNFRSF8": "CD30", "CD33": "CD33", "IL3RA": "CD123",
    "CD79B": "CD79b", "CD47": "CD47", "CD70": "CD70", "TNFRSF17": "BCMA", "GPRC5D": "GPRC5D", "FCRL5": "FcRH5",
    "DLL3": "DLL3", "TACSTD2": "TROP2", "NECTIN4": "Nectin-4", "CD276": "B7-H3", "VTCN1": "B7-H4", "CLDN18": "Claudin 18.2",
    "FOLR1": "Folate receptor alpha", "CEACAM5": "CEACAM5", "VEGFA": "VEGF", "KDR": "VEGF", "FLT1": "VEGF",
    "EPAS1": "HIF-2α", "IDH1": "IDH1", "IDH2": "IDH2", "FLT3": "FLT3", "MEN1": "Menin", "KIT": "KIT", "AR": "Androgen receptor",
    "ESR1": "Estrogen receptor", "FOLH1": "PSMA", "SSTR2": "Somatostatin receptor", "EZH2": "EZH2", "WEE1": "WEE1",
    "ATR": "ATR", "PTPN11": "SHP2", "MSLN": "Mesothelin", "PRMT5": "PRMT5", "KAT6A": "KAT6", "AXL": "AXL",
}

# Kinds of cancer, broad enough that "same cancer" means something to a beginner
CANCER_TYPES = {
    "lung": r"\blung\b|nsclc|sclc|pulmonary (carcinoma|adeno)|mesothelioma",
    "breast": r"\bbreast\b",
    "prostate": r"\bprostat",
    "colorectal": r"colorectal|\bcolon\b|\brectal\b|\bcrc\b",
    "pancreatic": r"pancrea",
    "stomach and esophagus": r"gastric|stomach|esophag|oesophag|gastroesophageal|\bgej\b",
    "liver and bile duct": r"hepatocellular|\bliver\b|\bhcc\b|biliary|cholangio|gallbladder",
    "ovarian": r"ovarian|fallopian|peritoneal",
    "uterine and cervical": r"endometri|uterine|cervical",
    "bladder and urinary": r"bladder|urothelial|\bnmibc\b|\bmibc\b",
    "kidney": r"renal cell|\bkidney\b|\brcc\b",
    "head and neck": r"head and neck|\bhnscc\b|oral cavity|oropharyn|nasopharyn|laryn",
    "melanoma and skin": r"melanoma|skin|cutaneous squamous|merkel|basal cell",
    "brain": r"glioma|glioblastoma|\bgbm\b|astrocytom|brain|meningiom",
    "leukemia": r"leuka?emia|\baml\b|\bcll\b|\bcml\b|\ball\b(?=\W)",
    "lymphoma": r"lymphoma|\bdlbcl\b|\bnhl\b",
    "myeloma": r"myeloma",
    "sarcoma": r"sarcoma|\bgist\b|chordoma",
    "thyroid": r"thyroid",
    "neuroendocrine": r"neuroendocrine|carcinoid",
    "myelodysplastic and myeloproliferative": r"myelodysplas|\bmds\b|myelofibrosis|polycythemia|thrombocythemia",
}
_CANCER_RE = {k: re.compile(v, re.I) for k, v in CANCER_TYPES.items()}


def targets_in(text: str) -> set[str]:
    """Target names written in a piece of trial text."""
    return {name for name, rx in _TARGET_RE.items() if rx.search(text or "")}


def from_symbols(symbols) -> set[str]:
    return {SYMBOLS[s] for s in symbols or [] if s in SYMBOLS}


def cancer_types(conditions: list[str], title: str = "") -> set[str]:
    text = " ; ".join(conditions or []) + " ; " + (title or "")
    return {name for name, rx in _CANCER_RE.items() if rx.search(text)}


_NOT_CANCER_WORD = {"leukemia", "lymphoma", "myeloma", "sarcoma", "melanoma and skin", "brain",
                    "myelodysplastic and myeloproliferative", "neuroendocrine"}
_PHRASE = {"melanoma and skin": "melanoma or skin cancer", "brain": "brain tumors",
           "myelodysplastic and myeloproliferative": "bone marrow cancers", "neuroendocrine": "neuroendocrine tumors"}


def cancer_phrase(kind: str) -> str:
    """'lung' -> 'lung cancer', 'leukemia' -> 'leukemia' (for plain sentences)."""
    return _PHRASE.get(kind) or (kind if kind in _NOT_CANCER_WORD else f"{kind} cancer")
