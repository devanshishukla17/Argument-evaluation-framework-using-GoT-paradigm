"""
graph_builder.py — Build argument graphs and GoT graphs from classified essay data.
Supports context-aware dynamic graph type selection.
"""

from __future__ import annotations
import networkx as nx
import pandas as pd
from typing import Literal

# Node type colours for visualisation
NODE_COLORS = {
    "Claim":              "#7c6af7",
    "Evidence":           "#4ecdc4",
    "Counterclaim":       "#fc5c65",
    "Rebuttal":           "#f7b731",
    "Assumption":         "#fd9644",
    "Missing Evidence":   "#5a6177",
    "Devil Critique":     "#ff6b9d",
    "Final Verdict":      "#26de81",
    "Premise":            "#a29bfe",
    "Position":           "#74b9ff",
    "Lead":               "#81ecec",
    "Concluding Statement": "#00b894",
    "Logical Fallacy":    "#e17055",
    "Bias Indicator":     "#fdcb6e",
    "Unsupported Claim":  "#d63031",
    "Strong Evidence":    "#00cec9",
    "Weak Evidence":      "#e67e22",
    "Supporting Fact":    "#636e72",
    "Example":            "#6c5ce7",
    "Cause-Effect Relation": "#0984e3",
}

GraphType = Literal[
    "standard_argument_graph",
    "debate_graph",
    "unsupported_claim_graph",
    "hidden_assumption_graph",
    "contradiction_graph",
    "got_branch_graph",
]


def select_graph_type(stats: dict) -> GraphType:
    """
    Dynamically select the most informative graph type given essay stats.
    """
    cc  = stats.get("counterclaim_count", 0)
    uc  = stats.get("unsupported_count", 0)
    ac  = stats.get("assumption_count", 0)
    fc  = stats.get("fallacy_count", 0)
    ec  = stats.get("evidence_count", 0)
    tot = stats.get("total_sentences", 1)

    if cc >= 2:
        return "debate_graph"
    if uc >= 3:
        return "unsupported_claim_graph"
    if ac >= 2:
        return "hidden_assumption_graph"
    if fc >= 2:
        return "contradiction_graph"
    return "standard_argument_graph"


def build_argument_graph(df: pd.DataFrame) -> nx.DiGraph:
    """
    Build a directed argument graph from classified discourse units.
    Nodes are sentences; edges are inferred discourse relations.
    """
    G = nx.DiGraph()

    claim_cats    = {"Claim", "Unsupported Claim", "Position"}
    evidence_cats = {"Evidence", "Strong Evidence", "Weak Evidence", "Supporting Fact", "Example"}
    counter_cats  = {"Counterclaim"}
    rebuttal_cats = {"Rebuttal"}
    assumption_cats = {"Assumption", "Premise"}

    prev_claim_id   = None
    prev_node_id    = None

    for idx, row in df.iterrows():
        node_id = f"node_{idx}"
        short   = row["sentence"][:80] + ("…" if len(row["sentence"]) > 80 else "")
        G.add_node(
            node_id,
            label    = short,
            full     = row["sentence"],
            category = row["category"],
            color    = NODE_COLORS.get(row["category"], "#888"),
            confidence = row.get("confidence", 0.5),
        )

        cat = row["category"]

        # Connect evidence to the nearest preceding claim
        if cat in evidence_cats and prev_claim_id:
            G.add_edge(node_id, prev_claim_id, relation="supports", weight=0.8)

        # Connect counterclaims to the nearest preceding claim
        elif cat in counter_cats and prev_claim_id:
            G.add_edge(node_id, prev_claim_id, relation="contradicts", weight=0.7)

        # Connect rebuttals to the nearest preceding counterclaim
        elif cat in rebuttal_cats:
            # find most recent counterclaim node
            cc_nodes = [n for n, d in G.nodes(data=True) if d.get("category") == "Counterclaim"]
            if cc_nodes:
                G.add_edge(node_id, cc_nodes[-1], relation="rebuts", weight=0.75)

        # Link assumptions to claims
        elif cat in assumption_cats and prev_claim_id:
            G.add_edge(node_id, prev_claim_id, relation="assumes", weight=0.6)

        # Flag missing evidence nodes for claims
        if row.get("missing_evidence"):
            me_id = f"missing_{idx}"
            G.add_node(
                me_id,
                label    = "⚠ Missing Evidence",
                full     = "No supporting evidence found for this claim.",
                category = "Missing Evidence",
                color    = NODE_COLORS["Missing Evidence"],
                confidence = 0.0,
            )
            G.add_edge(me_id, node_id, relation="weakens", weight=0.9)

        if cat in claim_cats:
            prev_claim_id = node_id

        # Sequential chain for flow
        if prev_node_id and prev_node_id != node_id:
            if not G.has_edge(node_id, prev_node_id):
                G.add_edge(prev_node_id, node_id, relation="extends", weight=0.3)

        prev_node_id = node_id

    return G


