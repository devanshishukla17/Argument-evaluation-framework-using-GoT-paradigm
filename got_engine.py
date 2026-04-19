"""
got_engine.py — TRUE Graph-of-Thought (GoT) engine using the Claude API.

What makes this REAL GoT (Besta et al., 2023):
  1. GENERATE   — LLM independently generates N thought nodes (reasoning perspectives)
                  without knowing about the others.
  2. SCORE      — LLM scores each node for logical validity, evidence quality, completeness.
  3. AGGREGATE  — High-scoring nodes are connected into a graph; the LLM then reasons
                  OVER that graph structure to produce a synthesised verdict.
  4. REFINE     — The LLM is shown the aggregated graph and asked to identify the single
                  strongest reasoning path and fill any remaining gaps.

This replaces the old fake GoT (hardcoded branch templates with hardcoded confidence values).

Scoring follows the Toulmin Argumentation Model (Toulmin, 1958):
  T1 Claim Clarity (0-3), T2 Evidence Quality (0-4), T3 Warrant/Reasoning (0-3),
  T4 Counterargument (0-2), T5 Rebuttal Quality (0-2), T6 Structural Cohesion (0-2)
  Total raw 0-16, normalised to 0-10.
"""

from __future__ import annotations
import json
import re
import time
import os
import pandas as pd
from groq import Groq

# ---------------------------------------------------------------------------
# Claude client
# ---------------------------------------------------------------------------
_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
_MODEL = "llama-3.3-70b-versatile"


def _short(text: str, max_len: int = 55) -> str:
    return text[:max_len] + "..." if len(text) > max_len else text


def _call_groq(system: str, user: str, max_tokens: int = 1200) -> str:
    for attempt in range(2):
        try:
            msg = _client.chat.completions.create(
                model=_MODEL,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user}
                ],
                max_tokens=max_tokens,
                temperature=0.3
            )

            return msg.choices[0].message.content.strip()

        except Exception as e:
            if attempt == 0:
                time.sleep(1)
            else:
                raise RuntimeError(f"Groq API error: {e}") from e

    return ""


def _parse_json(text: str):
    text = re.sub(r"```(?:json)?", "", text).replace("```", "").strip()
    start = min(
        (text.find("{") if "{" in text else len(text)),
        (text.find("[") if "[" in text else len(text)),
    )
    if start == len(text):
        return {}
    try:
        return json.loads(text[start:])
    except json.JSONDecodeError:
        for op, cl in [("{", "}"), ("[", "]")]:
            if op in text:
                s = text.find(op)
                e = text.rfind(cl)
                if e > s:
                    try:
                        return json.loads(text[s:e+1])
                    except Exception:
                        pass
        return {}


# ===========================================================================
# STEP 1 — GENERATE: LLM produces independent thought nodes
# ===========================================================================

_GENERATE_SYSTEM = """You are an expert argument analyst. Analyse essays by generating
INDEPENDENT reasoning branches. Each branch examines the essay from a completely different
analytical perspective. Return ONLY valid JSON, no prose before or after."""

_GENERATE_USER = """Analyse this essay from 4 INDEPENDENT reasoning perspectives:

1. "Causal Chain"     - trace the main claim -> evidence -> conclusion logical flow
2. "Adversarial"      - focus on counterarguments, rebuttals, and dialectic strength
3. "Assumption Audit" - surface hidden premises the argument silently depends on
4. "Evidence Quality" - audit strength of evidence (strong/weak/missing)

Essay:
\"\"\"{essay}\"\"\"

Discourse summary: {discourse_summary}

Return a JSON array of 4 branch objects:
[{{
  "name": "<branch name>",
  "branch_type": "<causal|adversarial|assumption|evidential>",
  "description": "<one sentence>",
  "thought_nodes": [
    {{
      "node_id": "<type>_<index>",
      "thought": "<the actual reasoning step>",
      "category": "<Claim|Evidence|Counterclaim|Rebuttal|Assumption|Missing Evidence|Strong Evidence|Weak Evidence|Concluding Statement>",
      "sentence_ref": "<quoted fragment max 60 chars from essay, or empty>",
      "raw_confidence": <0.0-1.0>
    }}
  ]
}}]
Each branch must have 3-6 thought nodes."""


