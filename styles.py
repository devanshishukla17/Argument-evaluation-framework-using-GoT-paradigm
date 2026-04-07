"""
styles.py — CSS styling for the Essay Evaluation Framework.
Supports dark and light themes.
"""

DARK_THEME_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700;800&family=DM+Mono:wght@300;400;500&family=DM+Sans:ital,wght@0,300;0,400;0,500;1,300&display=swap');

:root {
    --bg-primary: #0d0f14;
    --bg-secondary: #13161e;
    --bg-card: #1a1d27;
    --bg-card-hover: #1f2332;
    --accent-primary: #7c6af7;
    --accent-secondary: #4ecdc4;
    --accent-warning: #f7b731;
    --accent-danger: #fc5c65;
    --accent-success: #26de81;
    --text-primary: #e8eaf0;
    --text-secondary: #9298ae;
    --text-muted: #5a6177;
    --border-color: #262b3d;
    --shadow: 0 4px 24px rgba(0,0,0,0.4);
    --shadow-accent: 0 4px 24px rgba(124,106,247,0.15);
    --radius: 12px;
    --radius-sm: 8px;
}

html, body, [data-testid="stApp"] {
    background-color: var(--bg-primary) !important;
    font-family: 'DM Sans', sans-serif !important;
    color: var(--text-primary) !important;
}

[data-testid="stSidebar"] {
    background-color: var(--bg-secondary) !important;
    border-right: 1px solid var(--border-color) !important;
}

[data-testid="stSidebar"] * { color: var(--text-primary) !important; }

h1, h2, h3, h4, h5, h6 {
    font-family: 'Syne', sans-serif !important;
    color: var(--text-primary) !important;
    letter-spacing: -0.02em;
}

.metric-card {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: var(--radius);
    padding: 1.25rem 1.5rem;
    transition: all 0.2s ease;
    position: relative;
    overflow: hidden;
}

.metric-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    background: linear-gradient(90deg, var(--accent-primary), var(--accent-secondary));
}

.metric-value {
    font-family: 'Syne', sans-serif;
    font-size: 2.2rem;
    font-weight: 700;
    color: var(--accent-primary);
    line-height: 1;
    margin-bottom: 0.25rem;
}

.metric-label {
    font-family: 'DM Mono', monospace;
    font-size: 0.72rem;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.1em;
}

.tag {
    display: inline-block;
    padding: 0.2rem 0.65rem;
    border-radius: 99px;
    font-size: 0.72rem;
    font-family: 'DM Mono', monospace;
    font-weight: 500;
    letter-spacing: 0.05em;
}

