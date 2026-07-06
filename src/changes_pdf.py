"""
changes_pdf.py — read the DEFRA "major changes" report (PDF) and retrieve the
passage relevant to a given factor. This is the grounding source for the AI
explanation: the model may only explain a change from text that actually appears
here. No vector DB — plain keyword + fuzzy retrieval, kept in memory.

Public functions:
    extract_changes_text(pdf_path) -> str
    chunk_changes(text)            -> list[dict{title, text}]
    retrieve_passage(chunks, material, min_score) -> (passage_text, score)
"""

from __future__ import annotations

import re
import pdfplumber
from rapidfuzz import fuzz

# Generic words that carry no discriminating signal when matching a material name
# to a passage (they appear on almost every DEFRA row).
_STOPWORDS = {
    "primary", "material", "production", "average", "blend", "generated",
    "supply", "scope", "the", "and", "of", "for", "uk", "all", "use", "mix",
    "total", "per", "unit", "factor", "factors",
}


def extract_changes_text(pdf_path: str) -> str:
    """Extract all text from the changes-report PDF."""
    parts = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            parts.append(page.extract_text() or "")
    return "\n".join(parts)


def chunk_changes(text: str) -> list[dict]:
    """
    Split the report into passages. We prefer explicit "Change: <x>" blocks (as
    DEFRA-style reports use headed sections); if none exist we fall back to
    paragraph blocks separated by blank lines.
    """
    lines = [ln.rstrip() for ln in text.splitlines()]

    # Try headed "Change:" blocks first.
    blocks, current = [], None
    for ln in lines:
        m = re.match(r"\s*change\s*:\s*(.+)", ln, flags=re.IGNORECASE)
        if m:
            if current:
                blocks.append(current)
            current = {"title": m.group(1).strip(), "text": ""}
        elif current is not None:
            current["text"] = (current["text"] + " " + ln).strip()
    if current:
        blocks.append(current)

    if blocks:
        return [b for b in blocks if b["text"] or b["title"]]

    # Fallback: paragraph blocks.
    paras, buf = [], []
    for ln in lines:
        if ln.strip():
            buf.append(ln.strip())
        elif buf:
            paras.append(" ".join(buf))
            buf = []
    if buf:
        paras.append(" ".join(buf))
    return [{"title": "", "text": p} for p in paras if len(p) > 20]


def _keywords(material: str) -> set[str]:
    """Discriminating tokens from a material/activity name."""
    toks = re.findall(r"[a-z0-9]+", str(material).lower())
    return {t for t in toks if len(t) >= 4 and t not in _STOPWORDS}


def _keyword_overlap(material: str, passage: str) -> float:
    """Fraction of the material's discriminating keywords present in the passage."""
    kws = _keywords(material)
    if not kws:
        return 0.0
    ptoks = set(re.findall(r"[a-z0-9]+", passage.lower()))
    hit = sum(1 for k in kws if k in ptoks)
    return hit / len(kws)


def retrieve_passage(chunks: list[dict], material: str, min_score: float = 0.5):
    """
    Return (passage_text, score) for the chunk best matching `material`, or
    ("", 0.0) if nothing is relevant enough. A returned empty string is the
    signal that the report does NOT explain this change — the explainer must then
    say so rather than invent a reason.
    """
    best_text, best_score = "", 0.0
    for ch in chunks:
        haystack = f"{ch['title']} {ch['text']}"
        overlap = _keyword_overlap(material, f"{ch['title']} {ch['text']}")
        # Fuzzy score against the (short, distinctive) title guards against
        # passages that mention a keyword only in passing.
        title_fuzz = fuzz.token_set_ratio(material.lower(), ch["title"].lower()) / 100.0
        score = max(overlap, title_fuzz)
        if score > best_score:
            best_score, best_text = score, haystack.strip()

    if best_score >= min_score:
        return best_text, round(best_score, 3)
    return "", round(best_score, 3)
