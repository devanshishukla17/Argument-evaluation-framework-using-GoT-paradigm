"""
devil_agents.py — Devil's Advocate critique agents.

Seven specialised agents analyse the essay from adversarial perspectives.
Each agent returns structured findings with teacher & student explanations.
"""

from __future__ import annotations
import re
import pandas as pd


# ---------------------------------------------------------------------------
# Base agent helper
# ---------------------------------------------------------------------------

def _sentences_with_category(df: pd.DataFrame, categories: list[str]) -> list[str]:
    return df[df["category"].isin(categories)]["sentence"].tolist()


def _sentences_all(df: pd.DataFrame) -> list[str]:
    return df["sentence"].tolist()


# ---------------------------------------------------------------------------
# 1. Logical Devil
# ---------------------------------------------------------------------------

_FALLACY_PATTERNS = {
    "Ad Hominem":      r"(you are|they are|he is|she is).{0,30}(wrong|stupid|ignorant|foolish)",
    "Straw Man":       r"(the opposition|critics|opponents).{0,40}(claim|say|argue).{0,40}(extreme|ridiculous|impossible)",
    "False Dichotomy": r"(either|you must choose|only two options|there is no middle)",
    "Slippery Slope":  r"(will lead to|inevitably|eventually lead|next step will be|end up with)",
    "Hasty Generalisation": r"(all|every|none|never|always|no one|everyone).{0,30}(are|is|do|does|have|has)",
    "Circular Reasoning":   r"(because it is|is true because|is correct because it|proves itself)",
    "Appeal to Authority":  r"(experts say|scientists agree|everyone knows|all experts|studies prove)",
    "Post Hoc":        r"(after|followed by|since).{0,30}(therefore|caused|led to|resulted in)",
}

_CONTRADICTION_PAIRS = [
    (["always", "every", "all people"], ["sometimes", "few", "some people"]),
    (["never", "no one", "none"], ["often", "many", "most"]),
]


def logical_devil(df: pd.DataFrame) -> dict:
    """Detect logical fallacies, contradictions, circular reasoning."""
    findings = []
    sentences = _sentences_all(df)

    for sent in sentences:
        lower = sent.lower()
        for fallacy_name, pattern in _FALLACY_PATTERNS.items():
            if re.search(pattern, lower):
                findings.append({
                    "type":       "Logical Fallacy",
                    "subtype":    fallacy_name,
                    "sentence":   sent[:120],
                    "teacher_note": f"This sentence may contain a '{fallacy_name}' fallacy.",
                    "student_note": f"Tip: Avoid '{fallacy_name}' — strengthen this with specific evidence instead.",
                    "severity":   "high" if fallacy_name in ("Ad Hominem", "False Dichotomy") else "medium",
                })
                break  # one fallacy per sentence

    # Detect potential contradictions
    high_universals = [s for s in sentences if re.search(r'\b(always|all|every|never)\b', s.lower())]
    low_universals  = [s for s in sentences if re.search(r'\b(sometimes|few|rarely|some)\b', s.lower())]
    if high_universals and low_universals:
        findings.append({
            "type":     "Contradiction",
            "subtype":  "Quantifier Conflict",
            "sentence": high_universals[0][:120],
            "teacher_note": "The essay contains universal statements that may conflict with qualified ones.",
            "student_note": "Check: You use 'always/all' and 'sometimes/few' — make sure these don't contradict.",
            "severity": "medium",
        })

    # Unsupported claims
    unsup = df[df["category"] == "Unsupported Claim"]["sentence"].tolist()
    for sent in unsup:
        findings.append({
            "type":       "Unsupported Claim",
            "subtype":    "Missing Evidence",
            "sentence":   sent[:120],
            "teacher_note": "This claim lacks empirical support or citation.",
            "student_note": "Add evidence: a statistic, example, or expert quote to back this up.",
            "severity":   "high",
        })

    summary = (
        f"Found {len([f for f in findings if f['type']=='Logical Fallacy'])} logical fallacy/fallacies, "
        f"{len([f for f in findings if f['type']=='Unsupported Claim'])} unsupported claim(s), "
        f"and {len([f for f in findings if f['type']=='Contradiction'])} potential contradiction(s)."
    )

    return {"agent": "Logical Devil", "icon": "⚖️", "findings": findings,
            "summary": summary, "count": len(findings)}