.tag-claim { background: rgba(124,106,247,0.15); color: #a89ef9; border: 1px solid rgba(124,106,247,0.3); }
.tag-evidence { background: rgba(78,205,196,0.15); color: #6ee7e0; border: 1px solid rgba(78,205,196,0.3); }
.tag-counterclaim { background: rgba(252,92,101,0.15); color: #fd8a8f; border: 1px solid rgba(252,92,101,0.3); }
.tag-rebuttal { background: rgba(247,183,49,0.15); color: #fac95e; border: 1px solid rgba(247,183,49,0.3); }
.tag-assumption { background: rgba(253,150,68,0.15); color: #fda46f; border: 1px solid rgba(253,150,68,0.3); }
.tag-fallacy { background: rgba(252,92,101,0.2); color: #fc5c65; border: 1px solid rgba(252,92,101,0.4); }
.tag-missing { background: rgba(90,97,119,0.2); color: #9298ae; border: 1px solid rgba(90,97,119,0.3); }
.tag-strong { background: rgba(38,222,129,0.15); color: #26de81; border: 1px solid rgba(38,222,129,0.3); }
.tag-weak { background: rgba(247,183,49,0.15); color: #f7b731; border: 1px solid rgba(247,183,49,0.3); }

.section-card {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: var(--radius);
    padding: 1.5rem;
    margin: 1rem 0;
}

.feedback-item {
    padding: 0.85rem 1rem;
    border-radius: var(--radius-sm);
    margin: 0.5rem 0;
    border-left: 3px solid;
    font-size: 0.9rem;
}

.feedback-strength { background: rgba(38,222,129,0.08); border-color: #26de81; color: #a8f0ce; }
.feedback-weakness { background: rgba(252,92,101,0.08); border-color: #fc5c65; color: #fdb4b8; }
.feedback-suggestion { background: rgba(124,106,247,0.08); border-color: #7c6af7; color: #c2bafc; }
.feedback-missing { background: rgba(90,97,119,0.12); border-color: #5a6177; color: var(--text-secondary); }

.sentence-highlight {
    display: block;
    padding: 0.6rem 0.9rem;
    border-radius: var(--radius-sm);
    margin: 0.35rem 0;
    font-size: 0.88rem;
    line-height: 1.55;
}
.sh-claim { background: rgba(124,106,247,0.12); border-left: 3px solid #7c6af7; }
.sh-evidence { background: rgba(78,205,196,0.12); border-left: 3px solid #4ecdc4; }
.sh-counterclaim { background: rgba(252,92,101,0.12); border-left: 3px solid #fc5c65; }
.sh-rebuttal { background: rgba(247,183,49,0.12); border-left: 3px solid #f7b731; }
.sh-assumption { background: rgba(253,150,68,0.12); border-left: 3px solid #fd9644; }
.sh-default { background: rgba(26,29,39,0.8); border-left: 3px solid #262b3d; }

.devil-card {
    background: linear-gradient(135deg, rgba(252,92,101,0.05), rgba(252,92,101,0.02));
    border: 1px solid rgba(252,92,101,0.2);
    border-radius: var(--radius);
    padding: 1.25rem 1.5rem;
    margin: 0.75rem 0;
}

.score-bar-wrap { margin-bottom: 1rem; }
.score-bar-header { display:flex; justify-content:space-between; margin-bottom:0.3rem; }
.score-bar-label { font-size:0.85rem; color:#9298ae; }
.score-bar-value { font-family:'DM Mono',monospace; font-size:0.8rem; font-weight:600; }
.score-bar-track { background:#1a1d27; border-radius:99px; height:8px; overflow:hidden; }
.score-bar-fill { height:100%; border-radius:99px; transition:width 0.8s; }

.page-header { padding: 1.5rem 0 2rem 0; border-bottom: 1px solid var(--border-color); margin-bottom: 2rem; }
.page-title { font-family: 'Syne', sans-serif; font-size: 2rem; font-weight: 800; color: var(--text-primary); letter-spacing: -0.03em; margin: 0 0 0.4rem 0; }
.page-subtitle { font-family: 'DM Mono', monospace; font-size: 0.78rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.1em; }

.verdict-box {
    background: linear-gradient(135deg, rgba(124,106,247,0.08), rgba(78,205,196,0.05));
    border: 1px solid rgba(124,106,247,0.25);
    border-radius: var(--radius);
    padding: 1.5rem;
    margin: 1rem 0;
}

.got-branch { background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: var(--radius-sm); padding: 1rem 1.25rem; margin: 0.5rem 0; }
.got-branch.best { border-color: var(--accent-primary); background: rgba(124,106,247,0.06); }

.confidence-pill { display:inline-block; padding:0.15rem 0.6rem; border-radius:99px; font-size:0.72rem; font-family:'DM Mono',monospace; font-weight:600; }
.pill-high { background: rgba(38,222,129,0.15); color: #26de81; }
.pill-med  { background: rgba(247,183,49,0.15); color: #f7b731; }
.pill-low  { background: rgba(252,92,101,0.15); color: #fc5c65; }

.sidebar-logo { font-family: 'Syne', sans-serif; font-size: 1.3rem; font-weight: 800; letter-spacing: -0.03em; color: var(--accent-primary); padding: 0.5rem 0 1.5rem 0; }
.nav-section-label { font-family: 'DM Mono', monospace; font-size: 0.65rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.12em; padding: 0.75rem 0 0.25rem 0; }

.path-item { display:flex; align-items:flex-start; gap:1rem; padding:0.85rem 1rem; background:var(--bg-secondary); border-radius:var(--radius-sm); margin:0.4rem 0; font-size:0.88rem; }
.branch-connector { display:flex; align-items:center; gap:0.5rem; font-size:0.82rem; color:var(--text-muted); padding:0.15rem 1rem; }

.stButton > button { background: linear-gradient(135deg, var(--accent-primary), #9b8cf9) !important; color: white !important; border: none !important; border-radius: var(--radius-sm) !important; }
.stTextArea textarea, .stTextInput input { background: var(--bg-secondary) !important; border: 1px solid var(--border-color) !important; border-radius: var(--radius-sm) !important; color: var(--text-primary) !important; }
.stTextArea textarea:focus, .stTextInput input:focus { border-color: var(--accent-primary) !important; }
[data-testid="metric-container"] { background: var(--bg-card) !important; border: 1px solid var(--border-color) !important; border-radius: var(--radius) !important; }
.stProgress > div > div > div { background: linear-gradient(90deg, var(--accent-primary), var(--accent-secondary)) !important; }
.stTabs [data-baseweb="tab-list"] { background: var(--bg-secondary) !important; border-radius: var(--radius-sm) !important; }
.stTabs [data-baseweb="tab"] { background: transparent !important; color: var(--text-secondary) !important; border-radius: var(--radius-sm) !important; }
.stTabs [aria-selected="true"] { background: var(--bg-card) !important; color: var(--text-primary) !important; }
.stExpander { background: var(--bg-card) !important; border: 1px solid var(--border-color) !important; border-radius: var(--radius-sm) !important; }
hr { border-color: var(--border-color) !important; }

.graph-legend { display:flex; flex-wrap:wrap; gap:0.5rem; padding:0.75rem 1rem; background:var(--bg-secondary); border-radius:var(--radius-sm); margin:0.5rem 0; }
.legend-item { display:flex; align-items:center; gap:0.4rem; font-size:0.76rem; font-family:'DM Mono',monospace; color:var(--text-secondary); }
.legend-dot { width:10px; height:10px; border-radius:50%; flex-shrink:0; }

.graph-insight {
    background: linear-gradient(135deg, rgba(78,205,196,0.06), rgba(124,106,247,0.04));
    border: 1px solid rgba(78,205,196,0.2);
    border-left: 3px solid #4ecdc4;
    border-radius: var(--radius-sm);
    padding: 0.75rem 1rem;
    margin: 0.5rem 0 1.25rem 0;
    font-size: 0.87rem;
    color: var(--text-secondary);
    line-height: 1.55;
}

.export-card {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: var(--radius);
    padding: 1.5rem;
    text-align: center;
    transition: all 0.2s;
}
.export-card:hover { border-color: var(--accent-primary); }

::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--bg-secondary); }
::-webkit-scrollbar-thumb { background: var(--border-color); border-radius: 3px; }
</style>
"""

LIGHT_THEME_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700;800&family=DM+Mono:wght@300;400;500&family=DM+Sans:ital,wght@0,300;0,400;0,500;1,300&display=swap');
:root {
    --bg-primary: #f5f4f2; --bg-secondary: #eeede9; --bg-card: #ffffff;
    --accent-primary: #5b47e8; --accent-secondary: #0fbfb5;
    --accent-warning: #d4900a; --accent-danger: #d93d46; --accent-success: #1a9e57;
    --text-primary: #1a1a2e; --text-secondary: #5a5a7a; --text-muted: #9898b0;
    --border-color: #e0deda; --radius: 12px; --radius-sm: 8px;
}
html, body, [data-testid="stApp"] { background-color: var(--bg-primary) !important; font-family: 'DM Sans', sans-serif !important; }
[data-testid="stSidebar"] { background-color: var(--bg-card) !important; border-right: 1px solid var(--border-color) !important; }
h1,h2,h3,h4,h5,h6 { font-family: 'Syne', sans-serif !important; }
.metric-card { background: var(--bg-card); border: 1px solid var(--border-color); border-radius: var(--radius); padding: 1.25rem 1.5rem; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
.metric-value { font-family: 'Syne', sans-serif; font-size: 2.2rem; font-weight: 700; color: var(--accent-primary); }
.metric-label { font-family: 'DM Mono', monospace; font-size: 0.72rem; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.1em; }
.tag { display:inline-block; padding:0.2rem 0.65rem; border-radius:99px; font-size:0.72rem; font-family:'DM Mono',monospace; font-weight:500; }
.tag-claim { background:rgba(91,71,232,0.1); color:#5b47e8; border:1px solid rgba(91,71,232,0.3); }
.tag-evidence { background:rgba(15,191,181,0.1); color:#0a9e96; border:1px solid rgba(15,191,181,0.3); }
.tag-counterclaim { background:rgba(217,61,70,0.1); color:#d93d46; border:1px solid rgba(217,61,70,0.3); }
.tag-rebuttal { background:rgba(212,144,10,0.1); color:#b37800; border:1px solid rgba(212,144,10,0.3); }
.tag-assumption { background:rgba(253,150,68,0.1); color:#c05f00; border:1px solid rgba(253,150,68,0.3); }
.tag-fallacy { background:rgba(217,61,70,0.15); color:#d93d46; border:1px solid rgba(217,61,70,0.4); }
.tag-missing { background:rgba(100,100,120,0.1); color:#5a5a7a; border:1px solid rgba(100,100,120,0.2); }
.tag-strong { background:rgba(26,158,87,0.1); color:#1a9e57; border:1px solid rgba(26,158,87,0.3); }
.tag-weak { background:rgba(212,144,10,0.1); color:#b37800; border:1px solid rgba(212,144,10,0.3); }
.section-card { background:var(--bg-card); border:1px solid var(--border-color); border-radius:var(--radius); padding:1.5rem; margin:1rem 0; }
.feedback-item { padding:0.85rem 1rem; border-radius:var(--radius-sm); margin:0.5rem 0; border-left:3px solid; font-size:0.9rem; }
.feedback-strength { background:rgba(26,158,87,0.06); border-color:#1a9e57; color:#145c38; }
.feedback-weakness { background:rgba(217,61,70,0.06); border-color:#d93d46; color:#8b1c23; }
.feedback-suggestion { background:rgba(91,71,232,0.06); border-color:#5b47e8; color:#3c2dad; }
.feedback-missing { background:rgba(100,100,120,0.08); border-color:#9898b0; color:#5a5a7a; }
.sentence-highlight { display:block; padding:0.6rem 0.9rem; border-radius:var(--radius-sm); margin:0.35rem 0; font-size:0.88rem; line-height:1.55; }
.sh-claim { background:rgba(91,71,232,0.07); border-left:3px solid #5b47e8; }
.sh-evidence { background:rgba(15,191,181,0.07); border-left:3px solid #0fbfb5; }
.sh-counterclaim { background:rgba(217,61,70,0.07); border-left:3px solid #d93d46; }
.sh-rebuttal { background:rgba(212,144,10,0.07); border-left:3px solid #d4900a; }
.sh-assumption { background:rgba(253,150,68,0.07); border-left:3px solid #fd9644; }
.sh-default { background:rgba(240,240,240,0.8); border-left:3px solid #e0deda; }
.page-header { padding:1.5rem 0 2rem 0; border-bottom:1px solid var(--border-color); margin-bottom:2rem; }
.page-title { font-family:'Syne',sans-serif; font-size:2rem; font-weight:800; color:var(--text-primary); }
.page-subtitle { font-family:'DM Mono',monospace; font-size:0.78rem; color:var(--text-muted); text-transform:uppercase; letter-spacing:0.1em; }
.verdict-box { background:linear-gradient(135deg,rgba(91,71,232,0.06),rgba(15,191,181,0.04)); border:1px solid rgba(91,71,232,0.2); border-radius:var(--radius); padding:1.5rem; margin:1rem 0; }
.got-branch { background:var(--bg-secondary); border:1px solid var(--border-color); border-radius:var(--radius-sm); padding:1rem 1.25rem; margin:0.5rem 0; }
.confidence-pill { display:inline-block; padding:0.15rem 0.6rem; border-radius:99px; font-size:0.72rem; font-family:'DM Mono',monospace; font-weight:600; }
.pill-high { background:rgba(26,158,87,0.15); color:#1a9e57; }
.pill-med  { background:rgba(212,144,10,0.15); color:#b37800; }
.pill-low  { background:rgba(217,61,70,0.15); color:#d93d46; }
.sidebar-logo { font-family:'Syne',sans-serif; font-size:1.3rem; font-weight:800; color:var(--accent-primary); padding:0.5rem 0 1.5rem 0; }
.nav-section-label { font-family:'DM Mono',monospace; font-size:0.65rem; color:var(--text-muted); text-transform:uppercase; letter-spacing:0.12em; padding:0.75rem 0 0.25rem 0; }
.path-item { display:flex; align-items:flex-start; gap:1rem; padding:0.85rem 1rem; background:var(--bg-secondary); border-radius:var(--radius-sm); margin:0.4rem 0; }
.graph-legend { display:flex; flex-wrap:wrap; gap:0.5rem; padding:0.75rem 1rem; background:var(--bg-secondary); border-radius:var(--radius-sm); margin:0.5rem 0; }
.legend-item { display:flex; align-items:center; gap:0.4rem; font-size:0.76rem; font-family:'DM Mono',monospace; color:var(--text-secondary); }
.legend-dot { width:10px; height:10px; border-radius:50%; flex-shrink:0; }
.graph-insight { background:linear-gradient(135deg,rgba(15,191,181,0.06),rgba(91,71,232,0.04)); border:1px solid rgba(15,191,181,0.2); border-left:3px solid #0fbfb5; border-radius:var(--radius-sm); padding:0.75rem 1rem; margin:0.5rem 0 1.25rem 0; font-size:0.87rem; color:var(--text-secondary); line-height:1.55; }
.score-bar-wrap { margin-bottom:1rem; }
.score-bar-header { display:flex; justify-content:space-between; margin-bottom:0.3rem; }
.score-bar-label { font-size:0.85rem; color:var(--text-secondary); }
.score-bar-value { font-family:'DM Mono',monospace; font-size:0.8rem; font-weight:600; }
.score-bar-track { background:var(--bg-secondary); border-radius:99px; height:8px; overflow:hidden; }
.score-bar-fill { height:100%; border-radius:99px; }
</style>
"""


def get_css(theme: str = "dark") -> str:
    return DARK_THEME_CSS if theme == "dark" else LIGHT_THEME_CSS


def metric_card_html(value, label, color="#7c6af7", icon="") -> str:
    return f"""
    <div class="metric-card">
        <div class="metric-value" style="color:{color}">{icon} {value}</div>
        <div class="metric-label">{label}</div>
    </div>
    """


def tag_html(text: str, category: str) -> str:
    cls_map = {
        "Claim": "tag-claim", "Unsupported Claim": "tag-fallacy",
        "Position": "tag-claim", "Evidence": "tag-evidence",
        "Strong Evidence": "tag-strong", "Weak Evidence": "tag-weak",
        "Counterclaim": "tag-counterclaim", "Rebuttal": "tag-rebuttal",
        "Assumption": "tag-assumption", "Premise": "tag-assumption",
        "Logical Fallacy": "tag-fallacy", "Missing Evidence": "tag-missing",
        "Bias Indicator": "tag-weak",
    }
    cls = cls_map.get(category, "tag-claim")
    return f'<span class="tag {cls}">{text}</span>'


def score_bar_html(score: float, label: str) -> str:
    """Render a single score bar as self-contained HTML with inline styles only."""
    pct = min(100, max(0, score * 10))
    color = "#26de81" if score >= 7 else ("#f7b731" if score >= 4 else "#fc5c65")
    return f"""<div style="margin-bottom:1rem">
  <div style="display:flex;justify-content:space-between;margin-bottom:0.3rem">
    <span style="font-size:0.85rem;color:#9298ae">{label}</span>
    <span style="font-family:'DM Mono',monospace;font-size:0.8rem;color:{color};font-weight:600">{score:.1f}/10</span>
  </div>
  <div style="background:#1a1d27;border-radius:99px;height:8px;overflow:hidden">
    <div style="width:{pct}%;height:100%;border-radius:99px;background:{color}"></div>
  </div>
</div>"""


def graph_legend_html(items: list[tuple[str, str]]) -> str:
    """items = list of (color_hex, label) tuples"""
    dots = "".join(
        f'<div class="legend-item"><div class="legend-dot" style="background:{col}"></div>{lbl}</div>'
        for col, lbl in items
    )
    return f'<div class="graph-legend">{dots}</div>'


def graph_insight_html(text: str) -> str:
    """A teal-accented 1-2 line insight box shown below each chart."""
    return f'<div class="graph-insight">💡 {text}</div>'