def _generate_thought_nodes(essay: str, df: pd.DataFrame) -> list[dict]:
    counts = df["category"].value_counts().to_dict()
    discourse_summary = "; ".join(f"{k}: {v}" for k, v in counts.items())
    prompt = _GENERATE_USER.format(essay=essay[:3000], discourse_summary=discourse_summary)
    raw = _call_groq(_GENERATE_SYSTEM, prompt, max_tokens=2000)
    parsed = _parse_json(raw)
    if isinstance(parsed, list):
        return parsed
    if isinstance(parsed, dict) and "branches" in parsed:
        return parsed["branches"]
    return []


# ===========================================================================
# STEP 2 — SCORE: LLM scores each thought node
# ===========================================================================

_SCORE_SYSTEM = """You are a rigorous argumentation judge. Score reasoning nodes
from essay analysis. Return ONLY valid JSON."""

_SCORE_USER = """Score each thought node on three dimensions (0.0-1.0 each):
- logical_validity: Is the reasoning step logically sound?
- evidence_support: Is this node grounded in actual essay content?
- completeness:     Does this node fully capture the aspect it targets?

Nodes to score:
{nodes_json}

Return JSON array:
[{{"node_id": "<id>", "logical_validity": <float>, "evidence_support": <float>,
   "completeness": <float>, "score_note": "<one sentence justification>"}}]"""


def _score_thought_nodes(branches: list[dict]) -> dict[str, dict]:
    all_nodes = []
    for branch in branches:
        for node in branch.get("thought_nodes", []):
            all_nodes.append({
                "node_id": node.get("node_id", ""),
                "thought": node.get("thought", "")[:200],
                "category": node.get("category", ""),
                "raw_confidence": node.get("raw_confidence", 0.5),
            })
    if not all_nodes:
        return {}
    raw = _call_groq(_SCORE_SYSTEM,
                       _SCORE_USER.format(nodes_json=json.dumps(all_nodes, indent=2)),
                       max_tokens=1500)
    parsed = _parse_json(raw)
    scores: dict[str, dict] = {}
    if isinstance(parsed, list):
        for item in parsed:
            nid = item.get("node_id", "")
            if nid:
                scores[nid] = item
    return scores


# ===========================================================================
# STEP 3 — AGGREGATE: LLM reasons OVER the scored graph
# ===========================================================================

_AGG_SYSTEM = """You are a master argument synthesiser. You receive a scored
Graph-of-Thought and reason OVER the graph to produce a holistic synthesis.
Return ONLY valid JSON."""

_AGG_USER = """Reason OVER this scored Graph-of-Thought (multiple branches, each with
independently scored nodes) to identify:
1. Which reasoning paths are strongest end-to-end
2. Where branches REINFORCE each other (convergent evidence)
3. Where branches CONTRADICT each other (conflicting signals)
4. What the graph as a whole reveals about essay quality

Scored GoT graph:
{got_graph_json}

Return JSON:
{{
  "cross_branch_insights": ["<insight about branch relationships>"],
  "convergent_signals": ["<thing multiple branches agree on>"],
  "contradictory_signals": ["<thing branches disagree on>"],
  "graph_level_verdict": "<2-3 sentence synthesis of what the WHOLE graph reveals>",
  "strongest_path_ids": ["<node_ids of highest-value chain across branches>"],
  "aggregation_confidence": <0.0-1.0>
}}"""


def _aggregate_over_graph(branches: list[dict], node_scores: dict) -> dict:
    got_graph = []
    for branch in branches:
        scored_nodes = []
        for node in branch.get("thought_nodes", []):
            nid = node.get("node_id", "")
            sc = node_scores.get(nid, {})
            composite = (
                sc.get("logical_validity", 0.5) * 0.4
                + sc.get("evidence_support", 0.5) * 0.4
                + sc.get("completeness", 0.5) * 0.2
            )
            scored_nodes.append({
                "node_id": nid,
                "thought": node.get("thought", "")[:150],
                "category": node.get("category", ""),
                "composite_score": round(composite, 3),
                "score_note": sc.get("score_note", ""),
            })
        got_graph.append({
            "name": branch.get("name", ""),
            "branch_type": branch.get("branch_type", ""),
            "description": branch.get("description", ""),
            "scored_nodes": scored_nodes,
        })
    raw = _call_groq(_AGG_SYSTEM,
                       _AGG_USER.format(got_graph_json=json.dumps(got_graph, indent=2)),
                       max_tokens=1000)
    parsed = _parse_json(raw)
    return parsed if isinstance(parsed, dict) else {}