# ---------------------------------------------------------------------------
# 2. Ethical Devil
# ---------------------------------------------------------------------------

_ETHICS_PATTERNS = {
    "Discrimination":   r"(women|men|race|religion|nationality|age|gender|disabled).{0,30}(are|is|should|cannot|must)",
    "Harmful Framing":  r"(inferior|superior|should be removed|must be eliminated|deserve to)",
    "Moral Claim":      r"(it is immoral|morally wrong|ethically unacceptable|sin|evil|wicked)",
    "Fairness Concern": r"(only|just|merely|simply).{0,20}(the rich|the poor|minorities|majority)",
}


def ethical_devil(df: pd.DataFrame) -> dict:
    findings = []
    for _, row in df.iterrows():
        lower = row["sentence"].lower()
        for issue, pattern in _ETHICS_PATTERNS.items():
            if re.search(pattern, lower):
                findings.append({
                    "type":       "Ethical Concern",
                    "subtype":    issue,
                    "sentence":   row["sentence"][:120],
                    "teacher_note": f"Ethical issue detected: {issue}. This may need clarification or removal.",
                    "student_note": f"Consider rewriting — this statement could be seen as unfair or biased ({issue}).",
                    "severity":   "high" if issue == "Discrimination" else "medium",
                })
                break

    summary = f"Identified {len(findings)} potential ethical concern(s) in the essay."
    return {"agent": "Ethical Devil", "icon": "🧭", "findings": findings,
            "summary": summary, "count": len(findings)}


# ---------------------------------------------------------------------------
# 3. Domain Devil
# ---------------------------------------------------------------------------

_DOMAIN_INDICATORS = {
    "Science":   r"(evolution|climate change|vaccination|quantum|dna|genome|experiment)",
    "History":   r"(world war|revolution|century|ancient|medieval|colonial|empire)",
    "Law":       r"(legal|illegal|law|statute|constitution|court|rights|regulation)",
    "Economics": r"(gdp|inflation|market|supply|demand|trade|capital|revenue)",
    "Technology":r"(ai|algorithm|software|hardware|internet|blockchain|cybersecurity)",
}


def domain_devil(df: pd.DataFrame) -> dict:
    findings = []
    for _, row in df.iterrows():
        lower = row["sentence"].lower()
        for domain, pattern in _DOMAIN_INDICATORS.items():
            if re.search(pattern, lower) and not row["has_citation"] and not row["is_numeric"]:
                findings.append({
                    "type":       "Domain Gap",
                    "subtype":    domain,
                    "sentence":   row["sentence"][:120],
                    "teacher_note": f"Domain-specific claim in {domain} without a source.",
                    "student_note": f"This is a {domain.lower()} claim — add a credible source or data point.",
                    "severity":   "medium",
                })
                break

    summary = f"Found {len(findings)} domain-specific claim(s) lacking expert citation."
    return {"agent": "Domain Devil", "icon": "🔬", "findings": findings,
            "summary": summary, "count": len(findings)}


# ---------------------------------------------------------------------------
# 4. Cultural Devil
# ---------------------------------------------------------------------------

_BIAS_PATTERNS = {
    "Overgeneralisation": r"\b(all|every|universally|globally|no culture|every culture)\b",
    "Western Bias":       r"(developed countries|western|america|europe).{0,30}(better|superior|leading|advanced)",
    "Stereotype":         r"(men are|women are|teenagers are|young people are|old people are|the poor are)",
    "Cultural Narrowness":r"(our culture|our society|in this country).{0,30}(is the|are the|proves|shows)",
}


