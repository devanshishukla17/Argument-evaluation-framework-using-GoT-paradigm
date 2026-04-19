"""
explanation_engine.py — Generate human-readable feedback from analysis results.
Produces teacher-grade and student-friendly explanations.
"""

from __future__ import annotations
import pandas as pd
from typing import Optional


# ---------------------------------------------------------------------------
# Graph explanations
# ---------------------------------------------------------------------------

def explain_graph_type(graph_type: str, stats: dict) -> str:
    """Return a plain-English description of why this graph type was chosen."""
    descriptions = {
        "standard_argument_graph": (
            "The essay follows a straightforward argumentation structure with claims supported by evidence. "
            "This graph shows the logical flow from premises to conclusions."
        ),
        "debate_graph": (
            f"The essay contains {stats.get('counterclaim_count', 0)} counterclaim(s), suggesting a debate-style structure. "
            "This graph highlights the claim–counterclaim–rebuttal dialectic."
        ),
        "unsupported_claim_graph": (
            f"The essay contains {stats.get('unsupported_count', 0)} unsupported claim(s). "
            "This graph flags where evidence is missing or insufficient."
        ),
        "hidden_assumption_graph": (
            f"The essay contains {stats.get('assumption_count', 0)} assumption(s). "
            "This graph surfaces the implicit premises that the argument depends on."
        ),
        "contradiction_graph": (
            f"The essay contains {stats.get('fallacy_count', 0)} potential logical fallacy/fallacies. "
            "This graph highlights contradictory or inconsistent statements."
        ),
        "got_branch_graph": (
            "Multiple reasoning branches were detected. "
            "This Graph-of-Thought view shows each branch and ranks them by logical strength."
        ),
    }
    return descriptions.get(graph_type, "This graph represents the argument structure of the essay.")


def explain_got_branch(branch: dict) -> str:
    """Return a plain-English explanation of a GoT reasoning branch."""
    name   = branch.get("name", "Branch")
    scores = branch.get("scores", {})
    steps  = branch.get("steps", [])
    desc   = branch.get("description", "")

    conf  = scores.get("confidence", 0)
    compl = scores.get("completeness", 0)
    div   = scores.get("diversity", 0)

    conf_str  = "high" if conf >= 0.75 else ("moderate" if conf >= 0.5 else "low")
    compl_str = "complete" if compl >= 0.7 else ("partial" if compl >= 0.4 else "incomplete")

    return (
        f"**{name}** — {desc} "
        f"This branch has *{conf_str}* confidence ({conf:.0%}), is *{compl_str}* "
        f"in its coverage of key discourse types ({compl:.0%}), "
        f"and shows a diversity score of {div:.0%}. "
        f"It contains {len(steps)} reasoning step(s)."
    )


def explain_aggregation(stats: dict) -> str:
    """Explain the aggregation of discourse units."""
    total = stats.get("total_sentences", 0)
    claims = stats.get("claim_count", 0)
    evidence = stats.get("evidence_count", 0)
    ratio = evidence / max(claims, 1)

    if ratio >= 1.5:
        quality = "well-evidenced"
    elif ratio >= 0.8:
        quality = "adequately evidenced"
    elif ratio >= 0.4:
        quality = "under-evidenced"
    else:
        quality = "poorly evidenced"

    return (
        f"The essay contains {total} discourse units, of which {claims} are claim-type and "
        f"{evidence} are evidence-type. This gives an evidence-to-claim ratio of "
        f"{ratio:.2f}, indicating the argument is **{quality}**."
    )


# ---------------------------------------------------------------------------
# Feedback generation
# ---------------------------------------------------------------------------