# ===========================================================================
# STEP 4 — REFINE: LLM produces final Toulmin verdict
# ===========================================================================

_REFINE_SYSTEM = """You are a final-stage essay evaluator with access to a complete
Graph-of-Thought analysis. Produce the definitive scoring and feedback.
Return ONLY valid JSON."""

_REFINE_USER = """Final REFINEMENT step of Graph-of-Thought essay evaluation.

Score using the Toulmin rubric:
  T1 Claim Clarity (0-3): is thesis specific and arguable?
  T2 Evidence Quality (0-4): are claims backed by credible evidence?
  T3 Warrant/Reasoning (0-3): is the logical connection explained?
  T4 Counterargument (0-2): does essay acknowledge opposing views?
  T5 Rebuttal Quality (0-2): are counterarguments effectively rebutted?
  T6 Structural Cohesion (0-2): is argument organised and coherent?

GoT synthesis:
{aggregation_json}

Discourse stats:
{stats_json}

Top nodes by score:
{top_nodes_json}

Return JSON:
{{
  "toulmin_scores": {{
    "T1_claim_clarity":       {{"raw": <0-3>, "note": "<justification>"}},
    "T2_evidence_quality":    {{"raw": <0-4>, "note": "<justification>"}},
    "T3_warrant_reasoning":   {{"raw": <0-3>, "note": "<justification>"}},
    "T4_counterargument":     {{"raw": <0-2>, "note": "<justification>"}},
    "T5_rebuttal_quality":    {{"raw": <0-2>, "note": "<justification>"}},
    "T6_structural_cohesion": {{"raw": <0-2>, "note": "<justification>"}}
  }},
  "overall_score": <0.0-10.0>,
  "verdict_text": "<2-3 sentence overall verdict>",
  "strengths": ["<strength 1>", "<strength 2>", "<strength 3>"],
  "weaknesses": ["<weakness 1>", "<weakness 2>"],
  "improvements": ["<improvement 1>", "<improvement 2>", "<improvement 3>"],
  "got_synthesis_note": "<one sentence on what GoT revealed beyond single-pass analysis>"
}}"""


def _refine_verdict(aggregation: dict, branches: list[dict],
                    node_scores: dict, stats: dict) -> dict:
    all_scored = []
    for branch in branches:
        for node in branch.get("thought_nodes", []):
            nid = node.get("node_id", "")
            sc = node_scores.get(nid, {})
            composite = (
                sc.get("logical_validity", 0.5) * 0.4
                + sc.get("evidence_support", 0.5) * 0.4
                + sc.get("completeness", 0.5) * 0.2
            )
            all_scored.append({
                "node_id": nid, "branch": branch.get("name", ""),
                "thought": node.get("thought", "")[:120],
                "composite": round(composite, 3),
            })
    top_nodes = sorted(all_scored, key=lambda x: x["composite"], reverse=True)[:8]
    raw = _call_groq(
        _REFINE_SYSTEM,
        _REFINE_USER.format(
            aggregation_json=json.dumps(aggregation, indent=2),
            stats_json=json.dumps(stats, indent=2),
            top_nodes_json=json.dumps(top_nodes, indent=2),
        ),
        max_tokens=1500,
    )
    parsed = _parse_json(raw)
    return parsed if isinstance(parsed, dict) else {}


# ===========================================================================
# PUBLIC API
# ===========================================================================

