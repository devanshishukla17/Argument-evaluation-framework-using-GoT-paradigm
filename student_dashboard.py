"""
student_dashboard.py — Student-friendly feedback view.
"""

import streamlit as st
import pandas as pd
from styles import tag_html, score_bar_html, graph_insight_html


_SH_MAP = {
    "Claim":               "sh-claim",
    "Unsupported Claim":   "sh-counterclaim",
    "Evidence":            "sh-evidence",
    "Strong Evidence":     "sh-evidence",
    "Counterclaim":        "sh-counterclaim",
    "Rebuttal":            "sh-rebuttal",
    "Assumption":          "sh-assumption",
}


def render_student_dashboard(
    df: pd.DataFrame,
    feedback_items: list[dict],
    verdict: dict,
    subscores: dict,
    best_branch: dict,
    keywords: list[str],
):
    """Render the student-friendly feedback dashboard."""

    st.markdown("""
    <div class="page-header">
        <div class="page-title">Student Dashboard</div>
        <div class="page-subtitle">Personalised · Actionable Feedback</div>
    </div>
    """, unsafe_allow_html=True)

    # ── Score summary ─────────────────────────────────────────────────────────
    score = verdict.get("overall_score", 0)
    score_color = "#26de81" if score >= 7 else ("#f7b731" if score >= 4 else "#fc5c65")
    st.markdown(f"""
    <div class="verdict-box" style="text-align:center;padding:2rem">
        <div style="font-family:'DM Mono',monospace;font-size:.75rem;
                    color:var(--text-muted);text-transform:uppercase;letter-spacing:.1em;
                    margin-bottom:.5rem">Your Essay Score</div>
        <div style="font-family:'Syne',sans-serif;font-size:3.5rem;font-weight:800;
                    color:{score_color};line-height:1">{score:.1f}<span style="font-size:1.5rem;color:var(--text-secondary)">/10</span></div>
        <div style="margin-top:1rem;font-size:.9rem;color:var(--text-secondary)">
            {verdict.get('verdict_text','').replace('**','').replace('*','')}
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Feedback filter tabs ──────────────────────────────────────────────────
    tabs = st.tabs(["✅ Strengths", "⚠️ Weaknesses", "🔍 Missing Evidence",
                     "💡 Suggestions", "📝 All Feedback"])

    strength_items  = [f for f in feedback_items if f["feedback_type"] == "strength"]
    weakness_items  = [f for f in feedback_items if f["feedback_type"] == "weakness"]
    missing_items   = [f for f in feedback_items if f["feedback_type"] == "missing"]
    suggest_items   = [f for f in feedback_items if f["feedback_type"] == "suggestion"]

    with tabs[0]:
        if strength_items:
            for item in strength_items:
                st.markdown(f"""
                <div class="feedback-item feedback-strength">
                    <div style="font-size:.75rem;color:#26de81;font-family:'DM Mono',monospace;
                                margin-bottom:.3rem">{item['category'].upper()}</div>
                    {item['sentence'][:120]}{'…' if len(item['sentence'])>120 else ''}
                    <div style="margin-top:.4rem;font-size:.82rem;color:#a8f0ce">{item['message']}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No explicit strengths found. Focus on adding strong evidence and rebuttals.")

    with tabs[1]:
        if weakness_items:
            for item in weakness_items:
                st.markdown(f"""
                <div class="feedback-item feedback-weakness">
                    <div style="font-size:.75rem;color:#fc5c65;font-family:'DM Mono',monospace;
                                margin-bottom:.3rem">{item['category'].upper()}</div>
                    {item['sentence'][:120]}{'…' if len(item['sentence'])>120 else ''}
                    <div style="margin-top:.4rem;font-size:.82rem;color:#fdb4b8">{item['message']}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.success("No significant weaknesses detected. Well done!")

    with tabs[2]:
        if missing_items:
            for item in missing_items:
                st.markdown(f"""
                <div class="feedback-item feedback-missing">
                    <div style="font-size:.75rem;color:var(--text-muted);font-family:'DM Mono',monospace;
                                margin-bottom:.3rem">MISSING EVIDENCE</div>
                    {item['sentence'][:120]}{'…' if len(item['sentence'])>120 else ''}
                    <div style="margin-top:.4rem;font-size:.82rem">{item['message']}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.success("All major claims appear to be supported.")

    with tabs[3]:
        if suggest_items:
            for item in suggest_items:
                st.markdown(f"""
                <div class="feedback-item feedback-suggestion">
                    {item['sentence'][:120]}{'…' if len(item['sentence'])>120 else ''}
                    <div style="margin-top:.4rem;font-size:.82rem;color:#c2bafc">{item['message']}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No specific suggestions at this time.")

    with tabs[4]:
        for item in feedback_items:
            cls_map = {
                "strength": "feedback-strength",
                "weakness": "feedback-weakness",
                "missing":  "feedback-missing",
                "suggestion": "feedback-suggestion",
            }
            cls = cls_map.get(item["feedback_type"], "feedback-suggestion")
            st.markdown(f"""
            <div class="feedback-item {cls}">
                <div style="font-size:.75rem;font-family:'DM Mono',monospace;
                            opacity:.7;margin-bottom:.25rem">{item['category'].upper()}</div>
                {item['sentence'][:120]}{'…' if len(item['sentence'])>120 else ''}
                <div style="margin-top:.3rem;font-size:.82rem">{item['message']}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")

    # ── Best argument path (simplified for student) ───────────────────────────
    if best_branch:
        st.markdown("""
        <div style="font-family:'Syne',sans-serif;font-size:1.05rem;font-weight:700;margin-bottom:.75rem">
            🧠 Your Best Argument Path
        </div>
        """, unsafe_allow_html=True)
        steps = best_branch.get("steps", [])
        for i, step in enumerate(steps):
            arrow = " → " if i < len(steps) - 1 else ""
            cat = step.get("category", "Claim")
            st.markdown(
                f'<span class="tag tag-claim" style="margin:.2rem">{i+1}. {step["label"][:50]}</span>{arrow}',
                unsafe_allow_html=True,
            )
        score_val = best_branch.get("scores", {}).get("overall", 0)
        st.markdown(f"""
        <div style="margin-top:.75rem;font-size:.83rem;color:var(--text-secondary)">
            Path strength: <b style="color:#26de81">{score_val:.0%}</b>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # ── Annotated essay ───────────────────────────────────────────────────────
    st.markdown("""
    <div style="font-family:'Syne',sans-serif;font-size:1.05rem;font-weight:700;margin-bottom:.75rem">
        📄 Annotated Essay
    </div>
    """, unsafe_allow_html=True)

    # Annotated essay explanation
    st.markdown(graph_insight_html(
        "Every sentence is colour-coded by its discourse role. "        "Purple = Claim, Teal = Evidence, Red = Counterclaim, Yellow = Rebuttal, Orange = Assumption. "        "A ⚠ Missing Evidence badge means this claim has no supporting evidence nearby."
    ), unsafe_allow_html=True)

    for _, row in df.iterrows():
        cat = row["category"]
        sh_cls = _SH_MAP.get(cat, "sh-default")
        tag_html_str = tag_html(cat, cat)
        missing_badge = ' <span class="tag tag-missing">⚠ No Evidence</span>' if row.get("missing_evidence") else ""
        st.markdown(f"""
        <div class="sentence-highlight {sh_cls}">
            <div style="display:flex;align-items:center;gap:.5rem;margin-bottom:.25rem">
                {tag_html_str}{missing_badge}
                <span style="font-family:'DM Mono',monospace;font-size:.65rem;
                             color:var(--text-muted)">{row['confidence']:.0%} conf</span>
            </div>
            {row['sentence']}
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # ── Score bars ────────────────────────────────────────────────────────────
    st.markdown("""
    <div style="font-family:'Syne',sans-serif;font-size:1.05rem;font-weight:700;margin-bottom:.75rem">
        📊 Your Scores at a Glance
    </div>
    """, unsafe_allow_html=True)
    for lbl, val in subscores.items():
        st.markdown(score_bar_html(val, lbl), unsafe_allow_html=True)