def cultural_devil(df: pd.DataFrame) -> dict:
    findings = []
    for _, row in df.iterrows():
        lower = row["sentence"].lower()
        for bias_type, pattern in _BIAS_PATTERNS.items():
            if re.search(pattern, lower):
                findings.append({
                    "type":       "Cultural Bias",
                    "subtype":    bias_type,
                    "sentence":   row["sentence"][:120],
                    "teacher_note": f"Potential {bias_type} detected. Consider broader perspectives.",
                    "student_note": f"Caution: '{bias_type}' — does your argument hold across different cultures?",
                    "severity":   "medium",
                })
                break

    summary = f"Detected {len(findings)} possible cultural bias/overgeneralisation instance(s)."
    return {"agent": "Cultural Devil", "icon": "🌍", "findings": findings,
            "summary": summary, "count": len(findings)}


# ---------------------------------------------------------------------------
# 5. Counterargument Devil
# ---------------------------------------------------------------------------

def counterargument_devil(df: pd.DataFrame) -> dict:
    """
    Generate the strongest possible opposing argument for each main claim.
    """
    findings = []
    claims = df[df["category"].isin(["Claim", "Position", "Unsupported Claim"])]["sentence"].tolist()

    counter_templates = [
        "However, one could argue the opposite: {claim_topic} may not hold in all contexts.",
        "Critics would counter that the evidence for '{claim_topic}' is circumstantial.",
        "A sceptic might note that '{claim_topic}' ignores important confounding variables.",
        "The opposing view holds that '{claim_topic}' is culturally specific, not universal.",
        "Research in other fields suggests '{claim_topic}' oversimplifies a complex issue.",
    ]

    for i, claim in enumerate(claims[:5]):
        topic = claim[:50].rstrip(".!?,")
        template = counter_templates[i % len(counter_templates)]
        counter = template.format(claim_topic=topic)
        findings.append({
            "type":       "Counterargument",
            "subtype":    "Devil's Opposition",
            "sentence":   claim[:120],
            "counter":    counter,
            "teacher_note": f"Strongest counter to this claim: '{counter}'",
            "student_note": f"Consider addressing this objection: '{counter}'",
            "severity":   "low",
        })

    summary = f"Generated {len(findings)} strongest opposing argument(s) against your claims."
    return {"agent": "Counterargument Devil", "icon": "⚔️", "findings": findings,
            "summary": summary, "count": len(findings)}


# ---------------------------------------------------------------------------
# 6. Evidence Devil
# ---------------------------------------------------------------------------

def evidence_devil(df: pd.DataFrame) -> dict:
    findings = []

    # Flag weak evidence
    weak_ev = df[df["category"] == "Weak Evidence"]["sentence"].tolist()
    for sent in weak_ev:
        findings.append({
            "type":       "Weak Evidence",
            "subtype":    "Anecdotal / Opinion",
            "sentence":   sent[:120],
            "teacher_note": "Weak or anecdotal evidence. Should be replaced with data or citations.",
            "student_note": "Try replacing 'I think / people say' with a real study, statistic, or expert.",
            "severity":   "medium",
        })

    # Missing evidence flags
    missing = df[df["missing_evidence"] == True]["sentence"].tolist()
    for sent in missing[:5]:
        findings.append({
            "type":       "Missing Evidence",
            "subtype":    "Evidential Gap",
            "sentence":   sent[:120],
            "teacher_note": "Claim without supporting evidence.",
            "student_note": "This claim needs evidence — what data, study, or example backs it up?",
            "severity":   "high",
        })

    # Good evidence (positive notes)
    strong = df[df["category"] == "Strong Evidence"]["sentence"].tolist()
    for sent in strong[:3]:
        findings.append({
            "type":       "Strong Evidence",
            "subtype":    "Citation / Statistic",
            "sentence":   sent[:120],
            "teacher_note": "Well-supported with strong evidence. ✓",
            "student_note": "Great! This claim is backed by solid evidence.",
            "severity":   "none",
        })

    summary = (
        f"{len(weak_ev)} weak evidence segment(s), "
        f"{len(missing)} unsupported claim(s), "
        f"{len(strong)} well-evidenced segment(s)."
    )
    return {"agent": "Evidence Devil", "icon": "🔍", "findings": findings,
            "summary": summary, "count": len(findings)}