def run_got_pipeline(essay: str, df: pd.DataFrame, stats: dict) -> dict:
    """
    Execute the full 4-step Graph-of-Thought pipeline:
      1. Generate thought nodes (LLM)
      2. Score each node (LLM)
      3. Aggregate over the graph (LLM)
      4. Refine to final verdict (LLM)
    Returns a dict compatible with the existing app.py session state.
    """
    raw_branches = _generate_thought_nodes(essay, df)
    if not raw_branches:
        return _fallback_result(stats, df)

    node_scores = _score_thought_nodes(raw_branches)
    branches    = _annotate_branches(raw_branches, node_scores)
    aggregation = _aggregate_over_graph(branches, node_scores)
    refinement  = _refine_verdict(aggregation, branches, node_scores, stats)

    return _build_result(branches, node_scores, aggregation, refinement, stats, df)


def _annotate_branches(raw_branches: list[dict], node_scores: dict) -> list[dict]:
    annotated = []
    for branch in raw_branches:
        nodes = branch.get("thought_nodes", [])
        composites = []
        enriched = []
        for node in nodes:
            nid = node.get("node_id", "")
            sc = node_scores.get(nid, {})
            composite = (
                sc.get("logical_validity", node.get("raw_confidence", 0.5)) * 0.4
                + sc.get("evidence_support", node.get("raw_confidence", 0.5)) * 0.4
                + sc.get("completeness", node.get("raw_confidence", 0.5)) * 0.2
            )
            composites.append(composite)
            enriched.append({
                **node,
                "label":      node.get("thought", "")[:55],
                "confidence": round(composite, 3),
                "scores":     sc,
            })
        avg_conf = round(sum(composites) / max(len(composites), 1), 3)
        key_types = {"Claim", "Evidence", "Counterclaim", "Rebuttal", "Concluding Statement"}
        step_types = {n.get("category", "") for n in nodes}
        completeness = round(len(step_types & key_types) / max(len(key_types), 1), 3)
        diversity = round(min(1.0, len(step_types) / 5.0), 3)
        overall = round((avg_conf + completeness + diversity) / 3, 3)
        annotated.append({
            **branch,
            "steps": enriched,
            "scores": {
                "confidence": avg_conf, "completeness": completeness,
                "diversity": diversity, "overall": overall,
            },
        })
    return annotated


