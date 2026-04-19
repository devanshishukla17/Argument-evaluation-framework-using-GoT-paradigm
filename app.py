import io
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Essay Evaluation Framework", page_icon="", layout="wide",
                   initial_sidebar_state="expanded")

from styles import get_css, graph_legend_html, graph_insight_html, score_bar_html, tag_html
from discourse_classifier import classify_essay, get_summary_stats
from graph_builder import select_graph_type, get_graph_for_type, build_got_graph, build_argument_graph, build_hidden_assumption_graph
from got_engine import run_got_pipeline, rank_branches, merge_branches, generate_final_verdict
from devil_agents import run_all_agents
from explanation_engine import (generate_student_feedback, generate_teacher_feedback,
    compute_subscores, extract_keywords, detect_topic, explain_graph_type)
from visualization import (argument_network_chart, got_branch_timeline,
    subscore_chart, discourse_distribution_chart, devil_summary_chart,
    sentence_heatmap, pyvis_graph_html)
from dashboard import render_dashboard, render_score_bars
from student_dashboard import render_student_dashboard
from teacher_dashboard import render_teacher_dashboard

# Session state 
def _init():
    defs = dict(analysed=False, df=None, stats={}, verdict={}, subscores={},
                keywords=[], topic="General", branches=[], ranked_branches=[],
                best_branch={}, merged_branch={}, graph_type="standard_argument_graph",
                G=None, got_G=None, devil_results={}, student_fb=[], teacher_fb={},
                essay_text="", theme="dark", got_pipeline_used=False, got_aggregation={})
    for k, v in defs.items():
        if k not in st.session_state: st.session_state[k] = v

_init()
st.markdown(get_css(st.session_state.theme), unsafe_allow_html=True)

# Sidebar 
with st.sidebar:
    st.markdown('<div class="sidebar-logo"> EssayEval<span style="color:#4ecdc4">AI</span></div>', unsafe_allow_html=True)
    tc = st.radio("Theme", ["dark","light"], index=0 if st.session_state.theme=="dark" else 1, horizontal=True)
    if tc != st.session_state.theme:
        st.session_state.theme = tc; st.rerun()

    st.markdown('<div class="nav-section-label">Navigation</div>', unsafe_allow_html=True)
    pages = [("","Home Dashboard"),("","Full Argument Graph"),("","GoT Explorer"),
             ("","Aggregation & Refinement"),("","Devil's Advocate Review"),
             ("","Student Dashboard"),("","Teacher Dashboard")]
    page_labels = [f"{i} {l}" for i,l in pages]
    sel = st.radio("", page_labels, label_visibility="collapsed")
    page_name = sel.split(" ",1)[1]

    if st.session_state.analysed:
        st.markdown('<div class="nav-section-label">Quick Stats</div>', unsafe_allow_html=True)
        s = st.session_state.stats
        sc_val = st.session_state.verdict.get("overall_score",0)
        sc_col = "green" if sc_val>=7 else ("orange" if sc_val>=4 else "red")
        st.markdown(f"""<div style="font-size:.82rem">
            <div style="display:flex;justify-content:space-between;margin:.25rem 0"><span style="color:#9298ae">Score</span><b style="color:{sc_col}">{sc_val:.1f}/10</b></div>
            <div style="display:flex;justify-content:space-between;margin:.25rem 0"><span style="color:#9298ae">Sentences</span><b>{s.get('total_sentences',0)}</b></div>
            <div style="display:flex;justify-content:space-between;margin:.25rem 0"><span style="color:#9298ae">Claims</span><b>{s.get('claim_count',0)}</b></div>
            <div style="display:flex;justify-content:space-between;margin:.25rem 0"><span style="color:#9298ae">Evidence</span><b>{s.get('evidence_count',0)}</b></div>
            <div style="display:flex;justify-content:space-between;margin:.25rem 0"><span style="color:#9298ae">Topic</span><b style="font-size:.78rem">{st.session_state.topic[:22]}</b></div>
        </div>""", unsafe_allow_html=True)


