"""
discourse_classifier.py — Classify essay sentences into discourse categories
using rule-based heuristics + optional transformer model scoring.
"""

from __future__ import annotations
import re
import math
from typing import Optional
import pandas as pd

# ---------------------------------------------------------------------------
# Discourse category definitions
# ---------------------------------------------------------------------------
DISCOURSE_CATEGORIES = [
    "Lead", "Position", "Claim", "Evidence", "Counterclaim", "Rebuttal",
    "Concluding Statement", "Premise", "Assumption", "Supporting Fact",
    "Example", "Cause-Effect Relation", "Strong Evidence", "Weak Evidence",
    "Missing Evidence", "Unsupported Claim", "Bias Indicator", "Logical Fallacy",
]

# Sentence-position heuristic boundaries
_LEAD_RATIO     = 0.10   # first 10% of sentences
_CONCLUDE_RATIO = 0.10   # last 10% of sentences

# Keyword / pattern maps (order matters: first match wins in _keyword_classify)
_PATTERNS: list[tuple[str, list[str]]] = [
    ("Counterclaim",       ["however,", "on the other hand", "critics argue", "opponents claim",
                            "some believe", "others argue", "contrary to", "alternatively,"]),
    ("Rebuttal",           ["nevertheless,", "despite this", "regardless,", "yet", "even so,",
                            "in response,", "this can be refuted", "while it is true"]),
    ("Logical Fallacy",    ["everyone knows", "nobody can deny", "it's obvious that",
                            "clearly everyone", "all people", "always", "never fail",
                            "slippery slope", "straw man"]),
    ("Bias Indicator",     ["it is obvious", "undeniably", "without question",
                            "without a doubt", "certainly all", "universally accepted",
                            "no one can argue"]),
    ("Cause-Effect Relation", ["because of", "as a result", "leads to", "therefore",
                               "consequently", "this causes", "due to", "thus,"]),
    ("Example",            ["for example,", "for instance,", "such as", "to illustrate",
                            "consider the case", "e.g.,", "specifically,"]),
    ("Evidence",           ["according to", "studies show", "research indicates",
                            "data suggests", "statistics show", "reports indicate",
                            "surveys reveal", "a study by"]),
    ("Strong Evidence",    ["peer-reviewed", "meta-analysis", "clinical trial",
                            "randomized controlled", "systematic review", "statistically significant"]),
    ("Weak Evidence",      ["some people say", "it has been said", "i think",
                            "i believe", "in my opinion", "it seems", "people feel"]),
    ("Assumption",         ["it can be assumed", "it is assumed", "we can assume",
                            "this implies", "presumably", "it goes without saying"]),
    ("Claim",              ["should", "must", "ought to", "it is important",
                            "is essential", "is necessary", "we need to", "it is critical"]),
    ("Rebuttal",           ["but in fact", "this is not the case", "the evidence contradicts"]),
    ("Supporting Fact",    ["is", "are", "was", "were", "has been", "have been"]),
]


def _keyword_classify(sentence: str) -> Optional[str]:
    """Return the first matching discourse category based on keywords."""
    lower = sentence.lower()
    for category, kws in _PATTERNS:
        for kw in kws:
            if kw in lower:
                return category
    return None


def _has_citation(sentence: str) -> bool:
    """Detect APA/MLA-style citations."""
    return bool(re.search(r'\(\d{4}\)|\[[\d,]+\]|et al\.', sentence))


def _is_numeric_evidence(sentence: str) -> bool:
    """Detect sentences containing statistics / percentages."""
    return bool(re.search(r'\d+\s*%|\d+\s*(million|billion|thousand|\b\d{4}\b)', sentence))


