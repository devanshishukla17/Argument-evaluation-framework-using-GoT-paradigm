"""
got_engine.py — True Graph-of-Thought (GoT) reasoning engine.

Generates multiple reasoning branches, scores each on confidence /
diversity / completeness, merges them, and produces a final verdict.
"""

from __future__ import annotations
import math
import pandas as pd


# ---------------------------------------------------------------------------
# Branch generation helpers
# ---------------------------------------------------------------------------

def _short(text: str, max_len: int = 55) -> str:
    return text[:max_len] + "…" if len(text) > max_len else text


def generate_branches(df: pd.DataFrame) -> list[dict]:
    branches: list[dict] = []

    claims        = df[df["category"].isin(["Claim","Position","Unsupported Claim"])]["sentence"].tolist()
    evidence      = df[df["category"].isin(["Evidence","Strong Evidence","Supporting Fact"])]["sentence"].tolist()
    weak_ev       = df[df["category"] == "Weak Evidence"]["sentence"].tolist()
    counterclaims = df[df["category"] == "Counterclaim"]["sentence"].tolist()
    rebuttals     = df[df["category"] == "Rebuttal"]["sentence"].tolist()
    assumptions   = df[df["category"].isin(["Assumption","Premise"])]["sentence"].tolist()
    effects       = df[df["category"] == "Cause-Effect Relation"]["sentence"].tolist()
    conclusions   = df[df["category"] == "Concluding Statement"]["sentence"].tolist()

    # ── Branch 1: Main Causal / Support Branch ────────────────────────────────
    if claims:
        steps = []
        for i, claim in enumerate(claims[:3]):
            steps.append({"id":f"b0_c{i}","label":_short(claim),"category":"Claim","confidence":0.75})
            if i < len(evidence):
                steps.append({"id":f"b0_e{i}","label":_short(evidence[i]),"category":"Evidence","confidence":0.82})
            if i < len(effects):
                steps.append({"id":f"b0_ef{i}","label":_short(effects[i]),"category":"Cause-Effect Relation","confidence":0.70})
        if conclusions:
            steps.append({"id":"b0_conc","label":_short(conclusions[0]),"category":"Concluding Statement","confidence":0.88})
        conf  = _avg_confidence(steps)
        compl = _completeness(steps, df)
        branches.append({"name":"Main Argument Chain","description":"Follows the primary claims through evidence toward the conclusion.",
                          "steps":steps,"branch_type":"causal",
                          "scores":{"confidence":conf,"completeness":compl,"diversity":0.4,
                                    "overall":round((conf+compl+0.4)/3,3)}})

    # ── Branch 2: Adversarial (Debate) Branch ─────────────────────────────────
    if counterclaims:
        steps = []
        if claims:
            steps.append({"id":"b1_pos","label":_short(claims[0]),"category":"Claim","confidence":0.72})
        for i, cc in enumerate(counterclaims[:2]):
            steps.append({"id":f"b1_cc{i}","label":_short(cc),"category":"Counterclaim","confidence":0.68})
            if i < len(rebuttals):
                steps.append({"id":f"b1_r{i}","label":_short(rebuttals[i]),"category":"Rebuttal","confidence":0.71})
        if conclusions:
            steps.append({"id":"b1_conc","label":_short(conclusions[-1]),"category":"Concluding Statement","confidence":0.80})
        conf  = _avg_confidence(steps)
        compl = _completeness(steps, df)
        div   = 0.75
        branches.append({"name":"Debate / Adversarial Branch","description":"Explores the strongest opposing arguments and how the essay addresses them.",
                          "steps":steps,"branch_type":"adversarial",
                          "scores":{"confidence":conf,"completeness":compl,"diversity":div,
                                    "overall":round((conf+compl+div)/3,3)}})

    # ── Branch 3: Assumption / Hidden Premise Branch ──────────────────────────
    if assumptions or (df.get("missing_evidence") is not None and df["missing_evidence"].any()):
        steps = []
        if claims:
            steps.append({"id":"b2_c0","label":_short(claims[0]),"category":"Claim","confidence":0.65})
        for i, a in enumerate(assumptions[:2]):
            steps.append({"id":f"b2_a{i}","label":_short(a),"category":"Assumption","confidence":0.58})
        missing_rows = df[df["missing_evidence"]==True].head(2)
        for i,(_, row) in enumerate(missing_rows.iterrows()):
            steps.append({"id":f"b2_me{i}","label":"⚠ Missing evidence for: "+_short(row["sentence"],40),
                          "category":"Missing Evidence","confidence":0.3})
        conf  = _avg_confidence(steps)
        compl = 0.45
        div   = 0.60
        branches.append({"name":"Hidden Assumption Branch","description":"Surfaces implicit assumptions and evidence gaps.",
                          "steps":steps,"branch_type":"assumption",
                          "scores":{"confidence":conf,"completeness":compl,"diversity":div,
                                    "overall":round((conf+compl+div)/3,3)}})

    # ── Branch 4: Evidence Quality Branch ────────────────────────────────────
    strong = df[df["category"]=="Strong Evidence"]["sentence"].tolist()
    ev_steps = []
    for i,s in enumerate(strong[:2]):
        ev_steps.append({"id":f"b3_se{i}","label":_short(s),"category":"Strong Evidence","confidence":0.90})
    for i,w in enumerate(weak_ev[:2]):
        ev_steps.append({"id":f"b3_we{i}","label":_short(w),"category":"Weak Evidence","confidence":0.45})
    if ev_steps:
        conf  = _avg_confidence(ev_steps)
        compl = 0.50; div = 0.55
        branches.append({"name":"Evidence Quality Audit","description":"Distinguishes strong peer-reviewed evidence from weak anecdotal claims.",
                          "steps":ev_steps,"branch_type":"evidential",
                          "scores":{"confidence":conf,"completeness":compl,"diversity":div,
                                    "overall":round((conf+compl+div)/3,3)}})

    if not branches:
        all_sents = df["sentence"].tolist()[:5]
        branches.append({"name":"Linear Argument Thread","description":"Sequential reading of the main argument.",
                          "steps":[{"id":f"fb_{i}","label":_short(s),"category":"Supporting Fact","confidence":0.5}
                                    for i,s in enumerate(all_sents)],
                          "branch_type":"causal",
                          "scores":{"confidence":0.5,"completeness":0.5,"diversity":0.3,"overall":0.43}})
    return branches