# Graph legend constants 
ARGUMENT_LEGEND = [
    ("#7c6af7","Claim"), ("#4ecdc4","Evidence"), ("#00cec9","Strong Evidence"),
    ("#fc5c65","Counterclaim"), ("#f7b731","Rebuttal"), ("#fd9644","Assumption"),
    ("#5a6177","Missing Evidence"), ("#74b9ff","Position"), ("#26de81","Concluding"),
    ("#e17055","Logical Fallacy"), ("#d63031","Unsupported Claim"),
]
EDGE_LEGEND = [
    ("#26de81","supports"), ("#fc5c65","contradicts"),
    ("#f7b731","rebuts"), ("#5a6177","extends/other"),
]


# Analysis pipeline 
def _run_analysis(essay_text: str):
    with st.spinner(" Classifying discourse units..."):
        df = classify_essay(essay_text)
    if df.empty:
        st.error("Too short  -  please provide a longer essay."); return

    with st.spinner(" Computing statistics..."):
        stats = get_summary_stats(df)
        keywords = extract_keywords(df)
        topic = detect_topic(df, keywords)

    with st.spinner(" Building argument graph..."):
        graph_type = select_graph_type(stats)
        G = get_graph_for_type(df, graph_type)

    with st.spinner("🧠 Running Graph-of-Thought pipeline (4 LLM steps: Generate → Score → Aggregate → Refine)..."):
        got_result = run_got_pipeline(essay_text, df, stats)

    branches = got_result["branches"]
    ranked   = got_result["ranked_branches"]
    best     = got_result["best_branch"]
    merged   = got_result["merged_branch"]
    verdict  = got_result["verdict"]
    got_G    = build_got_graph(branches)
    got_pipeline_used = got_result.get("got_pipeline", False)

    with st.spinner(" Running Devil's Advocate agents..."):
        devil_results = run_all_agents(df)

    with st.spinner(" Generating feedback..."):
        subscores = compute_subscores(df, stats)
        student_fb = generate_student_feedback(df, verdict, stats)
        teacher_fb = generate_teacher_feedback(df, verdict, stats, devil_results)

    st.session_state.update(dict(
        analysed=True, df=df, stats=stats, verdict=verdict, subscores=subscores,
        keywords=keywords, topic=topic, branches=branches, ranked_branches=ranked,
        best_branch=best, merged_branch=merged, graph_type=graph_type,
        G=G, got_G=got_G, devil_results=devil_results,
        student_fb=student_fb, teacher_fb=teacher_fb, essay_text=essay_text,
        got_pipeline_used=got_pipeline_used,
        got_aggregation=got_result.get("aggregation", {})))
    st.success(" Analysis complete!"); st.rerun()


def _sample_essay():
    return """Social media has fundamentally transformed the way people communicate, share information, and participate in democratic life. The question of whether governments should regulate these platforms is one of the most pressing policy debates of our time. It is clear that without strict government regulation, social media companies will continue to cause irreparable harm to society.

Social media platforms have been proven to spread misinformation at an alarming rate. According to a 2022 MIT study, false news spreads six times faster on Twitter than accurate information. This directly undermines public trust in institutions and has real-world consequences, such as vaccine hesitancy and election interference. Furthermore, a report by the Reuters Institute found that 48% of people in surveyed countries encountered misinformation on social media at least once a week.

Everyone knows that social media companies only care about profit and will never self-regulate effectively. Facebook, Instagram, and TikTok have repeatedly failed to remove harmful content despite public pressure. If platforms are not forced to act, they never will. The government must therefore step in immediately and impose strict content moderation laws.

However, critics argue that government regulation of social media poses a serious threat to free speech. In authoritarian countries such as China and Russia, internet regulation has been used as a tool for censorship and political suppression. The opponents of regulation claim that any government control over online speech will inevitably lead to the silencing of political dissent and minority voices.

Nevertheless, there is a clear difference between democratic regulation designed to protect citizens and authoritarian censorship designed to silence them. The European Union's Digital Services Act, introduced in 2023, demonstrates that it is entirely possible to create a regulatory framework that holds platforms accountable for harmful content while preserving freedom of expression. This law requires platforms to be transparent about their algorithms and to remove illegal content within strict deadlines.

It can be assumed that all citizens want to live in a society free from online harassment, hate speech, and coordinated disinformation campaigns. Young people, who are the heaviest users of social media, are particularly vulnerable. A study published in the journal JAMA Pediatrics found that teenagers who spent more than three hours per day on social media were significantly more likely to report symptoms of anxiety and depression.

On the other hand, some researchers argue that the link between social media use and mental health is more complex than it first appears. Jonathan Haidt's work has been criticised by other psychologists who point out that correlation does not equal causation. The evidence base for a direct causal link between social media and mental illness remains contested among experts.

Social media companies are clearly evil corporations that do not deserve to operate freely in democratic societies. Their greed has destroyed a generation of young people. No reasonable person could defend giving these companies any further freedoms.

Governments should therefore adopt a tiered regulatory approach. Smaller platforms with fewer than one million users should face lighter requirements, while large platforms with significant societal influence should be subject to algorithmic transparency laws, mandatory content moderation audits, and substantial financial penalties for repeated violations. This proportionate approach balances innovation with accountability.

In conclusion, the evidence strongly supports the case for democratic government regulation of social media platforms. While free speech concerns are valid and must be carefully considered, the documented harms of unregulated social media  -  from misinformation to mental health damage  -  are too significant to ignore. Thoughtful, proportionate regulation is not the enemy of free expression; it is its guardian.""".strip()


