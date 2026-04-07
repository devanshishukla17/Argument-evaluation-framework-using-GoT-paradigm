"""
export_utils.py — Export essay analysis results to CSV, JSON, and PDF.
"""

from __future__ import annotations
import json
import io
import csv
import datetime
import pandas as pd
from typing import Optional


# ---------------------------------------------------------------------------
# CSV export
# ---------------------------------------------------------------------------

def export_csv(df: pd.DataFrame) -> bytes:
    """Export the classified discourse DataFrame as CSV bytes."""
    output = io.StringIO()
    df.to_csv(output, index=False)
    return output.getvalue().encode("utf-8")


# ---------------------------------------------------------------------------
# JSON export
# ---------------------------------------------------------------------------

def export_json(
    df: pd.DataFrame,
    stats: dict,
    verdict: dict,
    subscores: dict,
    devil_results: dict,
    branches: list[dict],
) -> bytes:
    """Export the full analysis as a JSON bytes object."""

    def _safe(obj):
        """Make objects JSON-serialisable."""
        if isinstance(obj, (bool, int, float, str, type(None))):
            return obj
        if isinstance(obj, dict):
            return {k: _safe(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [_safe(i) for i in obj]
        return str(obj)

    payload = {
        "exported_at":    datetime.datetime.utcnow().isoformat(),
        "discourse_units": _safe(df.to_dict(orient="records")),
        "stats":           _safe(stats),
        "verdict":         _safe(verdict),
        "subscores":       _safe(subscores),
        "got_branches":    _safe(branches),
        "devil_results":   _safe({
            k: {
                "agent":    v.get("agent", k),
                "summary":  v.get("summary", ""),
                "count":    v.get("count", 0),
                "findings": v.get("findings", []),
            }
            for k, v in devil_results.items() if k != "synthesis"
        }),
    }
    return json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")


# ---------------------------------------------------------------------------
# PDF report (using fpdf2 if available, else reportlab, else plain text)
# ---------------------------------------------------------------------------

def export_pdf_report(
    df: pd.DataFrame,
    stats: dict,
    verdict: dict,
    subscores: dict,
    keywords: list[str],
    topic: str,
    devil_results: dict,
    essay_text: str = "",
) -> bytes:
    """
    Generate a PDF analysis report.
    Falls back to a plain-text report if PDF libraries are unavailable.
    """
    try:
        return _pdf_fpdf2(df, stats, verdict, subscores, keywords, topic, devil_results, essay_text)
    except ImportError:
        pass
    try:
        return _pdf_reportlab(df, stats, verdict, subscores, keywords, topic, devil_results)
    except ImportError:
        pass
    return _pdf_plaintext(df, stats, verdict, subscores, keywords, topic, devil_results)


# ── fpdf2 implementation ─────────────────────────────────────────────────────

def _pdf_fpdf2(df, stats, verdict, subscores, keywords, topic, devil_results, essay_text) -> bytes:
    from fpdf import FPDF, XPos, YPos

    class PDF(FPDF):
        def header(self):
            self.set_font("Helvetica", "B", 11)
            self.set_text_color(80, 80, 200)
            self.cell(0, 8, "Essay Evaluation Framework — Analysis Report", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            self.set_draw_color(200, 200, 200)
            self.line(10, self.get_y(), 200, self.get_y())
            self.ln(3)

        def footer(self):
            self.set_y(-12)
            self.set_font("Helvetica", "I", 8)
            self.set_text_color(150, 150, 150)
            self.cell(0, 6, f"Page {self.page_no()} — Generated {datetime.datetime.now().strftime('%Y-%m-%d')}", align="C")

    pdf = PDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_margins(14, 14, 14)

    def h1(text):
        pdf.set_font("Helvetica", "B", 14)
        pdf.set_text_color(60, 50, 180)
        pdf.ln(4)
        pdf.cell(0, 8, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_draw_color(180, 180, 220)
        pdf.line(14, pdf.get_y(), 196, pdf.get_y())
        pdf.ln(2)
        pdf.set_text_color(30, 30, 30)

    def h2(text):
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(80, 60, 160)
        pdf.ln(2)
        pdf.cell(0, 7, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_text_color(30, 30, 30)

    def body(text, size=10):
        pdf.set_font("Helvetica", "", size)
        pdf.set_text_color(40, 40, 40)
        pdf.multi_cell(0, 5.5, text)
        pdf.ln(1)

    def kv(key, value):
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(60, 60, 60)
        pdf.cell(55, 6, f"{key}:")
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(30, 30, 30)
        pdf.cell(0, 6, str(value), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # ── Title block
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(40, 30, 140)
    pdf.cell(0, 12, "Essay Evaluation Report", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 6, f"Generated: {datetime.datetime.now().strftime('%B %d, %Y %H:%M')} UTC",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 6, f"Detected Topic: {topic}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(4)

    # ── Overall verdict
    h1("Overall Assessment")
    body(verdict.get("verdict_text", "").replace("**", "").replace("*", ""))
    kv("Overall Score", f"{verdict.get('overall_score', 0):.1f} / 10")
    kv("Keywords", ", ".join(keywords[:8]))

    # ── Sub-scores
    h1("Detailed Scores")
    for dim, sc in subscores.items():
        kv(dim, f"{sc:.1f} / 10")

    # ── Stats
    h1("Discourse Statistics")
    for k, v in stats.items():
        kv(k.replace("_", " ").title(), v)

    # ── Strengths / Weaknesses
    h1("Strengths & Weaknesses")
    h2("Strengths")
    for s in verdict.get("strengths", []):
        body(f"  ✓  {s}")
    h2("Weaknesses")
    for w in verdict.get("weaknesses", []):
        body(f"  ✗  {w}")
    h2("Recommended Improvements")
    for i in verdict.get("improvements", []):
        body(f"  →  {i}")

    # ── Discourse table
    h1("Classified Discourse Units")
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(230, 230, 250)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(100, 6, "Sentence", border=1, fill=True)
    pdf.cell(40, 6, "Category", border=1, fill=True)
    pdf.cell(22, 6, "Confidence", border=1, fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_font("Helvetica", "", 8)
    for _, row in df.iterrows():
        sent = row["sentence"][:80] + ("…" if len(row["sentence"]) > 80 else "")
        pdf.cell(100, 5, sent, border=1)
        pdf.cell(40, 5, row["category"], border=1)
        pdf.cell(22, 5, f"{row['confidence']:.0%}", border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # ── Devil summary
    h1("Devil's Advocate Review")
    for agent_key in ["logical", "ethical", "domain", "cultural", "evidence", "cultural", "pedagogy"]:
        agent = devil_results.get(agent_key, {})
        if agent:
            h2(f"{agent.get('icon', '')} {agent.get('agent', agent_key)}")
            body(agent.get("summary", ""))

    output = io.BytesIO()
    pdf.output(output)
    return output.getvalue()


# ── reportlab fallback ───────────────────────────────────────────────────────

def _pdf_reportlab(df, stats, verdict, subscores, keywords, topic, devil_results) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                             leftMargin=2*cm, rightMargin=2*cm,
                             topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    story = []

    title_style = ParagraphStyle("title", parent=styles["Title"],
                                  textColor=colors.HexColor("#5b47e8"))
    story.append(Paragraph("Essay Evaluation Report", title_style))
    story.append(Spacer(1, 12))
    story.append(Paragraph(f"Topic: {topic} | Score: {verdict.get('overall_score', 0):.1f}/10", styles["Normal"]))
    story.append(Spacer(1, 8))
    story.append(Paragraph(verdict.get("verdict_text", "").replace("**", "").replace("*", ""), styles["Normal"]))
    story.append(Spacer(1, 16))
    story.append(Paragraph("Detailed Scores", styles["Heading2"]))
    for k, v in subscores.items():
        story.append(Paragraph(f"• {k}: {v:.1f}/10", styles["Normal"]))
    story.append(Spacer(1, 12))
    story.append(Paragraph("Discourse Units", styles["Heading2"]))
    tdata = [["Sentence", "Category", "Confidence"]]
    for _, row in df.iterrows():
        tdata.append([row["sentence"][:70], row["category"], f"{row['confidence']:.0%}"])
    t = Table(tdata, colWidths=[10*cm, 4*cm, 2.5*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#5b47e8")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f4f2")]),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
    ]))
    story.append(t)
    doc.build(story)
    return buf.getvalue()


# ── plain text fallback ──────────────────────────────────────────────────────

def _pdf_plaintext(df, stats, verdict, subscores, keywords, topic, devil_results) -> bytes:
    lines = [
        "ESSAY EVALUATION REPORT",
        "=" * 60,
        f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"Topic: {topic}",
        f"Overall Score: {verdict.get('overall_score', 0):.1f} / 10",
        "",
        "VERDICT",
        "-" * 40,
        verdict.get("verdict_text", "").replace("**", "").replace("*", ""),
        "",
        "SCORES",
        "-" * 40,
    ]
    for k, v in subscores.items():
        lines.append(f"  {k}: {v:.1f}/10")
    lines += ["", "STATISTICS", "-" * 40]
    for k, v in stats.items():
        lines.append(f"  {k.replace('_',' ').title()}: {v}")
    lines += ["", "DISCOURSE UNITS", "-" * 40]
    for _, row in df.iterrows():
        lines.append(f"  [{row['category']}] {row['sentence'][:90]}")
    return "\n".join(lines).encode("utf-8")