def _avg_confidence(steps: list[dict]) -> float:
    if not steps: return 0.5
    return round(sum(s["confidence"] for s in steps)/len(steps), 3)


def _completeness(steps: list[dict], df: pd.DataFrame) -> float:
    key_types = {"Claim","Evidence","Counterclaim","Rebuttal","Concluding Statement"}
    step_types = {s["category"] for s in steps}
    present_in_essay = set(df["category"].unique())
    available_keys = key_types & present_in_essay
    if not available_keys: return 0.5
    return round(len(step_types & available_keys)/len(available_keys), 3)


def rank_branches(branches: list[dict]) -> list[dict]:
    return sorted(branches, key=lambda b: b["scores"]["overall"], reverse=True)


def merge_branches(branches: list[dict]) -> dict:
    if not branches: return {}
    ranked = rank_branches(branches)
    merged_steps: list[dict] = []
    seen: set = set()
    for branch in ranked:
        for step in branch["steps"]:
            key = step["label"][:40]
            if key not in seen and step["confidence"] >= 0.5:
                merged_steps.append(step); seen.add(key)
            if len(merged_steps) >= 8: break
        if len(merged_steps) >= 8: break
    avg_conf  = _avg_confidence(merged_steps)
    avg_compl = sum(b["scores"]["completeness"] for b in branches)/len(branches)
    avg_div   = sum(b["scores"]["diversity"] for b in branches)/len(branches)
    return {"name":"Synthesised Best Path","description":"Merged from highest-confidence steps across all branches.",
            "steps":merged_steps,"branch_type":"synthesis",
            "scores":{"confidence":round(avg_conf,3),"completeness":round(avg_compl,3),
                      "diversity":round(avg_div,3),"overall":round((avg_conf+avg_compl+avg_div)/3,3)}}