def _weak_essay():
    return """Social media is bad for society. People spend too much time on their phones and this causes many problems. Everyone knows that Facebook and Instagram have made teenagers depressed. Companies don't care about users, they only want money. The government should ban social media because it is dangerous.

Young people are addicted to their devices. This is obvious to anyone who walks down the street. Schools are suffering because students can't concentrate. Teachers also agree that phones are a big problem. Life was better before social media existed.

Some people say social media is good for communication but they are wrong. The benefits do not outweigh the harms. All social media platforms should be regulated immediately or society will collapse. We must act now before it is too late.

In conclusion, social media is destroying the world and we need to do something about it right away.""".strip()


def _render_input():
    st.markdown("""<div class="page-header">
        <div class="page-title">Essay Evaluation Framework</div>
        <div class="page-subtitle">Graph-of-Thought . Devil's Advocate . Dynamic Analysis</div>
    </div>""", unsafe_allow_html=True)

    col_info, col_input = st.columns([1,2])
    with col_info:
        st.markdown("""<div class="section-card">
            <div style="font-family:'Syne',sans-serif;font-size:1rem;font-weight:700;margin-bottom:.75rem;color:#7c6af7">What this tool does</div>
            <div style="font-size:.87rem;line-height:1.7;color:#9298ae">
            <b style="color:#e8eaf0">1. Discourse Classification</b><br>Labels every sentence: Claim, Evidence, Counterclaim + 15 more categories.<br><br>
            <b style="color:#e8eaf0">2. Argument Graph</b><br>Shows how ideas connect  -  what supports what, what contradicts what.<br><br>
            <b style="color:#e8eaf0">3. Graph-of-Thought</b><br>Generates multiple reasoning branches, scores them, finds the strongest path.<br><br>
            <b style="color:#e8eaf0">4. Devil's Advocate</b><br>7 agents challenge your essay from every angle: logic, ethics, culture, evidence.<br><br>
            <b style="color:#e8eaf0">5. Feedback & Export</b><br>Student-friendly + teacher-grade feedback. Export as CSV, JSON or PDF.
            </div></div>""", unsafe_allow_html=True)

    with col_input:
        method = st.radio("Input", [" Type / Paste"," Upload File"], horizontal=True, label_visibility="collapsed")
        essay_text = ""
        if "" in method:
            essay_text = st.text_area("Essay:", height=260, placeholder="Paste your essay here...", label_visibility="collapsed")
        else:
            f = st.file_uploader("Upload .txt or .pdf", type=["txt","pdf"])
            if f:
                if f.name.endswith(".pdf"):
                    try:
                        import PyPDF2
                        essay_text = "\n".join(p.extract_text() or "" for p in PyPDF2.PdfReader(io.BytesIO(f.read())).pages)
                    except: essay_text = ""
                else:
                    essay_text = f.read().decode("utf-8","replace")
                if essay_text: st.success(f" {len(essay_text.split())} words loaded")

        c1,c2,c3 = st.columns([2,1,1])
        with c1:
            if st.button(" Analyse Essay", type="primary", use_container_width=True):
                if essay_text and len(essay_text.strip())>50: _run_analysis(essay_text)
                else: st.warning("Please enter a longer essay.")
        with c2:
            if st.button("Load Strong Sample", use_container_width=True): _run_analysis(_sample_essay())
        with c3:
            if st.button("Load Weak Sample", use_container_width=True): _run_analysis(_weak_essay())

    if not st.session_state.analysed:
        st.markdown("---")
        cards = [("","Argument Graph","Visualise how claims, evidence and counterarguments connect."),
                 ("","Graph-of-Thought","Multiple reasoning paths scored and ranked by logical strength."),
                 ("","Devil's Advocate","7 agents challenge your argument from every angle."),
                 ("","Detailed Scores","Evidence, logic, bias, readability scored out of 10."),
                 ("","Student View","Sentence-by-sentence annotated feedback.")]
        cols = st.columns(3)
        for i,(ico,ttl,desc) in enumerate(cards):
            with cols[i%3]:
                st.markdown(f"""<div class="metric-card" style="min-height:110px">
                    <div style="font-size:1.5rem;margin-bottom:.5rem">{ico}</div>
                    <div style="font-family:'Syne',sans-serif;font-weight:700;margin-bottom:.35rem">{ttl}</div>
                    <div style="font-size:.82rem;color:#9298ae">{desc}</div></div>""", unsafe_allow_html=True)