def _build_result(branches, node_scores, aggregation, refinement, stats, df) -> dict:
    ranked = sorted(branches, key=lambda b: b["scores"]["overall"], reverse=True)
    best   = ranked[0] if ranked else {}

    ts = refinement.get("toulmin_scores", {})
    maxes = {
        "T1_claim_clarity": 3.0, "T2_evidence_quality": 4.0,
        "T3_warrant_reasoning": 3.0, "T4_counterargument": 2.0,
        "T5_rebuttal_quality": 2.0, "T6_structural_cohesion": 2.0,
    }
    display_names = {
        "T1_claim_clarity":       "T1 — Claim Clarity",
        "T2_evidence_quality":    "T2 — Evidence Quality",
        "T3_warrant_reasoning":   "T3 — Warrant/Reasoning",
        "T4_counterargument":     "T4 — Counterargument",
        "T5_rebuttal_quality":    "T5 — Rebuttal Quality",
        "T6_structural_cohesion": "T6 — Structural Cohesion",
    }
    trait_breakdown = {}
    raw_total = 0.0
    for key, mx in maxes.items():
        raw  = float(ts.get(key, {}).get("raw", 0.0))
        raw  = min(raw, mx)
        note = ts.get(key, {}).get("note", "")
        s10  = round((raw / mx) * 10.0, 1)
        raw_total += raw
        trait_breakdown[display_names[key]] = {"raw": raw, "max": mx, "note": note, "score_10": s10}
    raw_max = sum(maxes.values())

    llm_score = refinement.get("overall_score")
    if isinstance(llm_score, (int, float)) and 0 <= llm_score <= 10:
        overall = round(float(llm_score), 1)
    else:
        overall = round(max(1.0, (raw_total / raw_max) * 10.0), 1)

    trait_breakdown["_raw_total"]  = raw_total
    trait_breakdown["_raw_max"]    = raw_max
    trait_breakdown["_normalised"] = overall

    # Synthesised path from aggregation
    strongest_ids = aggregation.get("strongest_path_ids", [])
    all_nodes_map = {
        node.get("node_id", ""): node
        for branch in branches for node in branch.get("steps", [])
    }
    merged_steps = [all_nodes_map[nid] for nid in strongest_ids if nid in all_nodes_map]
    if not merged_steps and best:
        merged_steps = best.get("steps", [])[:6]
    avg_mc = round(sum(s.get("confidence", 0.5) for s in merged_steps) / max(len(merged_steps), 1), 3) if merged_steps else 0.5
    merged_branch = {
        "name": "GoT Synthesised Path",
        "description": aggregation.get("graph_level_verdict", "Merged from highest-scoring nodes."),
        "steps": merged_steps,
        "scores": {
            "confidence": avg_mc,
            "completeness": best.get("scores", {}).get("completeness", 0.5),
            "diversity": best.get("scores", {}).get("diversity", 0.5),
            "overall": round((avg_mc + best.get("scores", {}).get("overall", 0.5)) / 2, 3),
        },
    }

    verdict = {
        "verdict_text":    refinement.get("verdict_text", _verdict_summary(overall)),
        "overall_score":   overall,
        "trait_breakdown": trait_breakdown,
        "strengths":       refinement.get("strengths", ["Essay presents a recognisable argument."]),
        "weaknesses":      refinement.get("weaknesses", ["See GoT analysis for details."]),
        "improvements":    refinement.get("improvements", ["Strengthen evidence quality."]),
        "scoring_model":   "GoT + Toulmin (1958) — LLM 4-step pipeline, 6-trait rubric",
        "best_branch":     best.get("name", ""),
        "best_score":      best.get("scores", {}).get("overall", 0.0),
        "weak_branch":     ranked[-1].get("name", "") if ranked else "",
        "weak_score":      ranked[-1].get("scores", {}).get("overall", 0.0) if ranked else 0.0,
        "got_cross_branch_insights": aggregation.get("cross_branch_insights", []),
        "got_convergent_signals":    aggregation.get("convergent_signals", []),
        "got_contradictory_signals": aggregation.get("contradictory_signals", []),
        "got_graph_verdict":         aggregation.get("graph_level_verdict", ""),
        "got_synthesis_note":        refinement.get("got_synthesis_note", ""),
    }

    return {
        "branches":        ranked,
        "ranked_branches": ranked,
        "best_branch":     best,
        "merged_branch":   merged_branch,
        "verdict":         verdict,
        "node_scores":     node_scores,
        "aggregation":     aggregation,
        "got_pipeline":    True,
    }


# ===========================================================================
# Fallback (if API unavailable)
# ===========================================================================

def _fallback_result(stats: dict, df: pd.DataFrame) -> dict:
    score, trait_breakdown = _compute_toulmin_score_local(stats, df)
    verdict = {
        "verdict_text":    _verdict_summary(score),
        "overall_score":   score,
        "trait_breakdown": trait_breakdown,
        "strengths":       ["Essay presents an identifiable argument."],
        "weaknesses":      ["GoT pipeline unavailable — API not reachable."],
        "improvements":    ["Ensure ANTHROPIC_API_KEY is set and retry."],
        "scoring_model":   "Local Toulmin fallback (GoT API unavailable)",
        "best_branch":     "Fallback Branch", "best_score": 0.5,
        "weak_branch":     "", "weak_score": 0.0,
        "got_pipeline":    False,
    }
    fallback_branch = {
        "name": "Linear Argument Thread",
        "description": "Sequential reading (GoT unavailable).",
        "steps": [
            {"node_id": f"fb_{i}", "label": _short(s), "thought": s,
             "category": "Supporting Fact", "confidence": 0.5}
            for i, s in enumerate(df["sentence"].tolist()[:5])
        ],
        "scores": {"confidence": 0.5, "completeness": 0.5, "diversity": 0.3, "overall": 0.43},
    }
    return {
        "branches": [fallback_branch], "ranked_branches": [fallback_branch],
        "best_branch": fallback_branch, "merged_branch": fallback_branch,
        "verdict": verdict, "node_scores": {}, "aggregation": {}, "got_pipeline": False,
    }


# ===========================================================================
# Backward-compat wrappers (called by explanation_engine.compute_subscores)
# ===========================================================================

def generate_branches(df: pd.DataFrame) -> list[dict]:
    return []