def _classify_sentence(sentence: str, idx: int, total: int) -> dict:
    """
    Classify a single sentence using positional + keyword heuristics.
    Returns a dict with 'category', 'confidence', and flags.
    """
    pos_ratio = idx / max(total - 1, 1)

    # Position-based overrides
    if idx == 0:
        return {"category": "Lead", "confidence": 0.90}
    if pos_ratio <= _LEAD_RATIO and idx > 0:
        cat = _keyword_classify(sentence)
        if cat in ("Claim", "Position", None):
            return {"category": "Position", "confidence": 0.80}

    if pos_ratio >= (1 - _CONCLUDE_RATIO):
        cat = _keyword_classify(sentence)
        if cat in (None, "Supporting Fact", "Claim"):
            return {"category": "Concluding Statement", "confidence": 0.82}

    # Citation-based upgrades
    if _has_citation(sentence) or _is_numeric_evidence(sentence):
        kw_cat = _keyword_classify(sentence)
        if kw_cat in (None, "Evidence", "Supporting Fact"):
            return {"category": "Strong Evidence", "confidence": 0.85}

    # Keyword matching
    cat = _keyword_classify(sentence)
    if cat:
        # If claim-like but no evidence, flag as Unsupported Claim
        if cat == "Claim" and not _has_citation(sentence) and not _is_numeric_evidence(sentence):
            return {"category": "Unsupported Claim", "confidence": 0.70}
        return {"category": cat, "confidence": 0.75}

    # Default
    return {"category": "Supporting Fact", "confidence": 0.55}


def split_into_sentences(text: str) -> list[str]:
    """Split essay text into sentences using regex."""
    # Split on period / exclamation / question mark followed by space or end
    raw = re.split(r'(?<=[.!?])\s+', text.strip())
    # Filter very short fragments
    return [s.strip() for s in raw if len(s.strip()) > 15]


def classify_essay(
    text: str,
    use_transformer: bool = False,   # reserved for future transformer upgrade
) -> pd.DataFrame:
    """
    Main entry point.
    Accepts raw essay text, returns a DataFrame with columns:
      sentence, category, confidence, is_unsupported, is_assumption, has_citation, is_numeric
    """
    sentences = split_into_sentences(text)
    if not sentences:
        return pd.DataFrame(columns=[
            "sentence", "category", "confidence",
            "is_unsupported", "is_assumption", "has_citation", "is_numeric"
        ])

    rows = []
    for idx, sent in enumerate(sentences):
        result = _classify_sentence(sent, idx, len(sentences))
        rows.append({
            "sentence":       sent,
            "category":       result["category"],
            "confidence":     result["confidence"],
            "is_unsupported": result["category"] == "Unsupported Claim",
            "is_assumption":  result["category"] == "Assumption",
            "has_citation":   _has_citation(sent),
            "is_numeric":     _is_numeric_evidence(sent),
        })

    df = pd.DataFrame(rows)

    # Post-pass: mark "Missing Evidence" for claims without nearby evidence
    df = _flag_missing_evidence(df)

    return df


def _flag_missing_evidence(df: pd.DataFrame) -> pd.DataFrame:
    """
    If a Claim or Unsupported Claim is not followed within 2 sentences by Evidence,
    annotate it as needing missing evidence (store in 'missing_evidence' column).
    """
    df = df.copy()
    df["missing_evidence"] = False

    claim_cats = {"Claim", "Unsupported Claim", "Position"}
    evidence_cats = {"Evidence", "Strong Evidence", "Supporting Fact", "Example"}

    for i, row in df.iterrows():
        if row["category"] in claim_cats:
            # Check next 3 rows
            window = df.iloc[i + 1: i + 4]["category"].tolist() if i + 1 < len(df) else []
            if not any(c in evidence_cats for c in window):
                df.at[i, "missing_evidence"] = True

    return df


def get_category_counts(df: pd.DataFrame) -> dict:
    """Return a dict of {category: count} from classified df."""
    return df["category"].value_counts().to_dict()


def get_summary_stats(df: pd.DataFrame) -> dict:
    """Return high-level summary stats for the dashboard."""
    counts = get_category_counts(df)
    total = len(df)
    return {
        "total_sentences":    total,
        "claim_count":        counts.get("Claim", 0) + counts.get("Unsupported Claim", 0) + counts.get("Position", 0),
        "evidence_count":     counts.get("Evidence", 0) + counts.get("Strong Evidence", 0),
        "counterclaim_count": counts.get("Counterclaim", 0),
        "rebuttal_count":     counts.get("Rebuttal", 0),
        "assumption_count":   counts.get("Assumption", 0),
        "unsupported_count":  counts.get("Unsupported Claim", 0),
        "fallacy_count":      counts.get("Logical Fallacy", 0),
        "missing_evidence_count": int(df["missing_evidence"].sum()) if "missing_evidence" in df.columns else 0,
        "strong_evidence_count":  counts.get("Strong Evidence", 0),
        "weak_evidence_count":    counts.get("Weak Evidence", 0),
    }