def generate_student_feedback(df: pd.DataFrame, verdict: dict, stats: dict) -> list[dict]:
    """
    Return a list of sentence-level feedback items for the student view.
    Each item: {sentence, category, feedback_type, message}
    """
    items = []

    for _, row in df.iterrows():
        sentence = row["sentence"]
        cat      = row["category"]

        # Strengths
        if cat == "Strong Evidence":
            items.append({
                "sentence":      sentence,
                "category":      cat,
                "feedback_type": "strength",
                "message":       "✅ Excellent — this is well-supported evidence.",
            })
        elif cat == "Rebuttal":
            items.append({
                "sentence":      sentence,
                "category":      cat,
                "feedback_type": "strength",
                "message":       "✅ Good — addressing counterarguments strengthens your essay.",
            })
        elif cat == "Claim" and row.get("has_citation"):
            items.append({
                "sentence":      sentence,
                "category":      cat,
                "feedback_type": "strength",
                "message":       "✅ This claim is backed by a citation.",
            })

        # Weaknesses
        elif cat == "Unsupported Claim":
            items.append({
                "sentence":      sentence,
                "category":      cat,
                "feedback_type": "weakness",
                "message":       "⚠️ This claim needs evidence — add a statistic, study, or example.",
            })
        elif cat == "Logical Fallacy":
            items.append({
                "sentence":      sentence,
                "category":      cat,
                "feedback_type": "weakness",
                "message":       "❌ This sentence may contain a logical fallacy. Revise for clarity and rigour.",
            })
        elif cat == "Weak Evidence":
            items.append({
                "sentence":      sentence,
                "category":      cat,
                "feedback_type": "weakness",
                "message":       "⚠️ Weak / anecdotal evidence. Upgrade to a peer-reviewed source if possible.",
            })
        elif cat == "Bias Indicator":
            items.append({
                "sentence":      sentence,
                "category":      cat,
                "feedback_type": "weakness",
                "message":       "⚠️ This phrasing may come across as biased. Consider more neutral language.",
            })

        # Missing evidence
        if row.get("missing_evidence"):
            items.append({
                "sentence":      sentence,
                "category":      "Missing Evidence",
                "feedback_type": "missing",
                "message":       "🔍 No evidence follows this claim. Add support in the next sentence.",
            })

        # Suggestions
        if cat == "Assumption":
            items.append({
                "sentence":      sentence,
                "category":      cat,
                "feedback_type": "suggestion",
                "message":       "💡 Suggestion: Make this assumption explicit and justify it.",
            })
        elif cat == "Counterclaim" and not any(
            df.iloc[max(0, df.index.get_loc(_) - 3): df.index.get_loc(_) + 3]["category"].isin(["Rebuttal"]).tolist()
        ):
            items.append({
                "sentence":      sentence,
                "category":      cat,
                "feedback_type": "suggestion",
                "message":       "💡 You raised a counterargument — now rebut it to strengthen your position.",
            })

    return items


def generate_teacher_feedback(df: pd.DataFrame, verdict: dict, stats: dict, devil_results: dict) -> dict:
    """
    Return structured teacher-grade feedback covering all dimensions.
    """
    return {
        "summary":          verdict.get("verdict_text", ""),
        "overall_score":    verdict.get("overall_score", 0.0),
        "strengths":        verdict.get("strengths", []),
        "weaknesses":       verdict.get("weaknesses", []),
        "improvements":     verdict.get("improvements", []),
        "stats_overview":   stats,
        "logic_issues":     devil_results.get("logical", {}).get("findings", []),
        "ethical_issues":   devil_results.get("ethical", {}).get("findings", []),
        "evidence_issues":  devil_results.get("evidence", {}).get("findings", []),
        "cultural_biases":  devil_results.get("cultural", {}).get("findings", []),
        "domain_gaps":      devil_results.get("domain", {}).get("findings", []),
        "pedagogy_notes":   devil_results.get("pedagogy", {}).get("findings", []),
        "total_devil_issues": devil_results.get("synthesis", {}).get("total_issues", 0),
    }