# 
# PAGE ROUTING
# 

if page_name == "Home Dashboard":
    if st.session_state.analysed:
        render_dashboard(st.session_state.df, st.session_state.stats, st.session_state.verdict,
                         st.session_state.subscores, st.session_state.keywords,
                         st.session_state.topic, st.session_state.best_branch)
        st.markdown("---")
        with st.expander(" Analyse a new essay"):
            _render_input()
    else:
        _render_input()

# FULL ARGUMENT GRAPH 
elif page_name == "Full Argument Graph":
    st.markdown("""<div class="page-header">
        <div class="page-title">Full Argument Graph</div>
        <div class="page-subtitle">Interactive . Directed . Discourse Relations</div>
    </div>""", unsafe_allow_html=True)

    if not st.session_state.analysed:
        st.info("Please analyse an essay first.")
    else:
        G = st.session_state.G
        gt = st.session_state.graph_type

        st.markdown(f"""<div class="section-card" style="margin-bottom:1rem">
            <b>Graph Type:</b> {gt.replace('_',' ').title()}<br>
            <span style="color:#9298ae;font-size:.88rem">{explain_graph_type(gt, st.session_state.stats)}</span>
        </div>""", unsafe_allow_html=True)

        # Node colour legend
        st.markdown("**Node colours:**", unsafe_allow_html=False)
        st.markdown(graph_legend_html(ARGUMENT_LEGEND), unsafe_allow_html=True)
        st.markdown("**Edge colours:**", unsafe_allow_html=False)
        st.markdown(graph_legend_html(EDGE_LEGEND), unsafe_allow_html=True)

        html = pyvis_graph_html(G, "Argument Graph")
        if html:
            st.components.v1.html(html, height=520, scrolling=True)
        else:
            fig = argument_network_chart(G, "Argument Graph")
            st.plotly_chart(fig, use_container_width=True)

        st.markdown(graph_insight_html(
            "Each node is a sentence coloured by its discourse type. "
            "Green arrows = support, red arrows = contradiction, yellow = rebuttal. "
            "Larger nodes have more connections and play a central role in the argument."
        ), unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            fig2 = argument_network_chart(build_argument_graph(st.session_state.df), "Standard Argument Graph")
            st.plotly_chart(fig2, use_container_width=True)
            st.markdown(graph_insight_html(
                "Standard view: shows the full claim   evidence   conclusion flow of the essay."
            ), unsafe_allow_html=True)
        with col2:
            assumption_count = st.session_state.stats.get("assumption_count", 0)
            if assumption_count > 0:
                fig3 = argument_network_chart(
                    build_hidden_assumption_graph(st.session_state.df), "Hidden Assumption Graph")
                st.plotly_chart(fig3, use_container_width=True)
                st.markdown(graph_insight_html(
                    "Hidden Assumption view: orange nodes flag unstated premises that claims "
                    "silently depend on. If a claim has no citation, a hidden assumption node is added."
                ), unsafe_allow_html=True)
            else:
                st.markdown(graph_insight_html(
                "No hidden assumptions detected in this essay. "
                "Hidden Assumption graph is only shown when Assumption-type sentences are present."
            ), unsafe_allow_html=True)
# GoT EXPLORER 
elif page_name == "GoT Explorer":
    st.markdown("""<div class="page-header">
        <div class="page-title">Graph-of-Thought Explorer</div>
        <div class="page-subtitle">Multiple Branches . Scored . Ranked . Synthesised</div>
    </div>""", unsafe_allow_html=True)

    if not st.session_state.analysed:
        st.info("Please analyse an essay first.")
    else:
        branches = st.session_state.ranked_branches
        best = st.session_state.best_branch
        merged = st.session_state.merged_branch

        c1,c2,c3 = st.columns(3)
        c1.metric("Reasoning Branches", len(branches))
        c2.metric("Best Branch", best.get("name","N/A")[:25])
        c3.metric("Best Score", f"{best.get('scores',{}).get('overall',0):.0%}")

        # GoT pipeline status badge
        got_used = st.session_state.get("got_pipeline_used", False)
        if got_used:
            st.markdown("""<div style="background:linear-gradient(135deg,#7c6af7,#4ecdc4);
                border-radius:8px;padding:.6rem 1.2rem;margin:.75rem 0;display:inline-block">
                <span style="font-family:'DM Mono',monospace;font-size:.78rem;font-weight:600;color:#fff">
                ✅ REAL GoT PIPELINE ACTIVE — Generate → Score → Aggregate → Refine (4 LLM calls)
                </span></div>""", unsafe_allow_html=True)
        else:
            st.warning("⚠️ GoT pipeline used local fallback (API unavailable). Scores are rule-based.")

        # Cross-branch insights from aggregation step
        agg = st.session_state.get("got_aggregation", {})
        if agg:
            st.markdown("---")
            st.markdown("""<div style="font-family:'Syne',sans-serif;font-size:1.05rem;
                font-weight:700;margin-bottom:.75rem">🔗 Cross-Branch Aggregation
                <span style="font-size:.72rem;font-weight:400;color:#9298ae;margin-left:.5rem">
                What the LLM found by reasoning OVER the whole graph</span></div>""",
                unsafe_allow_html=True)

            col_left, col_right = st.columns(2)
            with col_left:
                convergent = agg.get("convergent_signals", [])
                if convergent:
                    st.markdown("**✅ Convergent Signals** *(branches agree)*")
                    for s in convergent:
                        st.markdown(f'<div class="feedback-item feedback-strength">{s}</div>',
                                    unsafe_allow_html=True)
                contradictory = agg.get("contradictory_signals", [])
                if contradictory:
                    st.markdown("**⚡ Contradictory Signals** *(branches disagree)*")
                    for s in contradictory:
                        st.markdown(f'<div class="feedback-item feedback-weakness">{s}</div>',
                                    unsafe_allow_html=True)
            with col_right:
                insights = agg.get("cross_branch_insights", [])
                if insights:
                    st.markdown("**🔍 Cross-Branch Insights**")
                    for ins in insights:
                        st.markdown(f'<div class="feedback-item feedback-suggestion">{ins}</div>',
                                    unsafe_allow_html=True)

            graph_verdict = agg.get("graph_level_verdict", "")
            if graph_verdict:
                st.markdown(f"""<div class="verdict-box" style="margin-top:.75rem">
                    <div style="font-size:.75rem;font-family:'DM Mono',monospace;
                                color:#7c6af7;margin-bottom:.4rem">GRAPH-LEVEL VERDICT</div>
                    {graph_verdict}</div>""", unsafe_allow_html=True)

            got_note = st.session_state.verdict.get("got_synthesis_note", "")
            if got_note:
                st.markdown(graph_insight_html(
                    f"GoT advantage over single-pass: {got_note}"
                ), unsafe_allow_html=True)

        # Show Toulmin trait breakdown
        trait_data = st.session_state.verdict.get("trait_breakdown", {})
        if trait_data:
            st.markdown("---")
            st.markdown('''<div style="font-family:'Syne',sans-serif;font-size:1.05rem;font-weight:700;margin-bottom:.75rem">
                 Toulmin Scoring Breakdown
                <span style="font-size:.75rem;font-weight:400;color:#9298ae;font-family:'DM Mono',monospace;margin-left:.75rem">
                Toulmin (1958) adapted  -  raw 0-16 normalised to 0-10
                </span></div>''', unsafe_allow_html=True)
            trait_cols = st.columns(3)
            trait_items = [(k,v) for k,v in trait_data.items() if not k.startswith("_")]
            for i, (trait_name, trait) in enumerate(trait_items):
                s10 = trait["score_10"]
                color = "#26de81" if s10 >= 7 else ("#f7b731" if s10 >= 5 else "#fc5c65")
                with trait_cols[i % 3]:
                    st.markdown(f'''<div class="metric-card" style="margin-bottom:.75rem">
                        <div style="font-family:'DM Mono',monospace;font-size:.68rem;color:#9298ae;margin-bottom:.3rem">{trait_name}</div>
                        <div style="font-family:'Syne',sans-serif;font-size:1.6rem;font-weight:700;color:{color}">{s10}<span style="font-size:.8rem;color:#9298ae">/10</span></div>
                        <div style="font-size:.75rem;color:#9298ae;margin-top:.25rem">raw {trait["raw"]}/{trait["max"]}</div>
                        <div style="font-size:.78rem;color:#5a6177;margin-top:.3rem;line-height:1.4">{trait["note"]}</div>
                    </div>''', unsafe_allow_html=True)
            st.markdown(graph_insight_html(
                f"Scoring model: {st.session_state.verdict.get('scoring_model','Toulmin 6-trait')}. "
                "T2 Evidence Quality has the highest weight (max 4 pts). "
                "T4+T5 together measure counterargument depth."
            ), unsafe_allow_html=True)

        st.plotly_chart(got_branch_timeline(branches), use_container_width=True)
        st.markdown(graph_insight_html(
            "Each row is a reasoning branch. Each dot is a step in that branch, coloured by discourse type. "
            "A longer branch with more steps means a richer line of reasoning."
        ), unsafe_allow_html=True)

        # Radar chart removed per user request

        st.markdown("### Synthesised Best Path")
        if merged:
            st.markdown(f"""<div class="verdict-box">
                <b>{merged.get('name','')}</b>  -  {merged.get('description','')}<br><br>
                <b>Overall Score:</b> {merged.get('scores',{}).get('overall',0):.0%}
            </div>""", unsafe_allow_html=True)
            for i,step in enumerate(merged.get("steps",[])):
                cat = step.get("category","Claim")
                st.markdown(f"""<div class="path-item">
                    <span style="font-family:'DM Mono',monospace;font-size:.72rem;color:#5a6177">{i+1}</span>
                    <div>{tag_html(cat,cat)}<span style="margin-left:.5rem;font-size:.87rem">{step.get('label','')}</span></div>
                </div>""", unsafe_allow_html=True)
            st.markdown(graph_insight_html(
                "The synthesised path merges the highest-confidence steps from all branches into one optimal reasoning chain."
            ), unsafe_allow_html=True)

# AGGREGATION & REFINEMENT 
elif page_name == "Aggregation & Refinement":
    st.markdown("""<div class="page-header">
        <div class="page-title">Aggregation & Refinement</div>
        <div class="page-subtitle">Discourse Statistics . Evidence Analysis . Heatmap</div>
    </div>""", unsafe_allow_html=True)

    if not st.session_state.analysed:
        st.info("Please analyse an essay first.")
    else:
        from explanation_engine import explain_aggregation
        df = st.session_state.df; stats = st.session_state.stats
        st.markdown(f'<div class="section-card">{explain_aggregation(stats)}</div>', unsafe_allow_html=True)

        col1,col2 = st.columns(2)
        with col1:
            st.plotly_chart(discourse_distribution_chart(df), use_container_width=True)
            st.markdown(graph_insight_html(
                "Distribution of all discourse types. Evidence-rich essays have taller teal bars. "
                "A high Unsupported Claim count (red) means the argument needs more backing."
            ), unsafe_allow_html=True)
        with col2:
            st.plotly_chart(sentence_heatmap(df), use_container_width=True)
            st.markdown(graph_insight_html(
                "Heatmap: each column is a sentence, each row is a quality dimension. "
                "Bright purple = high / present. Dark = low / absent. "
                "Look for dark columns in 'Missing Evidence' to find gaps."
            ), unsafe_allow_html=True)

        st.markdown("### Evidence vs Claims")
        ev_data = pd.DataFrame({
            "Category": ["Strong Evidence","Evidence","Weak Evidence","Claim","Unsupported Claim","Counterclaim"],
            "Count": [stats.get("strong_evidence_count",0),
                      max(0,stats.get("evidence_count",0)-stats.get("strong_evidence_count",0)),
                      stats.get("weak_evidence_count",0),
                      max(0,stats.get("claim_count",0)-stats.get("unsupported_count",0)),
                      stats.get("unsupported_count",0),
                      stats.get("counterclaim_count",0)]})
        import plotly.express as px
        fig = px.bar(ev_data, x="Category", y="Count", color="Category", template="plotly_dark",
                     color_discrete_map={"Strong Evidence":"#26de81","Evidence":"#4ecdc4","Weak Evidence":"#f7b731",
                                         "Claim":"#7c6af7","Unsupported Claim":"#fc5c65","Counterclaim":"#fd9644"})
        fig.update_layout(paper_bgcolor="#13161e",plot_bgcolor="#0d0f14",showlegend=False,height=300)
        st.plotly_chart(fig, use_container_width=True)
        st.markdown(graph_insight_html(
            "A strong essay has more green/teal bars (evidence) than red/orange (unsupported claims). "
            "Every Claim should be paired with at least one Evidence."
        ), unsafe_allow_html=True)

# DEVIL'S ADVOCATE 
elif page_name == "Devil's Advocate Review":
    st.markdown("""<div class="page-header">
        <div class="page-title">Devil's Advocate Review</div>
        <div class="page-subtitle">7 Specialist Agents . Plain-English Critique</div>
    </div>""", unsafe_allow_html=True)

    if not st.session_state.analysed:
        st.info("Please analyse an essay first.")
    else:
        devil = st.session_state.devil_results
        syn = devil.get("synthesis",{})

        # What is this page?
        st.markdown("""<div class="graph-insight">
             <b>What is Devil's Advocate?</b> Seven specialised AI agents read your essay and argue against it  -  
            on purpose. Each agent plays a different role: one checks your logic, one checks your ethics, 
            one checks if your evidence is strong enough, and so on. Their job is to find every weakness 
            before your real reader does. Use this feedback to make your argument bulletproof.
        </div>""", unsafe_allow_html=True)

        c1,c2,c3 = st.columns(3)
        c1.metric("Total Issues Found", syn.get("total_issues",0))
        c2.metric("High Severity", syn.get("high_severity",0))
        c3.metric("Agents Run", 7)

        for pt in syn.get("summary_points",[]):
            cls = "feedback-weakness" if ("" in pt or "" in pt) else "feedback-strength"
            st.markdown(f'<div class="feedback-item {cls}">{pt}</div>', unsafe_allow_html=True)

        st.plotly_chart(devil_summary_chart(devil), use_container_width=True)
        st.markdown(graph_insight_html(
            "Each bar shows how many issues a particular agent found. "
            "A long bar doesn't always mean the essay is bad  -  the Pedagogy agent will always have suggestions."
        ), unsafe_allow_html=True)

        st.markdown("---")

        # Agent explanations  -  plain English
        agent_meta = {
            "logical": ("","Logical Devil","Checks whether your reasoning makes sense. Looks for logical fallacies (e.g. 'everyone knows'), contradictions between statements, and claims you made without any proof."),
            "ethical": ("","Ethical Devil","Checks whether any statements could be seen as unfair, discriminatory, or harmful. Flags language that singles out groups of people or makes moral judgements without justification."),
            "domain": ("","Domain Devil","Checks whether domain-specific facts (science, law, history, technology) are backed by a credible source. Flags expert-area claims that have no citation."),
            "cultural": ("","Cultural Devil","Checks whether the essay assumes one culture's values apply universally. Flags overgeneralisations like 'all people' or 'every society' and Western-centric assumptions."),
            "counterargument":("","Counterargument Devil","For each of your main claims, generates the strongest possible opposing argument. Use these to strengthen your essay by pre-empting objections."),
            "evidence": ("","Evidence Devil","Audits the quality of your evidence. Distinguishes between strong evidence (studies, statistics, peer-reviewed research) and weak evidence (opinions, anecdotes, 'people say')."),
            "pedagogy": ("","Pedagogy Devil","Checks writing quality. Looks for vague pronouns, hedging words ('very', 'quite'), overly long sentences, and structural issues like missing transitions or weak topic sentences."),
        }

        for key in ["logical","ethical","domain","cultural","counterargument","evidence","pedagogy"]:
            agent = devil.get(key,{})
            if not agent: continue
            findings = agent.get("findings",[])
            ico, name, plain_desc = agent_meta[key]
            with st.expander(f"{ico} {name}  -  {agent.get('count',0)} finding(s)"):
                # Plain English role description
                st.markdown(f"""<div class="graph-insight">
                    <b>What this agent does:</b> {plain_desc}
                </div>""", unsafe_allow_html=True)
                st.caption(agent.get("summary",""))
                if not findings:
                    st.success("No issues found by this agent.")
                    continue
                for f in findings[:12]:
                    sev = f.get("severity","low")
                    if f.get("type") == "Strong Evidence": cls = "feedback-strength"
                    elif sev == "high": cls = "feedback-weakness"
                    elif sev in ("medium","low"): cls = "feedback-suggestion"
                    else: cls = "feedback-missing"
                    # Render each devil finding using st.container to avoid broken HTML
                    sev_label = f.get('type','') + ' . ' + f.get('subtype','')
                    note_text = f.get('student_note','')
                    sent_text = f'"{f["sentence"][:100]}{"..." if len(f["sentence"])>100 else ""}"' if f.get("sentence") else ""
                    counter_text = f' Strongest counter: {f["counter"]}' if f.get("counter") else ""

                    border_color = "#fc5c65" if sev=="high" else ("#7c6af7" if sev in ("medium","low") else "#5a6177")
                    if f.get("type") == "Strong Evidence": border_color = "#26de81"

                    st.markdown(
                        f'<div style="border-left:3px solid {border_color};background:rgba(0,0,0,0.15);'
                        f'border-radius:8px;padding:.75rem 1rem;margin:.4rem 0">'
                        f'<div style="font-size:.72rem;font-family:monospace;opacity:.6;margin-bottom:.35rem">{sev_label}</div>'
                        + (f'<div style="font-size:.82rem;color:#9298ae;font-style:italic;margin-bottom:.3rem">{sent_text}</div>' if sent_text else "")
                        + f'<div style="font-size:.87rem">{note_text}</div>'
                        + (f'<div style="font-size:.82rem;color:#4ecdc4;margin-top:.35rem">{counter_text}</div>' if counter_text else "")
                        + '</div>',
                        unsafe_allow_html=True
                    )

# STUDENT DASHBOARD 
elif page_name == "Student Dashboard":
    if not st.session_state.analysed:
        st.info("Please analyse an essay first.")
    else:
        render_student_dashboard(st.session_state.df, st.session_state.student_fb,
                                  st.session_state.verdict, st.session_state.subscores,
                                  st.session_state.best_branch, st.session_state.keywords)

# TEACHER DASHBOARD 
elif page_name == "Teacher Dashboard":
    if not st.session_state.analysed:
        st.info("Please analyse an essay first.")
    else:
        render_teacher_dashboard(st.session_state.df, st.session_state.stats,
                                  st.session_state.verdict, st.session_state.subscores,
                                  st.session_state.teacher_fb, st.session_state.devil_results,
                                  st.session_state.ranked_branches, st.session_state.graph_type,
                                  st.session_state.G)

