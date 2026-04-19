"""
dashboard.py — Main metrics dashboard.
"""

import streamlit as st
import pandas as pd
from styles import metric_card_html, score_bar_html, tag_html, graph_legend_html, graph_insight_html
from visualization import discourse_distribution_chart, subscore_chart


def render_score_bars(subscores: dict):
    """Render score bars one at a time so Streamlit renders HTML correctly."""
    for label, value in subscores.items():
        st.markdown(score_bar_html(value, label), unsafe_allow_html=True)


def render_dashboard(df, stats, verdict, subscores, keywords, topic, best_branch):

    st.markdown("""
    <div class="page-header">
        <div class="page-title">Dashboard Overview</div>
        <div class="page-subtitle">Essay Analysis · Summary Metrics</div>
    </div>""", unsafe_allow_html=True)

    # Topic + keywords
    col_a, col_b = st.columns([1, 2])
    with col_a:
        st.markdown(f"""
        <div class="section-card" style="padding:1rem 1.25rem">
            <div class="metric-label" style="margin-bottom:.5rem">DETECTED TOPIC</div>
            <div style="font-family:'Syne',sans-serif;font-size:1.3rem;font-weight:700;color:#4ecdc4">{topic}</div>
        </div>""", unsafe_allow_html=True)
    with col_b:
        kw_html = " ".join(tag_html(kw, "Evidence") for kw in keywords[:10])
        st.markdown(f"""
        <div class="section-card" style="padding:1rem 1.25rem">
            <div class="metric-label" style="margin-bottom:.5rem">KEY CONCEPTS</div>
            <div style="display:flex;flex-wrap:wrap;gap:.4rem">{kw_html}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Metric cards row 1
    c1, c2, c3, c4, c5 = st.columns(5)
    score = verdict.get("overall_score", 0)
    sc = "#26de81" if score >= 7 else ("#f7b731" if score >= 4 else "#fc5c65")
    with c1: st.markdown(metric_card_html(f"{score:.1f}/10", "Overall Score", sc, "🏆"), unsafe_allow_html=True)
    with c2: st.markdown(metric_card_html(stats.get("total_sentences",0), "Total Sentences", icon="📝"), unsafe_allow_html=True)
    with c3: st.markdown(metric_card_html(stats.get("claim_count",0), "Claims", "#7c6af7", "💬"), unsafe_allow_html=True)
    with c4: st.markdown(metric_card_html(stats.get("evidence_count",0), "Evidence Units", "#4ecdc4", "📊"), unsafe_allow_html=True)
    with c5:
        uc = stats.get("unsupported_count", 0)
        uc_c = "#fc5c65" if uc >= 3 else ("#f7b731" if uc >= 1 else "#26de81")
        st.markdown(metric_card_html(uc, "Unsupported Claims", uc_c, "⚠️"), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    c6, c7, c8, c9 = st.columns(4)
    with c6: st.markdown(metric_card_html(stats.get("counterclaim_count",0), "Counterclaims", "#fc5c65", "🔄"), unsafe_allow_html=True)
    with c7: st.markdown(metric_card_html(stats.get("rebuttal_count",0), "Rebuttals", "#f7b731", "🛡️"), unsafe_allow_html=True)
    with c8: st.markdown(metric_card_html(stats.get("assumption_count",0), "Assumptions", "#fd9644", "🤔"), unsafe_allow_html=True)
    with c9: st.markdown(metric_card_html(stats.get("fallacy_count",0), "Logical Fallacies", "#e17055", "❌"), unsafe_allow_html=True)

    st.markdown("---")

    # Verdict
    st.markdown("""<div class="verdict-box">
        <div style="font-family:'Syne',sans-serif;font-size:1rem;font-weight:700;color:#7c6af7;margin-bottom:.5rem">⚡ GoT Final Verdict</div>""",
        unsafe_allow_html=True)
    st.markdown(verdict.get("verdict_text", ""), unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Charts
    left, right = st.columns(2)
    with left:
        st.plotly_chart(discourse_distribution_chart(df), use_container_width=True)
        st.markdown(graph_insight_html(
            "Each bar shows how many sentences belong to a discourse type. "
            "A healthy essay balances Claims with Evidence and includes at least one Counterclaim."
        ), unsafe_allow_html=True)
    with right:
        st.plotly_chart(subscore_chart(subscores), use_container_width=True)
        st.markdown(graph_insight_html(
            "Green bars (≥7) are strong areas. Yellow (4–7) need improvement. Red (<4) need urgent attention."
        ), unsafe_allow_html=True)

    st.markdown("---")

    # Best reasoning path
    if best_branch:
        st.markdown("""<div style="font-family:'Syne',sans-serif;font-size:1.05rem;font-weight:700;margin-bottom:.75rem">🧠 Strongest Reasoning Path</div>""",
            unsafe_allow_html=True)
        scores = best_branch.get("scores", {})
        conf = scores.get("confidence", 0)
        conf_cls = "pill-high" if conf >= 0.7 else ("pill-med" if conf >= 0.4 else "pill-low")
        st.markdown(f"""
        <div class="got-branch best">
            <div style="display:flex;align-items:center;gap:.75rem;margin-bottom:.5rem">
                <span style="font-family:'Syne',sans-serif;font-weight:700">{best_branch.get('name','')}</span>
                <span class="confidence-pill {conf_cls}">Conf: {conf:.0%}</span>
                <span class="confidence-pill pill-high">Overall: {scores.get('overall',0):.0%}</span>
            </div>
            <div style="font-size:.85rem;color:#9298ae">{best_branch.get('description','')}</div>
        </div>""", unsafe_allow_html=True)

        for i, step in enumerate(best_branch.get("steps", [])):
            cat = step.get("category","Claim")
            arrow = '<div class="branch-connector">↓</div>' if i < len(best_branch["steps"])-1 else ""
            st.markdown(f"""
            <div class="got-branch">
                <div style="display:flex;align-items:flex-start;gap:.75rem">
                    <span style="font-family:'DM Mono',monospace;font-size:.72rem;color:#5a6177;min-width:1.5rem">{i+1}</span>
                    <div>{tag_html(cat,cat)}<div style="margin-top:.3rem;font-size:.87rem">{step.get('label','')}</div></div>
                </div>
            </div>{arrow}""", unsafe_allow_html=True)

    st.markdown("---")

    # Score bars — rendered one at a time to avoid raw HTML issue
    st.markdown("""<div style="font-family:'Syne',sans-serif;font-size:1.05rem;font-weight:700;margin-bottom:1rem">📐 Toulmin Trait Scores <span style="font-size:.72rem;font-weight:400;color:#9298ae;font-family:'DM Mono',monospace">Toulmin (1958) — 6 traits, raw 0-16 → normalised 0-10</span></div>""",
        unsafe_allow_html=True)
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    render_score_bars(subscores)
    st.markdown('</div>', unsafe_allow_html=True)