def compute_subscores(df: pd.DataFrame, stats: dict) -> dict:
    """
    Compute sub-scores aligned with the Toulmin scoring traits.
    Each score is 0-10, derived directly from the same trait functions
    used in got_engine._compute_toulmin_score() to ensure consistency.

    The six traits map to:
      T1 Claim Clarity         -> "Claim Clarity"
      T2 Evidence Quality      -> "Evidence Quality"
      T3 Warrant/Reasoning     -> "Warrant & Reasoning"
      T4 Counterargument       -> "Counterargument"
      T5 Rebuttal Quality      -> "Rebuttal Quality"
      T6 Structural Cohesion   -> "Structural Cohesion"
    """
    from got_engine import (
        _score_T1_claim_clarity, _score_T2_evidence_quality,
        _score_T3_warrant_reasoning, _score_T4_counterargument,
        _score_T5_rebuttal_quality, _score_T6_structural_cohesion
    )

    # We need ranked_branches for T3 — use a dummy if not available
    dummy_branches = [{"scores": {"overall": 0.5}}]

    t1_raw, t1_max, _ = _score_T1_claim_clarity(stats)
    t2_raw, t2_max, _ = _score_T2_evidence_quality(stats)
    t3_raw, t3_max, _ = _score_T3_warrant_reasoning(stats, dummy_branches)
    t4_raw, t4_max, _ = _score_T4_counterargument(stats)
    t5_raw, t5_max, _ = _score_T5_rebuttal_quality(stats)
    t6_raw, t6_max, _ = _score_T6_structural_cohesion(stats, df)

    def to_10(raw, mx):
        return round(min(10.0, max(0.0, (raw / mx) * 10.0)), 1)

    return {
        "T1 Claim Clarity":       to_10(t1_raw, t1_max),
        "T2 Evidence Quality":    to_10(t2_raw, t2_max),
        "T3 Warrant & Reasoning": to_10(t3_raw, t3_max),
        "T4 Counterargument":     to_10(t4_raw, t4_max),
        "T5 Rebuttal Quality":    to_10(t5_raw, t5_max),
        "T6 Structural Cohesion": to_10(t6_raw, t6_max),
    }


def extract_keywords(df: pd.DataFrame, top_n: int = 10) -> list[str]:
    """Simple frequency-based keyword extraction (no external NLP required)."""
    import re
    from collections import Counter

    stopwords = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been",
        "have", "has", "had", "do", "does", "did", "will", "would",
        "could", "should", "may", "might", "shall", "to", "of", "in",
        "for", "on", "with", "at", "by", "from", "as", "it", "this",
        "that", "they", "we", "he", "she", "and", "or", "but", "not",
        "its", "our", "their", "can", "also", "which", "these", "those",
        "than", "more", "also", "into", "such", "if", "when",
    }

    words = re.findall(r'\b[a-zA-Z]{4,}\b', " ".join(df["sentence"].tolist()))
    words = [w.lower() for w in words if w.lower() not in stopwords]
    return [w for w, _ in Counter(words).most_common(top_n)]


def detect_topic(df: pd.DataFrame, keywords: list[str]) -> str:
    """Very simple topic detection from keywords."""
    topic_map = {
        ("school", "uniforms", "students", "education", "teachers", "class"):       "Education",
        ("climate", "environment", "carbon", "fossil", "renewable", "emissions"):   "Climate / Environment",
        ("technology", "internet", "social", "media", "digital", "online"):         "Technology / Social Media",
        ("health", "medical", "disease", "hospital", "mental", "physical"):          "Health",
        ("economy", "trade", "gdp", "inflation", "poverty", "wealth"):               "Economics",
        ("government", "policy", "law", "political", "democracy", "rights"):         "Politics / Governance",
        ("gender", "race", "discrimination", "equality", "diversity"):               "Social Justice",
        ("war", "conflict", "military", "peace", "weapons"):                         "War / Conflict",
    }
    kw_set = set(keywords)
    best_topic, best_overlap = "General Argument", 0
    for topic_kws, topic_name in topic_map.items():
        overlap = len(kw_set & set(topic_kws))
        if overlap > best_overlap:
            best_overlap = overlap
            best_topic = topic_name
    return best_topic