def rank_branches(branches: list[dict]) -> list[dict]:
    return sorted(branches, key=lambda b: b.get("scores", {}).get("overall", 0), reverse=True)


def merge_branches(branches: list[dict]) -> dict:
    if not branches:
        return {}
    best = rank_branches(branches)[0]
    return {
        "name": "Synthesised Best Path",
        "description": "Merged from highest-scoring branches.",
        "steps": best.get("steps", [])[:6],
        "scores": best.get("scores", {}),
    }


def generate_final_verdict(branches: list[dict], stats: dict, df=None) -> dict:
    if df is None:
        df = pd.DataFrame()
    score, trait_breakdown = _compute_toulmin_score_local(stats, df)
    return {
        "verdict_text":    _verdict_summary(score),
        "overall_score":   score,
        "trait_breakdown": trait_breakdown,
        "strengths":       [], "weaknesses":   [], "improvements":  [],
        "scoring_model":   "Local Toulmin (subscores only)",
        "best_branch":     branches[0].get("name", "") if branches else "",
        "best_score":      branches[0].get("scores", {}).get("overall", 0.0) if branches else 0.0,
        "weak_branch": "", "weak_score": 0.0,
    }


# ===========================================================================
# Local Toulmin scoring (for subscores + fallback)
# ===========================================================================

def _score_T1_claim_clarity(stats):
    MAX = 3.0
    claim_cnt = stats.get("claim_count", 0)
    unsup = stats.get("unsupported_count", 0)
    total = max(stats.get("total_sentences", 1), 1)
    supported = max(0, claim_cnt - unsup)
    if claim_cnt == 0 and total >= 5:
        return 1.5, MAX, "Position implied but no explicit claim detected."
    if claim_cnt == 0:
        return 0.0, MAX, "No identifiable claim or position found."
    if unsup >= claim_cnt:
        return 1.0, MAX, "Claims present but all unsupported."
    if supported >= 2:
        return 3.0, MAX, "Clear, specific claims with positions stated."
    if supported == 1:
        return 2.0, MAX, "One clear supported claim."
    return 1.5, MAX, "Claim present but specificity could be improved."


def _score_T2_evidence_quality(stats):
    MAX = 4.0
    strong   = stats.get("strong_evidence_count", 0)
    plain_ev = max(0, stats.get("evidence_count", 0) - strong - stats.get("weak_evidence_count", 0))
    weak_ev  = stats.get("weak_evidence_count", 0)
    missing  = stats.get("missing_evidence_count", 0)
    claim_cnt = max(stats.get("claim_count", 1), 1)
    ev_weighted = strong * 1.0 + plain_ev * 0.5 + weak_ev * 0.1
    ev_per_claim = ev_weighted / claim_cnt
    if strong == 0 and plain_ev == 0 and weak_ev == 0:
        return 0.0, MAX, "No evidence found."
    if strong == 0 and weak_ev > 0:
        return max(0.5, min(1.5, ev_per_claim * 1.5)), MAX, "Only anecdotal evidence."
    if strong >= 1 and ev_per_claim >= 1.0:
        return min(4.0, 2.5 + strong * 0.4 - missing * 0.3), MAX, f"{strong} strong evidence unit(s)."
    return min(2.5, 1.0 + ev_per_claim * 1.5 - missing * 0.2), MAX, "Some evidence but gaps remain."


def _score_T3_warrant_reasoning(stats, ranked_branches):
    MAX = 3.0
    fallacy_cnt  = stats.get("fallacy_count", 0)
    unsup        = stats.get("unsupported_count", 0)
    branch_score = ranked_branches[0]["scores"]["overall"] if ranked_branches else 0.4
    raw = max(0.0, branch_score * 2.0 - fallacy_cnt * 0.5 - unsup * 0.3)
    if fallacy_cnt >= 3:
        note = f"{fallacy_cnt} logical fallacies undermine reasoning."
    elif fallacy_cnt >= 1:
        note = f"{fallacy_cnt} fallacy detected."
    elif branch_score >= 0.65:
        note = "Reasoning chain is logically structured."
    else:
        note = "Logical connections are weak."
    return round(min(MAX, raw), 2), MAX, note