def generate_final_verdict(branches: list[dict], stats: dict) -> dict:
    ranked = rank_branches(branches)
    best   = ranked[0] if ranked else {}
    worst  = ranked[-1] if ranked else {}

    total    = stats.get("total_sentences", 1)
    ev_cnt   = stats.get("evidence_count", 0)
    unsup    = stats.get("unsupported_count", 0)
    cc_cnt   = stats.get("counterclaim_count", 0)
    reb_cnt  = stats.get("rebuttal_count", 0)
    fall_cnt = stats.get("fallacy_count", 0)
    strong   = stats.get("strong_evidence_count", 0)
    weak_ev  = stats.get("weak_evidence_count", 0)
    missing  = stats.get("missing_evidence_count", 0)

    strengths, weaknesses, improvements = [], [], []

    if strong >= 2:          strengths.append("Uses strong, cited evidence to back key claims.")
    elif ev_cnt >= 3:        strengths.append("Several evidence units support the argument.")
    if cc_cnt >= 1:          strengths.append("Acknowledges opposing viewpoints.")
    if reb_cnt >= 1:         strengths.append("Rebuttals strengthen the author's position.")
    if unsup == 0:           strengths.append("All main claims appear to be supported.")
    if fall_cnt == 0:        strengths.append("No obvious logical fallacies detected.")

    if unsup >= 2:           weaknesses.append(f"{unsup} unsupported claim(s) significantly reduce credibility.")
    if fall_cnt >= 1:        weaknesses.append(f"{fall_cnt} logical fallacy/fallacies detected (e.g. 'everyone knows', slippery slope).")
    if weak_ev >= 2:         weaknesses.append(f"{weak_ev} anecdotal/opinion-based evidence units — replace with data.")
    if missing >= 2:         weaknesses.append(f"{missing} claim(s) have no supporting evidence in nearby sentences.")
    if cc_cnt == 0:          weaknesses.append("No counterclaims — essay ignores opposing arguments entirely.")
    if reb_cnt == 0 and cc_cnt >= 1: weaknesses.append("Counterclaims raised but not rebutted.")
    if ev_cnt < 2:           weaknesses.append("Very little evidence — the argument relies almost entirely on assertion.")
    if strong == 0 and ev_cnt > 0: weaknesses.append("No strong (cited/statistical) evidence — all evidence is weak or anecdotal.")

    if not strengths:        strengths.append("Essay states a clear position.")
    if not weaknesses:       weaknesses.append("No major structural weaknesses detected.")

    if unsup > 0:            improvements.append("Back every claim with a specific statistic, study, or named source.")
    if cc_cnt == 0:          improvements.append("Add at least one counterclaim and rebut it — this shows critical thinking.")
    if fall_cnt > 0:         improvements.append("Remove phrases like 'everyone knows' or 'obviously' — replace with evidence.")
    if weak_ev > 0:          improvements.append("Replace anecdotal evidence ('my friend said', 'I think') with peer-reviewed sources.")
    if missing > 0:          improvements.append("Ensure every claim paragraph ends with supporting evidence.")
    improvements.append("Use transitional phrases between paragraphs to improve logical flow.")

    overall_score = _compute_overall_score(stats, ranked)

    return {
        "verdict_text":  _verdict_summary(overall_score),
        "overall_score": overall_score,
        "strengths":     strengths,
        "weaknesses":    weaknesses,
        "improvements":  improvements,
        "best_branch":   best.get("name",""),
        "best_score":    best.get("scores",{}).get("overall",0.0),
        "weak_branch":   worst.get("name",""),
        "weak_score":    worst.get("scores",{}).get("overall",0.0),
    }