def build_debate_graph(df: pd.DataFrame) -> nx.DiGraph:
    """Emphasises claim ↔ counterclaim ↔ rebuttal debates."""
    G = build_argument_graph(df)
    # Strengthen counterclaim edges
    for u, v, d in G.edges(data=True):
        if d.get("relation") in ("contradicts", "rebuts"):
            d["weight"] = 1.0
    return G


def build_unsupported_claim_graph(df: pd.DataFrame) -> nx.DiGraph:
    """Highlights unsupported claims as hub nodes."""
    G = nx.DiGraph()
    for idx, row in df.iterrows():
        node_id = f"node_{idx}"
        short   = row["sentence"][:70] + "…" if len(row["sentence"]) > 70 else row["sentence"]
        G.add_node(
            node_id,
            label    = short,
            full     = row["sentence"],
            category = row["category"],
            color    = NODE_COLORS.get(row["category"], "#888"),
        )
        if row.get("missing_evidence"):
            me_id = f"me_{idx}"
            G.add_node(me_id, label="⚠ No Evidence", category="Missing Evidence",
                       color=NODE_COLORS["Missing Evidence"], full="Missing evidence")
            G.add_edge(node_id, me_id, relation="lacks", weight=1.0)
    return G


def build_hidden_assumption_graph(df: pd.DataFrame) -> nx.DiGraph:
    """Surfaces hidden assumptions linked to their host claims.
    Only adds assumption nodes if the essay actually contains
    classified Assumption/Premise sentences."""
    G = build_argument_graph(df)

    # Only flag hidden assumptions if real assumptions were detected
    real_assumptions = df[df["category"].isin(["Assumption", "Premise"])]
    if real_assumptions.empty:
        # No assumptions in essay — return standard graph unchanged
        return G

    # Add hidden assumption nodes only for claims without citations
    for idx, row in df.iterrows():
        if row["category"] in ("Claim", "Unsupported Claim") and not row.get("has_citation"):
            ha_id = f"ha_{idx}"
            G.add_node(ha_id,
                       label      = "Hidden Assumption",
                       full       = "This claim may rest on an unstated assumption.",
                       category   = "Assumption",
                       color      = NODE_COLORS["Assumption"],
                       confidence = 0.5)
            G.add_edge(ha_id, f"node_{idx}", relation="assumes", weight=0.7)
    return G


def build_got_graph(branches: list[dict]) -> nx.DiGraph:
    """
    Build a Graph-of-Thought graph from reasoning branches.
    Each branch is a list of step dicts with keys: id, label, category, confidence.
    """
    G = nx.DiGraph()
    for b_idx, branch in enumerate(branches):
        steps = branch.get("steps", [])
        for s_idx, step in enumerate(steps):
            node_id = f"b{b_idx}_s{s_idx}"
            G.add_node(
                node_id,
                label      = step.get("label", ""),
                category   = step.get("category", "Claim"),
                color      = NODE_COLORS.get(step.get("category", "Claim"), "#888"),
                confidence = step.get("confidence", 0.5),
                branch_id  = b_idx,
            )
            if s_idx > 0:
                prev_id = f"b{b_idx}_s{s_idx - 1}"
                G.add_edge(prev_id, node_id, relation="extends", weight=step.get("confidence", 0.5))

    return G


def get_graph_for_type(df: pd.DataFrame, graph_type: GraphType) -> nx.DiGraph:
    """Dispatch to the correct graph builder."""
    builders = {
        "standard_argument_graph": build_argument_graph,
        "debate_graph":            build_debate_graph,
        "unsupported_claim_graph": build_unsupported_claim_graph,
        "hidden_assumption_graph": build_hidden_assumption_graph,
        "contradiction_graph":     build_argument_graph,  # reuse + highlight
        "got_branch_graph":        build_argument_graph,
    }
    return builders.get(graph_type, build_argument_graph)(df)


def graph_stats(G: nx.DiGraph) -> dict:
    """Return basic graph stats for display."""
    relations = [d.get("relation", "unknown") for _, _, d in G.edges(data=True)]
    rel_counts: dict = {}
    for r in relations:
        rel_counts[r] = rel_counts.get(r, 0) + 1

    node_cats = [d.get("category", "Unknown") for _, d in G.nodes(data=True)]
    cat_counts: dict = {}
    for c in node_cats:
        cat_counts[c] = cat_counts.get(c, 0) + 1

    return {
        "num_nodes":   G.number_of_nodes(),
        "num_edges":   G.number_of_edges(),
        "relations":   rel_counts,
        "node_categories": cat_counts,
        "density":     round(nx.density(G), 3),
    }
