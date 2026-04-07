"""
visualization.py — Generate interactive Plotly and network graphs.
All chart functions return Plotly figures or HTML strings.
"""

from __future__ import annotations
import math
import random
import networkx as nx
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from typing import Optional

# Colour palette consistent with styles.py
_COLORS = {
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

_BG = "#0d0f14"
_PAPER = "#13161e"
_GRID = "#1a1d27"
_TEXT = "#e8eaf0"

_BASE_LAYOUT = dict(
    paper_bgcolor=_PAPER,
    plot_bgcolor=_BG,
    font=dict(family="DM Sans, sans-serif", color=_TEXT, size=12),
    margin=dict(l=16, r=16, t=40, b=16),
)


# ---------------------------------------------------------------------------
# Discourse distribution chart
# ---------------------------------------------------------------------------

def discourse_distribution_chart(df: pd.DataFrame) -> go.Figure:
    """Horizontal bar chart of discourse category counts."""
    counts = df["category"].value_counts().reset_index()
    counts.columns = ["Category", "Count"]
    colors = [_COLORS.get(c, "#888") for c in counts["Category"]]

    fig = go.Figure(go.Bar(
        x=counts["Count"],
        y=counts["Category"],
        orientation="h",
        marker=dict(color=colors, line=dict(width=0)),
        text=counts["Count"],
        textposition="outside",
        textfont=dict(color=_TEXT, size=11),
        hovertemplate="<b>%{y}</b><br>Count: %{x}<extra></extra>",
    ))
    fig.update_layout(
        **_BASE_LAYOUT,
        title=dict(text="Discourse Category Distribution", font=dict(size=16, color=_TEXT)),
        xaxis=dict(showgrid=True, gridcolor=_GRID, zeroline=False),
        yaxis=dict(showgrid=False, categoryorder="total ascending"),
        height=max(300, len(counts) * 32),
        showlegend=False,
    )
    return fig


# ---------------------------------------------------------------------------
# Network / argument graph
# ---------------------------------------------------------------------------

def argument_network_chart(G: nx.DiGraph, title: str = "Argument Graph") -> go.Figure:
    """
    Render a NetworkX directed graph as an interactive Plotly network chart.
    Uses spring layout. Nodes sized by degree.
    """
    if G.number_of_nodes() == 0:
        return go.Figure().update_layout(**_BASE_LAYOUT, title=title)

    # Layout
    try:
        pos = nx.spring_layout(G, k=1.8, seed=42, iterations=60)
    except Exception:
        pos = {n: (random.random(), random.random()) for n in G.nodes()}

    # Edge traces
    edge_traces = []
    for u, v, data in G.edges(data=True):
        x0, y0 = pos.get(u, (0, 0))
        x1, y1 = pos.get(v, (0, 0))
        relation = data.get("relation", "")
        color_map = {
            "supports": "#26de81", "contradicts": "#fc5c65",
            "rebuts": "#f7b731", "assumes": "#fd9644",
            "weakens": "#e17055", "extends": "#5a6177",
            "concludes": "#00b894", "depends_on": "#74b9ff",
            "lacks": "#d63031",
        }
        col = color_map.get(relation, "#5a6177")
        edge_traces.append(go.Scatter(
            x=[x0, x1, None], y=[y0, y1, None],
            mode="lines",
            line=dict(width=1.5, color=col),
            hoverinfo="none",
            showlegend=False,
        ))

    # Node trace
    node_x, node_y, node_text, node_hover, node_colors, node_sizes = [], [], [], [], [], []
    for node, data in G.nodes(data=True):
        x, y = pos.get(node, (0, 0))
        node_x.append(x)
        node_y.append(y)
        node_text.append(data.get("label", str(node))[:30])
        cat = data.get("category", "Supporting Fact")
        conf = data.get("confidence", 0.5)
        full = data.get("full", "")
        node_hover.append(
            f"<b>{cat}</b><br>{full[:100]}{'…' if len(full) > 100 else ''}<br>"
            f"<i>Confidence: {conf:.0%}</i>"
        )
        node_colors.append(_COLORS.get(cat, "#888"))
        degree = G.degree(node)
        node_sizes.append(max(14, min(40, 12 + degree * 4)))

    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode="markers+text",
        text=node_text,
        textposition="top center",
        textfont=dict(size=9, color=_TEXT),
        marker=dict(
            size=node_sizes,
            color=node_colors,
            line=dict(width=1.5, color=_BG),
        ),
        hovertext=node_hover,
        hoverinfo="text",
        showlegend=False,
    )

    fig = go.Figure(data=[*edge_traces, node_trace])
    fig.update_layout(
        **_BASE_LAYOUT,
        title=dict(text=title, font=dict(size=16, color=_TEXT)),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        height=520,
    )
    return fig


