"""
teacher_dashboard.py — Teacher-grade complete analysis view.
"""

import streamlit as st
import pandas as pd
from styles import tag_html, score_bar_html, graph_insight_html
from visualization import (
    discourse_distribution_chart, subscore_chart,
    got_branch_timeline, branch_score_radar,
    devil_summary_chart, sentence_heatmap,
)


def render_teacher_dashboard(
    df: pd.DataFrame,
    stats: dict,
    verdict: dict,
    subscores: dict,
    teacher_feedback: dict,
    devil_results: dict,
    branches: list[dict],
    graph_type: str,
    G,
):
    """Render the comprehensive teacher evaluation view."""

    st.markdown("""
    <div class="page-header">
        <div class="page-title">Teacher Dashboard</div>
        <div class="page-subtitle">Complete Evaluation · All Metrics · Devil's Advocate</div>
    </div>
    """, unsafe_allow_html=True)

    # ── Summary verdict ───────────────────────────────────────────────────────
    score = verdict.get("overall_score", 0)
    score_color = "#26de81" if score >= 7 else ("#f7b731" if score >= 4 else "#fc5c65")
    col_a, col_b = st.columns([2, 1])
    with col_a:
        st.markdown(f"""
        <div class="verdict-box">
            <div style="font-family:'Syne',sans-serif;font-size:1rem;font-weight:700;
                        color:var(--accent-primary,#7c6af7);margin-bottom:.6rem">
                Evaluation Summary
            </div>
            <div style="font-size:.95rem;line-height:1.6">
                {verdict.get('verdict_text','').replace('**','<b>').replace('*','<i>')}
            </div>
        </div>
        """, unsafe_allow_html=True)
    with col_b:
        st.markdown(f"""
        <div class="metric-card" style="text-align:center;padding:2rem 1.5rem">
            <div class="metric-label" style="margin-bottom:.5rem">OVERALL SCORE</div>
            <div style="font-family:'Syne',sans-serif;font-size:3rem;font-weight:800;
                        color:{score_color};line-height:1">{score:.1f}</div>
            <div style="font-size:.8rem;color:var(--text-muted)">/10</div>
            <div style="margin-top:.75rem;font-size:.8rem;color:var(--text-secondary)">
                Graph type: <code>{graph_type.replace('_',' ')}</code>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # ── Tabbed teacher view ───────────────────────────────────────────────────
    tab_overview, tab_discourse, tab_got, tab_devil, tab_deep = st.tabs([
        "📊 Overview",
        "🗂 Discourse Analysis",
        "🧠 GoT Branches",
        "👹 Devil's Advocate",
        "🔬 Deep Analysis",
    ])

    # ── Tab: Overview ─────────────────────────────────────────────────────────
    with tab_overview:
        left, right = st.columns(2)
        with left:
            st.plotly_chart(discourse_distribution_chart(df), use_container_width=True)
        with right:
            st.plotly_chart(subscore_chart(subscores), use_container_width=True)

        st.markdown("**Score Breakdown**")
        for lbl, val in subscores.items():
            st.markdown(score_bar_html(val, lbl), unsafe_allow_html=True)

        # Strengths & weaknesses
        left2, right2 = st.columns(2)
        with left2:
            st.markdown("#### ✅ Strengths")
            for s in verdict.get("strengths", []):
                st.markdown(f"""
                <div class="feedback-item feedback-strength">{s}</div>
                """, unsafe_allow_html=True)
        with right2:
            st.markdown("#### ⚠️ Weaknesses")
            for w in verdict.get("weaknesses", []):
                st.markdown(f"""
                <div class="feedback-item feedback-weakness">{w}</div>
                """, unsafe_allow_html=True)

        st.markdown("#### 💡 Recommended Improvements")
        for imp in verdict.get("improvements", []):
            st.markdown(f"""
            <div class="feedback-item feedback-suggestion">{imp}</div>
            """, unsafe_allow_html=True)

    # ── Tab: Discourse Analysis ───────────────────────────────────────────────
    with tab_discourse:
        st.plotly_chart(sentence_heatmap(df), use_container_width=True)

        st.markdown("**Full Classified Discourse Table**")
        display_cols = ["sentence", "category", "confidence", "has_citation",
                        "is_numeric", "missing_evidence"]
        available = [c for c in display_cols if c in df.columns]
        st.dataframe(
            df[available].style.map(
                lambda v: "background-color: rgba(252,92,101,0.15)" if v == "Unsupported Claim"
                          else ("background-color: rgba(78,205,196,0.15)" if v == "Strong Evidence" else ""),
                subset=["category"],
            ),
            use_container_width=True,
            height=400,
        )

        # Unsupported claims detail
        unsup = df[df["category"] == "Unsupported Claim"]
        if len(unsup) > 0:
            st.markdown(f"**⚠️ Unsupported Claims ({len(unsup)})**")
            for _, row in unsup.iterrows():
                st.markdown(f"""
                <div class="feedback-item feedback-weakness">
                    {tag_html('Unsupported Claim', 'Unsupported Claim')}
                    <div style="margin-top:.35rem">{row['sentence']}</div>
                </div>
                """, unsafe_allow_html=True)

        # Logical fallacies
        fallacies = df[df["category"] == "Logical Fallacy"]
        if len(fallacies) > 0:
            st.markdown(f"**❌ Logical Fallacies ({len(fallacies)})**")
            for _, row in fallacies.iterrows():
                st.markdown(f"""
                <div class="feedback-item feedback-weakness">
                    {tag_html('Logical Fallacy', 'Logical Fallacy')}
                    <div style="margin-top:.35rem">{row['sentence']}</div>
                </div>
                """, unsafe_allow_html=True)

    # ── Tab: GoT Branches ─────────────────────────────────────────────────────
    with tab_got:
        if branches:
            st.plotly_chart(got_branch_timeline(branches), use_container_width=True)
            st.markdown(graph_insight_html(
                "Each row is a reasoning branch. Each dot is a reasoning step coloured by discourse type. "
                "More steps = more developed reasoning chain. Compare branch depth across rows."
            ), unsafe_allow_html=True)
            st.plotly_chart(branch_score_radar(branches), use_container_width=True)
            st.markdown(graph_insight_html(
                "Radar chart: larger polygon = stronger branch. Confidence = how certain the reasoning is. "
                "Completeness = how many key discourse types are covered. Diversity = originality of the path."
            ), unsafe_allow_html=True)

            st.markdown("**Reasoning Branches Detail**")
            for b_idx, branch in enumerate(branches):
                scores = branch.get("scores", {})
                conf = scores.get("confidence", 0)
                conf_cls = "pill-high" if conf >= 0.7 else ("pill-med" if conf >= 0.4 else "pill-low")
                is_best = b_idx == 0

                with st.expander(f"{'🥇 ' if is_best else ''}{branch['name']} "
                                 f"— Overall: {scores.get('overall',0):.0%}", expanded=is_best):
                    st.markdown(f"""
                    <div class="got-branch {'best' if is_best else ''}">
                        <div style="display:flex;gap:.75rem;margin-bottom:.5rem;flex-wrap:wrap">
                            <span class="confidence-pill {conf_cls}">Confidence: {conf:.0%}</span>
                            <span class="confidence-pill pill-med">Completeness: {scores.get('completeness',0):.0%}</span>
                            <span class="confidence-pill pill-med">Diversity: {scores.get('diversity',0):.0%}</span>
                        </div>
                        <div style="font-size:.87rem;color:var(--text-secondary)">{branch.get('description','')}</div>
                    </div>
                    """, unsafe_allow_html=True)

                    steps = branch.get("steps", [])
                    for i, step in enumerate(steps):
                        cat = step.get("category", "Claim")
                        arrow = '<div class="branch-connector">↓</div>' if i < len(steps) - 1 else ""
                        st.markdown(f"""
                        <div class="path-item">
                            <span style="font-family:'DM Mono',monospace;font-size:.72rem;
                                         color:var(--text-muted)">{i+1}</span>
                            <div>
                                {tag_html(cat, cat)}
                                <div style="margin-top:.3rem;font-size:.87rem">{step.get('label','')}</div>
                                <div style="font-size:.75rem;color:var(--text-muted)">
                                    Confidence: {step.get('confidence',0):.0%}
                                </div>
                            </div>
                        </div>{arrow}
                        """, unsafe_allow_html=True)
        else:
            st.info("No reasoning branches generated. Please analyse an essay first.")

    # ── Tab: Devil's Advocate ─────────────────────────────────────────────────
    with tab_devil:
        synthesis = devil_results.get("synthesis", {})
        for pt in synthesis.get("summary_points", []):
            st.markdown(f"""
            <div class="feedback-item feedback-{'weakness' if '🚨' in pt else 'strength'}">
                {pt}
            </div>
            """, unsafe_allow_html=True)

        st.plotly_chart(devil_summary_chart(devil_results), use_container_width=True)

        # Agent-by-agent detail
        agent_order = ["logical", "ethical", "domain", "cultural",
                       "counterargument", "evidence", "pedagogy"]
        for agent_key in agent_order:
            agent = devil_results.get(agent_key, {})
            if not agent:
                continue
            findings = agent.get("findings", [])
            if not findings:
                continue
            with st.expander(f"{agent.get('icon','👹')} {agent.get('agent', agent_key)} "
                             f"— {agent.get('count',0)} finding(s)"):
                st.markdown(f"""
                <div style="font-size:.85rem;color:var(--text-secondary);margin-bottom:.75rem">
                    {agent.get('summary','')}
                </div>
                """, unsafe_allow_html=True)
                for finding in findings[:12]:
                    sev = finding.get("severity", "low")
                    sev_color = "#fc5c65" if sev == "high" else ("#f7b731" if sev == "medium" else "#5a6177")
                    if finding.get("type") == "Strong Evidence":
                        cls = "feedback-strength"
                    elif sev == "high":
                        cls = "feedback-weakness"
                    elif sev in ("medium", "low"):
                        cls = "feedback-suggestion"
                    else:
                        cls = "feedback-missing"

                    sentence_html = (
                        f'<div style="font-size:.82rem;margin-bottom:.3rem;'
                        f'color:var(--text-secondary)">{finding["sentence"]}</div>'
                        if finding.get("sentence") else ""
                    )
                    st.markdown(f"""
                    <div class="feedback-item {cls}">
                        <div style="display:flex;align-items:center;gap:.5rem;margin-bottom:.3rem">
                            <span class="tag" style="background:rgba(252,92,101,.1);
                                color:{sev_color};border:1px solid {sev_color}40;font-size:.68rem">
                                {finding.get('type','')} · {finding.get('subtype','')}
                            </span>
                        </div>
                        {sentence_html}
                        <div style="font-size:.82rem">{finding.get('teacher_note','')}</div>
                    </div>
                    """, unsafe_allow_html=True)

    # ── Tab: Deep Analysis ────────────────────────────────────────────────────
    with tab_deep:
        st.markdown("**📊 Raw Statistics**")
        stats_df = pd.DataFrame([{"Metric": k.replace("_"," ").title(), "Value": v}
                                   for k, v in stats.items()])
        st.dataframe(stats_df, use_container_width=True, hide_index=True)

        st.markdown("**🗺 Argument Graph Statistics**")
        if G is not None:
            import networkx as nx
            from graph_builder import graph_stats
            gs = graph_stats(G)
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Nodes", gs["num_nodes"])
            col2.metric("Edges", gs["num_edges"])
            col3.metric("Density", gs["density"])
            col4.metric("Graph Type", graph_type.replace("_", " ").title()[:20])

            with st.expander("Edge Relations"):
                for rel, cnt in gs.get("relations", {}).items():
                    st.markdown(f"- **{rel}**: {cnt}")

            with st.expander("Node Categories"):
                for cat, cnt in gs.get("node_categories", {}).items():
                    st.markdown(f"- {tag_html(cat, cat)} **{cnt}**", unsafe_allow_html=True)