def _score_T4_counterargument(stats):
    MAX = 2.0
    cc = stats.get("counterclaim_count", 0)
    if cc == 0:  return 0.0, MAX, "No counterarguments."
    if cc == 1:  return 1.5, MAX, "One counterargument acknowledged."
    return 2.0, MAX, f"{cc} counterarguments acknowledged."


def _score_T5_rebuttal_quality(stats):
    MAX = 2.0
    cc  = stats.get("counterclaim_count", 0)
    reb = stats.get("rebuttal_count", 0)
    if cc == 0:   return 0.0, MAX, "No counterarguments — rebuttal N/A."
    if reb == 0:  return 0.0, MAX, "Counterarguments raised but not rebutted."
    if reb >= cc: return 2.0, MAX, f"All {cc} counterargument(s) rebutted."
    return round((reb / cc) * 1.5, 2), MAX, f"{reb}/{cc} counterarguments rebutted."


def _score_T6_structural_cohesion(stats, df):
    MAX = 2.0
    cats = set(df["category"].unique()) if df is not None and not df.empty else set()
    pts = sum([
        "Lead" in cats,
        "Position" in cats or stats.get("claim_count", 0) > 0,
        "Concluding Statement" in cats,
        stats.get("evidence_count", 0) > 0,
    ])
    raw = max(0.0, (pts / 4.0) * 2.0 - stats.get("fallacy_count", 0) * 0.2)
    note = ("Well-structured essay." if pts == 4
            else "Basic structure but missing components." if pts >= 2
            else "Weak structure.")
    return round(raw, 2), MAX, note


def _compute_toulmin_score_local(stats: dict, df: pd.DataFrame) -> tuple:
    dummy = [{"scores": {"overall": 0.5}}]
    t1r, t1m, t1n = _score_T1_claim_clarity(stats)
    t2r, t2m, t2n = _score_T2_evidence_quality(stats)
    t3r, t3m, t3n = _score_T3_warrant_reasoning(stats, dummy)
    t4r, t4m, t4n = _score_T4_counterargument(stats)
    t5r, t5m, t5n = _score_T5_rebuttal_quality(stats)
    t6r, t6m, t6n = _score_T6_structural_cohesion(stats, df)
    raw_total = t1r + t2r + t3r + t4r + t5r + t6r
    raw_max   = t1m + t2m + t3m + t4m + t5m + t6m
    overall   = max(1.0, round((raw_total / raw_max) * 10.0, 1))
    trait_breakdown = {
        "T1 — Claim Clarity":       {"raw": t1r, "max": t1m, "note": t1n, "score_10": round((t1r/t1m)*10,1)},
        "T2 — Evidence Quality":    {"raw": t2r, "max": t2m, "note": t2n, "score_10": round((t2r/t2m)*10,1)},
        "T3 — Warrant/Reasoning":   {"raw": t3r, "max": t3m, "note": t3n, "score_10": round((t3r/t3m)*10,1)},
        "T4 — Counterargument":     {"raw": t4r, "max": t4m, "note": t4n, "score_10": round((t4r/t4m)*10,1)},
        "T5 — Rebuttal Quality":    {"raw": t5r, "max": t5m, "note": t5n, "score_10": round((t5r/t5m)*10,1)},
        "T6 — Structural Cohesion": {"raw": t6r, "max": t6m, "note": t6n, "score_10": round((t6r/t6m)*10,1)},
        "_raw_total": raw_total, "_raw_max": raw_max, "_normalised": overall,
    }
    return overall, trait_breakdown


def _verdict_summary(score: float) -> str:
    if score >= 8.5:
        return "**Exemplary Argument** — Meets the highest standard: cited evidence, engaged counterarguments, clear thesis, logical warrants."
    if score >= 7.0:
        return "**Proficient Argument** — Well-structured with good evidence. Minor gaps in counterargument or warrant quality."
    if score >= 5.5:
        return "**Developing Argument** — Position is clear but evidence quality and/or counterargument engagement need strengthening."
    if score >= 3.5:
        return "**Beginning Argument** — Basic claim present but lacks evidence, logical warrants, and engagement with opposition."
    return "**Inadequate Argument** — Relies on assertion, logical fallacies, or anecdote. Fundamental structural revision required."