# ---------------------------------------------------------------------------
# 7. Pedagogy Devil
# ---------------------------------------------------------------------------

_CLARITY_PATTERNS = [
    (r"(it|this|that|they|these)\b.{0,20}(is|are|was|were)\b", "Vague pronoun reference"),
    (r"\b(very|really|quite|rather|somewhat|a bit|sort of)\b", "Hedging / filler words"),
    (r".{150,}", "Very long sentence — consider splitting"),
    (r"\b(said|told|stated|noted)\b.{0,15}that", "Weak attribution verb"),
    (r"(etc\.|and so on|and more)", "Trailing list — be specific"),
]

_STRUCTURE_NOTES = [
    "Ensure each paragraph begins with a clear topic sentence.",
    "Use transitional phrases between sections (e.g., 'Furthermore,', 'In contrast,').",
    "The introduction should clearly state the thesis.",
    "The conclusion should synthesise — not just restate — the main argument.",
    "Consider using sub-headings for complex arguments.",
]


def pedagogy_devil(df: pd.DataFrame) -> dict:
    findings = []

    for _, row in df.iterrows():
        sent = row["sentence"]
        for pattern, note in _CLARITY_PATTERNS:
            if re.search(pattern, sent.lower() if "pronoun" in note.lower() else sent):
                findings.append({
                    "type":       "Clarity Issue",
                    "subtype":    note,
                    "sentence":   sent[:120],
                    "teacher_note": f"Clarity concern: {note}.",
                    "student_note": f"Writing tip: {note}. Rewrite for clarity.",
                    "severity":   "low",
                })
                break

    # Add structural suggestions
    for note in _STRUCTURE_NOTES:
        findings.append({
            "type":       "Structure Suggestion",
            "subtype":    "Organisation",
            "sentence":   "",
            "teacher_note": note,
            "student_note": note,
            "severity":   "info",
        })

    summary = f"Found {len([f for f in findings if f['type']=='Clarity Issue'])} clarity issue(s) and {len(_STRUCTURE_NOTES)} structural suggestions."
    return {"agent": "Pedagogy Devil", "icon": "📚", "findings": findings,
            "summary": summary, "count": len(findings)}


# ---------------------------------------------------------------------------
# Master runner
# ---------------------------------------------------------------------------

def run_all_agents(df: pd.DataFrame) -> dict:
    """Run all seven Devil's Advocate agents and return combined results."""
    agents = {
        "logical":       logical_devil(df),
        "ethical":       ethical_devil(df),
        "domain":        domain_devil(df),
        "cultural":      cultural_devil(df),
        "counterargument": counterargument_devil(df),
        "evidence":      evidence_devil(df),
        "pedagogy":      pedagogy_devil(df),
    }

    total_issues = sum(a["count"] for a in agents.values())
    high_sev = sum(
        len([f for f in a["findings"] if f.get("severity") == "high"])
        for a in agents.values()
    )

    # Synthesis
    synthesis = []
    if high_sev >= 3:
        synthesis.append(f"🚨 {high_sev} high-severity issues detected. Significant revision recommended.")
    elif high_sev >= 1:
        synthesis.append(f"⚠️ {high_sev} high-severity issue(s) detected. Targeted revision needed.")
    else:
        synthesis.append("✅ No high-severity issues detected. Minor improvements suggested.")

    synthesis.append(f"📊 Total critique items across all agents: {total_issues}")

    agents["synthesis"] = {
        "total_issues":   total_issues,
        "high_severity":  high_sev,
        "summary_points": synthesis,
    }

    return agents