def _verdict_summary(score: float) -> str:
    if score >= 8.0:
        return "**Strong Argument** — Well-structured, evidence-rich, and logically sound."
    elif score >= 6.5:
        return "**Good Argument** — Solid foundation with minor gaps in evidence or counterargument coverage."
    elif score >= 5.0:
        return "**Moderate Argument** — Has a clear position but needs more evidence and fewer unsupported claims."
    elif score >= 3.5:
        return "**Developing Argument** — The position is stated but the argument lacks evidence, logic, and structure."
    elif score >= 2.0:
        return "**Weak Argument** — Relies heavily on assertion, fallacies, and anecdote. Substantial revision needed."
    else:
        return "**Very Weak Argument** — Little to no evidence, multiple fallacies, no engagement with counterarguments."


def _compute_overall_score(stats: dict, ranked_branches: list[dict]) -> float:
    """
    Rubric-based scoring out of 10. Each dimension contributes a bounded portion.
    Designed so a weak essay (no citations, fallacies, no counterclaims) scores 1–3
    and a strong essay (cited evidence, rebuttals, no fallacies) scores 7–10.
    """
    total    = max(stats.get("total_sentences", 1), 1)
    ev_cnt   = stats.get("evidence_count", 0)
    strong   = stats.get("strong_evidence_count", 0)
    weak_ev  = stats.get("weak_evidence_count", 0)
    unsup    = stats.get("unsupported_count", 0)
    fall_cnt = stats.get("fallacy_count", 0)
    cc_cnt   = stats.get("counterclaim_count", 0)
    reb_cnt  = stats.get("rebuttal_count", 0)
    missing  = stats.get("missing_evidence_count", 0)
    claim_cnt = max(stats.get("claim_count", 1), 1)

    # ── 1. Evidence Quality (max 3.0) ────────────────────────────────────────
    # Strong evidence (cited/statistical) = 0.6 pts each, cap 2.4
    # Plain evidence = 0.25 pts each
    # Weak/anecdotal evidence = 0.05 pts each (barely counts)
    plain_ev = max(0, ev_cnt - strong - weak_ev)
    ev_score = min(3.0,
        strong  * 0.60 +
        plain_ev * 0.25 +
        weak_ev * 0.05
    )

    # ── 2. Evidence Coverage (max 2.0) ───────────────────────────────────────
    # What fraction of claims have supporting evidence?
    supported_claims = max(0, claim_cnt - unsup - missing)
    coverage = supported_claims / claim_cnt
    coverage_score = coverage * 2.0

    # ── 3. Counterargument Engagement (max 2.0) ───────────────────────────────
    if cc_cnt == 0:
        cc_score = 0.0          # no engagement at all
    elif reb_cnt == 0:
        cc_score = cc_cnt * 0.5 # raised but not rebutted
        cc_score = min(1.0, cc_score)
    else:
        cc_score = min(2.0, cc_cnt * 0.7 + reb_cnt * 0.6)

    # ── 4. Logical Integrity (max 2.0) ───────────────────────────────────────
    # Start at 2.0, subtract for fallacies and unsupported claims
    logic_score = 2.0
    logic_score -= fall_cnt * 0.6      # each fallacy costs 0.6
    logic_score -= unsup * 0.35        # each unsupported claim costs 0.35
    logic_score -= missing * 0.20      # each missing evidence gap costs 0.2
    logic_score = max(0.0, logic_score)

    # ── 5. Structure & Argument Quality (max 1.0) ────────────────────────────
    # Based on best branch overall score
    branch_quality = ranked_branches[0]["scores"]["overall"] if ranked_branches else 0.4
    structure_score = branch_quality * 1.0  # maps 0–1 → 0–1

    # ── Total ─────────────────────────────────────────────────────────────────
    raw = ev_score + coverage_score + cc_score + logic_score + structure_score
    # raw is out of 10 (3 + 2 + 2 + 2 + 1)

    # Hard floor/ceiling
    return round(min(10.0, max(1.0, raw)), 1)