# ---------------------------------------------------------------------------
# GoT branch timeline
# ---------------------------------------------------------------------------

def got_branch_timeline(branches: list[dict]) -> go.Figure:
    """Visualise GoT reasoning branches as a horizontal timeline / Gantt-style chart."""
    if not branches:
        return go.Figure().update_layout(**_BASE_LAYOUT)

    rows, colors_list = [], []
    for b_idx, branch in enumerate(branches):
        for s_idx, step in enumerate(branch.get("steps", [])):
            rows.append({
                "Branch":     branch["name"],
                "Step":       s_idx,
                "Label":      step.get("label", "")[:50],
                "Category":   step.get("category", "Claim"),
                "Confidence": step.get("confidence", 0.5),
            })

    if not rows:
        return go.Figure().update_layout(**_BASE_LAYOUT)

    df_plot = pd.DataFrame(rows)

    fig = px.scatter(
        df_plot,
        x="Step",
        y="Branch",
        color="Category",
        size="Confidence",
        hover_data={"Label": True, "Confidence": True, "Category": True},
        color_discrete_map=_COLORS,
        size_max=20,
        title="Graph-of-Thought: Reasoning Branch Map",
    )
    fig.update_traces(marker=dict(line=dict(width=1, color=_BG)))
    fig.update_layout(
        **_BASE_LAYOUT,
        xaxis_title="Reasoning Step",
        yaxis_title="",
        height=320,
        legend=dict(
            bgcolor="rgba(19,22,30,0.8)",
            bordercolor=_GRID,
            font=dict(color=_TEXT, size=10),
        ),
    )
    return fig


# ---------------------------------------------------------------------------
# Branch score radar
# ---------------------------------------------------------------------------

def branch_score_radar(branches: list[dict]) -> go.Figure:
    """Radar chart comparing branch scores."""
    if not branches:
        return go.Figure().update_layout(**_BASE_LAYOUT)

    categories = ["Confidence", "Completeness", "Diversity", "Overall"]
    fig = go.Figure()

    colors_list = ["#7c6af7", "#4ecdc4", "#f7b731", "#fc5c65", "#26de81"]
    for i, branch in enumerate(branches[:5]):
        scores = branch.get("scores", {})
        values = [
            scores.get("confidence", 0),
            scores.get("completeness", 0),
            scores.get("diversity", 0),
            scores.get("overall", 0),
        ]
        values += [values[0]]  # close polygon
        col = colors_list[i % len(colors_list)]
        fig.add_trace(go.Scatterpolar(
            r=values,
            theta=categories + [categories[0]],
            fill="toself",
            name=branch["name"][:30],
            line=dict(color=col, width=2),
            fillcolor=f"rgba({int(col[1:3],16)},{int(col[3:5],16)},{int(col[5:7],16)},0.12)",
            marker=dict(color=col, size=6),
        ))

    fig.update_layout(
        **_BASE_LAYOUT,
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 1], color=_TEXT,
                            gridcolor=_GRID, tickfont=dict(size=9)),
            angularaxis=dict(color=_TEXT, gridcolor=_GRID),
            bgcolor=_BG,
        ),
        title=dict(text="Branch Score Comparison", font=dict(size=16, color=_TEXT)),
        legend=dict(bgcolor="rgba(19,22,30,0.8)", font=dict(color=_TEXT, size=10)),
        height=380,
    )
    return fig


# ---------------------------------------------------------------------------
# Subscore bar chart
# ---------------------------------------------------------------------------

def subscore_chart(subscores: dict) -> go.Figure:
    labels = list(subscores.keys())
    values = list(subscores.values())
    colors_list = [
        "#26de81" if v >= 7 else ("#f7b731" if v >= 4 else "#fc5c65")
        for v in values
    ]

    fig = go.Figure(go.Bar(
        x=labels, y=values,
        marker=dict(color=colors_list, line=dict(width=0)),
        text=[f"{v:.1f}" for v in values],
        textposition="outside",
        textfont=dict(color=_TEXT, size=11),
        hovertemplate="<b>%{x}</b><br>Score: %{y:.1f}/10<extra></extra>",
    ))
    fig.add_shape(type="line", x0=-0.5, x1=len(labels) - 0.5, y0=5, y1=5,
                  line=dict(color="#5a6177", width=1, dash="dot"))
    fig.update_layout(
        **_BASE_LAYOUT,
        title=dict(text="Detailed Essay Scores", font=dict(size=16, color=_TEXT)),
        yaxis=dict(range=[0, 11], showgrid=True, gridcolor=_GRID),
        xaxis=dict(showgrid=False),
        height=320,
        showlegend=False,
    )
    return fig


# ---------------------------------------------------------------------------
# Heatmap of sentence quality
# ---------------------------------------------------------------------------

def sentence_heatmap(df: pd.DataFrame) -> go.Figure:
    """
    Heatmap where x = sentence index, y = discourse dimension, value = score.
    """
    sentences = df["sentence"].str[:40].tolist()
    short_labels = [f"S{i+1}" for i in range(len(sentences))]

    # Build a small matrix: rows = dimensions, cols = sentences
    dims = ["Confidence", "Has Citation", "Is Numeric", "Missing Evidence", "Unsupported"]
    z = [
        df["confidence"].tolist(),
        df["has_citation"].astype(float).tolist(),
        df["is_numeric"].astype(float).tolist(),
        df["missing_evidence"].astype(float).tolist() if "missing_evidence" in df.columns else [0]*len(df),
        (df["category"] == "Unsupported Claim").astype(float).tolist(),
    ]

    fig = go.Figure(go.Heatmap(
        z=z,
        x=short_labels,
        y=dims,
        colorscale=[[0, "#1a1d27"], [0.5, "#7c6af7"], [1.0, "#26de81"]],
        showscale=True,
        hovertemplate="Sentence %{x}<br>%{y}: %{z:.2f}<extra></extra>",
    ))
    fig.update_layout(
        **_BASE_LAYOUT,
        title=dict(text="Sentence Quality Heatmap", font=dict(size=16, color=_TEXT)),
        height=260,
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=False),
    )
    return fig


# ---------------------------------------------------------------------------
# Devil agent summary bar
# ---------------------------------------------------------------------------

def devil_summary_chart(devil_results: dict) -> go.Figure:
    agents = [k for k in devil_results if k != "synthesis"]
    counts = [devil_results[a].get("count", 0) for a in agents]
    labels = [devil_results[a].get("agent", a) for a in agents]
    icons  = [devil_results[a].get("icon", "") for a in agents]

    display_labels = [f"{icons[i]} {labels[i]}" for i in range(len(labels))]

    fig = go.Figure(go.Bar(
        x=counts,
        y=display_labels,
        orientation="h",
        marker=dict(
            color=["#fc5c65", "#f7b731", "#fd9644", "#4ecdc4", "#7c6af7", "#26de81", "#a29bfe"],
            line=dict(width=0),
        ),
        text=counts,
        textposition="outside",
        textfont=dict(color=_TEXT, size=11),
    ))
    fig.update_layout(
        **_BASE_LAYOUT,
        title=dict(text="Devil's Advocate — Issues by Agent", font=dict(size=16, color=_TEXT)),
        xaxis=dict(showgrid=True, gridcolor=_GRID),
        yaxis=dict(showgrid=False),
        height=320,
        showlegend=False,
    )
    return fig


# ---------------------------------------------------------------------------
# PyVis HTML network (optional enhanced graph)
# ---------------------------------------------------------------------------

def pyvis_graph_html(G: nx.DiGraph, title: str = "Argument Graph") -> Optional[str]:
    """
    Generate a PyVis interactive HTML string.
    Returns None if PyVis is unavailable.
    """
    try:
        from pyvis.network import Network
        net = Network(height="500px", width="100%", bgcolor=_BG,
                      font_color=_TEXT, directed=True)
        net.set_options("""
        {
          "nodes": {"font": {"size": 12, "color": "#e8eaf0"}, "borderWidth": 2},
          "edges": {"arrows": {"to": {"enabled": true, "scaleFactor": 0.7}},
                    "smooth": {"type": "dynamic"}},
          "physics": {"stabilization": {"iterations": 200}}
        }
        """)

        for node, data in G.nodes(data=True):
            net.add_node(
                node,
                label=data.get("label", str(node))[:35],
                title=data.get("full", ""),
                color=data.get("color", "#888"),
                size=max(14, min(35, 12 + G.degree(node) * 3)),
            )
        for u, v, data in G.edges(data=True):
            net.add_edge(u, v, label=data.get("relation", ""), color="#5a6177")

        return net.generate_html()
    except ImportError:
        return None
