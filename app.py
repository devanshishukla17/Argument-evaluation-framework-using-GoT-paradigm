"""
app.py
------
Streamlit app for the GoT Essay Analyzer 🧠✍️

Features:
1. Upload or paste essay text
2. Classify discourse components (Claim, Evidence, etc.)
3. Visualize argument structure with interactive graph
4. Run Graph-of-Thought reasoning (Aggregation + Refinement)
5. Generate AI feedback via Gemini
6. Feedback loop with 👍/👎 rating buttons

Requirements:
  - stage1_model/ directory (trained model)
  - GOOGLE_API_KEY set in environment
"""

from importlib.resources import path

import streamlit as st
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import json
from datetime import datetime
from pipeline_utils import load_discourse_model, predict_discourse_segments
from explanation_engine import (
    run_aggregation_explanation,
    run_refinement_explanation,
    run_feedback_explanation
)
from got_engine import run_got_reasoning

# ============================================================
# App Config
# ============================================================
st.set_page_config(
    page_title="GoT Essay Analyzer",
    page_icon="🧠",
    layout="wide"
)

# Initialize session state for feedback storage
if "feedback_log" not in st.session_state:
    st.session_state.feedback_log = []
if "segments_df" not in st.session_state:
    st.session_state.segments_df = None
if "essay_text" not in st.session_state:
    st.session_state.essay_text = ""
if "analysis_complete" not in st.session_state:
    st.session_state.analysis_complete = False

# ============================================================
# Header
# ============================================================
st.title("🧠 GoT Essay Analyzer")
st.markdown(
    """
    **Graph-of-Thought (GoT) Essay Reasoning System**

    Analyze essays using a hybrid pipeline of:
    - Transformer-based discourse classification
    - Graph-of-Thought reasoning with Google Gemini
    - Interactive argument structure visualization
    - Automatic feedback and quality scoring
    """
)

# ============================================================
# Sidebar for Input
# ============================================================
st.sidebar.header("Input Essay Text")
essay_text = st.sidebar.text_area(
    "Paste your essay here 👇",
    height=300,
    placeholder="Type or paste your essay...",
    value=st.session_state.essay_text
)

analyze_button = st.sidebar.button("Analyze Essay", type="primary")

# Clear analysis button
if st.sidebar.button("Clear Analysis"):
    st.session_state.analysis_complete = False
    st.session_state.segments_df = None
    st.session_state.essay_text = ""
    st.rerun()

# ============================================================
# Load model and tokenizer
# ============================================================
@st.cache_resource
def load_models():
    """Load the discourse classification model."""
    try:
        model, tokenizer = load_discourse_model()
        return model, tokenizer
    except Exception as e:
        st.error(f" Error loading model: {str(e)}")
        st.info("Make sure the 'stage1_model' folder is in the same directory as app.py")
        return None, None

model, tokenizer = load_models()

# ============================================================
# Helper: Build argument graph with proper relationships
# ============================================================
def build_argument_graph(segments_df):
    """
    Build a NetworkX graph representing argument structure.
    
    Logic:
    - Claims are central nodes
    - Evidence supports the nearest preceding Claim
    - Position/Lead are introductory
    - Counterclaim/Rebuttal are debate elements
    - Concluding Statement wraps up
    """
    G = nx.DiGraph()
    
    # Track recent claim for evidence linking
    current_claim = None
    
    for idx, row in segments_df.iterrows():
        node_id = f"{idx}"
        discourse_type = row['predicted_discourse_type']
        text_snippet = row['text'][:50] + "..." if len(row['text']) > 50 else row['text']
        
        # Add node with attributes
        G.add_node(
            node_id,
            label=discourse_type,
            text=row['text'],
            confidence=row['confidence'],
            snippet=text_snippet
        )

            # ======== Improved linking logic for richer graphs ========
    last_claim = None
    last_counterclaim = None
    last_position = None
    last_lead = None
    
    for idx, row in segments_df.iterrows():
        node_id = f"{idx}"
        discourse_type = row["predicted_discourse_type"]
        

        # --- LEAD ---
        if discourse_type == "Lead":
            if last_lead:
                G.add_edge(last_lead, node_id, relation="flows_to")
            last_lead = node_id

        # --- POSITION (Thesis) ---
        elif discourse_type == "Position":
            if last_lead:
                G.add_edge(last_lead, node_id, relation="introduces")
            last_position = node_id

        # --- CLAIM ---
        elif discourse_type == "Claim":
            # Link from position → claim
            if last_position:
                G.add_edge(last_position, node_id, relation="supports")

            # Link from previous claim → this claim (flow)
            if last_claim:
                G.add_edge(last_claim, node_id, relation="next_claim")

            last_claim = node_id

        # --- EVIDENCE ---
        elif discourse_type == "Evidence":
            # Attach evidence to nearest *claim*
            if last_claim:
                G.add_edge(node_id, last_claim, relation="supports")

            # Also attach to Position for stronger graph
            if last_position:
                G.add_edge(node_id, last_position, relation="reinforces")

        # --- COUNTERCLAIM ---
        elif discourse_type == "Counterclaim":
            if last_claim:
                G.add_edge(node_id, last_claim, relation="opposes")
            last_counterclaim = node_id

        # --- REBUTTAL ---
        elif discourse_type == "Rebuttal":
            if last_counterclaim:
                G.add_edge(node_id, last_counterclaim, relation="rebuts")

        # --- CONCLUSION ---
        elif discourse_type == "Concluding Statement":
            if last_claim:
                G.add_edge(last_claim, node_id, relation="concludes")

        
        # Add edges based on discourse type
        if discourse_type == 'Claim':
            current_claim = node_id
            # Link to Position if exists
            position_nodes = [n for n in G.nodes() if G.nodes[n]['label'] == 'Position']
            if position_nodes:
                G.add_edge(position_nodes[-1], node_id, relation="supports")
        
        elif discourse_type == 'Evidence':
            if current_claim:
                G.add_edge(node_id, current_claim, relation="supports")
        
        elif discourse_type == 'Counterclaim':
            if current_claim:
                G.add_edge(node_id, current_claim, relation="opposes")
        
        elif discourse_type == 'Rebuttal':
            # Link to most recent Counterclaim
            counterclaim_nodes = [n for n in G.nodes() if G.nodes[n]['label'] == 'Counterclaim']
            if counterclaim_nodes:
                G.add_edge(node_id, counterclaim_nodes[-1], relation="refutes")
    
    return G


# ============================================================
# Helper: Visualize argument graph
# ============================================================
def visualize_argument_graph(segments_df):
    """Create interactive visualization of argument structure."""
    st.subheader("Argument Structure Graph")
    
    G = build_argument_graph(segments_df)
    
    if len(G.nodes()) == 0:
        st.warning("No argument components detected.")
        return None
    
    # --- START NEW LOGIC: Identify Unsupported Claims ---
    unsupported_claims = []
    
    for node_id, data in G.nodes(data=True):
        if data.get('label') == 'Claim':
            # A Claim is supported if it has an incoming edge with relation="supports"
            is_supported = False
            # Iterate through incoming edges (u, v) where v is node_id
            for u, v, d in G.in_edges(node_id, data=True):
                if d.get('relation') == 'supports':
                    is_supported = True
                    break
            
            if not is_supported:
                unsupported_claims.append(node_id)
    # --- END NEW LOGIC ---

    # Color mapping for discourse types
    color_map = {
        'Lead': '#E8F4F8',
        'Position': '#B4E7F8',
        'Claim': '#FFD700',
        'Evidence': '#90EE90',
        'Counterclaim': '#FFB6C1',
        'Rebuttal': '#FFA07A',
        'Concluding Statement': '#D8BFD8',
        'Unsupported Claim': '#FF4500' # Bright red/orange for warning
    }
    
    # Create visualization
    fig, ax = plt.subplots(figsize=(14, 10))
    
    # Layout
    pos = nx.spring_layout(G, k=2, iterations=50, seed=42)
    
    # Draw nodes by type, ensuring unsupported claims are drawn in the warning color
    for discourse_type, color in color_map.items():
        if discourse_type == 'Unsupported Claim':
            node_list = unsupported_claims
        elif discourse_type == 'Claim':
            # Draw only the *supported* claims (standard color)
            node_list = [
                n for n in G.nodes() 
                if G.nodes[n]['label'] == discourse_type and n not in unsupported_claims
            ]
        else:
            # Draw all other discourse types normally
            node_list = [n for n in G.nodes() if G.nodes[n]['label'] == discourse_type]

        if node_list:
            nx.draw_networkx_nodes(
                G, pos, nodelist=node_list,
                node_color=color,
                node_size=3000,
                alpha=0.9,
                ax=ax
            )
    
    # Draw edges with different styles (This section remains unchanged)
    support_edges = [(u, v) for u, v, d in G.edges(data=True) if d.get('relation') == 'supports']
    oppose_edges = [(u, v) for u, v, d in G.edges(data=True) if d.get('relation') == 'opposes']
    refute_edges = [(u, v) for u, v, d in G.edges(data=True) if d.get('relation') == 'refutes']
    
    # General flow edges (all others that aren't the specific support/oppose/refute)
    # Filter out edges already drawn (support/oppose/refute)
    specific_relations = ['supports', 'opposes', 'rebuts']
    other_edges = [
        (u, v) for u, v, d in G.edges(data=True) 
        if d.get('relation') not in specific_relations
    ]

    nx.draw_networkx_edges(G, pos, edgelist=support_edges, edge_color='green', 
                        arrows=True, arrowsize=20, width=2, ax=ax)
    nx.draw_networkx_edges(G, pos, edgelist=oppose_edges, edge_color='red', 
                        arrows=True, arrowsize=20, width=2, style='dashed', ax=ax)
    nx.draw_networkx_edges(G, pos, edgelist=refute_edges, edge_color='orange', 
                        arrows=True, arrowsize=20, width=2, style='dotted', ax=ax)
    nx.draw_networkx_edges(G, pos, edgelist=other_edges, edge_color='#444444', 
                        arrows=True, arrowsize=10, width=1, style='dotted', alpha=0.5, ax=ax)

    # Labels
    labels = {n: f"{G.nodes[n]['label']}\n{G.nodes[n]['snippet']}" for n in G.nodes()}
    nx.draw_networkx_labels(G, pos, labels, font_size=8, font_weight='bold', ax=ax)
    
    ax.axis('off')
    plt.tight_layout()
    st.pyplot(fig)
    
    # --- START NEW LEGEND ---
    st.markdown("""
    **Legend:**
    -  **Unsupported Claim**: A claim with no evidence pointing to it.
    - Green arrows: Support relationships
    - Red dashed: Opposition relationships
    - Orange dotted: Refutation relationships
    - Gray dotted: General flow (connecting consecutive argument steps)
    """)
    # --- END NEW LEGEND ---
    
    return G

# ============================================================
# Helper: Save feedback
# ============================================================
def save_feedback(explanation_type, content, rating):
    """Save user feedback to session state."""
    feedback_entry = {
        "timestamp": datetime.now().isoformat(),
        "type": explanation_type,
        "content": content[:100] + "...",
        "rating": rating
    }
    st.session_state.feedback_log.append(feedback_entry)


# ============================================================
# Helper: Display explanation with feedback buttons
# ============================================================
def display_explanation_with_feedback(title, content, explanation_type):
    """Display an explanation with 👍/👎 feedback buttons."""
    st.markdown(f"**{title}**")
    st.markdown(content)
    
    col1, col2, col3 = st.columns([1, 1, 8])
    with col1:
        if st.button("👍", key=f"like_{explanation_type}"):
            save_feedback(explanation_type, content, "positive")
            st.success("Thanks for your feedback!")
    with col2:
        if st.button("👎", key=f"dislike_{explanation_type}"):
            save_feedback(explanation_type, content, "negative")
            st.info("Feedback recorded. We'll improve!")


# ============================================================
# MAIN PIPELINE EXECUTION
# ============================================================
if model is None or tokenizer is None:
    st.error("Cannot proceed without model. Please check model loading errors above.")
    st.stop()

if analyze_button and essay_text.strip():
    st.session_state.essay_text = essay_text
    st.session_state.analysis_complete = True
    
    # ========================================================
    # Step 1: Discourse Analysis
    # ========================================================
    st.subheader("Step 1: Discourse Analysis")
    with st.spinner("Running transformer model..."):
        segments_df = predict_discourse_segments(essay_text, model, tokenizer)
        st.session_state.segments_df = segments_df
        st.success("Discourse analysis complete!")

    st.dataframe(segments_df, use_container_width=True)
    
    # Identify unsupported claims
    claims = segments_df[segments_df['predicted_discourse_type'] == 'Claim']
    if not claims.empty:
        st.info(f"Found {len(claims)} claim(s) in your essay")

    # ========================================================
    # Step 2: Argument Graph Visualization
    # ========================================================
    G = visualize_argument_graph(segments_df)
    
    def visualize_reasoning_path(G, path):
        subgraph = G.subgraph(path)
        pos = nx.spring_layout(subgraph, k=1.6, seed=42)
        fig, ax = plt.subplots(figsize=(14,10))
        
        nx.draw_networkx_nodes(
        subgraph,
        pos,
        node_size=2600,
        node_color="#B4E7F8",
        ax=ax
        )
        
        nx.draw_networkx_edges(
        subgraph,
        pos,
        arrows=True,
        arrowsize=20,
        width=2,
        ax=ax
        )
        
        labels = {
            n: f"{subgraph.nodes[n]['label']}{n}"
            for n in subgraph.nodes()
            }
        
        nx.draw_networkx_labels(
        subgraph,
        pos,
        labels,
        font_size=11,
        font_weight="bold",
        ax=ax
        )

        ax.axis("off")

        return fig

    # ========================================================
    # Step 3: Graph-of-Thought Expansion (NEW)
    # ========================================================
    st.subheader("Graph-of-Thought Reasoning")
    got_results = run_got_reasoning(G)
    if "error" in got_results:
        st.warning(got_results["error"])

    else:

        st.markdown("### Reasoning Paths")

        thoughts = got_results["thoughts"]

        for i, node in enumerate(thoughts):

            data = node[1]

            score = data["score"]
            prob = data["probability"]
            path = data["path"]

            st.markdown(f"#### Path {i+1}")

            path_labels = [G.nodes[n]["label"] for n in path]

            st.code(" → ".join(path_labels))

            fig = visualize_reasoning_path(G, path)

            st.pyplot(fig)

            col1, col2 = st.columns(2)

            col1.metric("Score", f"{score:.2f}")
            col2.metric("Probability", f"{prob:.2f}")

            st.markdown("---")

        st.markdown("### ⭐ Best Reasoning Path")

        best_nodes = got_results["best_path"]

        best_labels = [G.nodes[n]["label"] for n in best_nodes]

        st.code(" → ".join(best_labels))

        fig = visualize_reasoning_path(G, best_nodes)

        st.pyplot(fig)
        
    # ========================================================
    # Visual Reasoning Graphs (Aggregation + Refinement)
    # ========================================================
    st.markdown("### Visual GoT Reasoning Graphs")

    claims_list = segments_df[segments_df['predicted_discourse_type'] == 'Claim']['text'].tolist()
    evidences_list = segments_df[segments_df['predicted_discourse_type'] == 'Evidence']['text'].tolist()
    # =============================
    # Aggregation Graph (Option A)
    # =============================
    
    if len(evidences_list) >= 2:
        st.markdown("#### Aggregation Graph (Multiple Evidence → Claim)")

        G_agg = nx.DiGraph()

        # Add Evidence nodes
        for i, ev in enumerate(evidences_list[:3]):
            G_agg.add_node(
                f"Evidence {i+1}",
                label=f"Evidence {i+1}",
                text=ev
            )

        # Aggregated reasoning node
        G_agg.add_node(
            "Aggregated Support",
            label="Aggregated Support",
            text="Combined reasoning from multiple premises"
        )

        # Claim node
        G_agg.add_node("Claim", label="Claim", text=claims_list[0])

        # Edges: Evidence → Aggregated Support → Claim
        for i in range(min(3, len(evidences_list))):
            G_agg.add_edge(f"Evidence {i+1}", "Aggregated Support")

        G_agg.add_edge("Aggregated Support", "Claim")

        figA, axA = plt.subplots(figsize=(12, 6))
        posA = nx.spring_layout(G_agg, seed=42, k=1.2)

        # Draw nodes with text
        for node in G_agg.nodes():
            nx.draw_networkx_nodes(
                G_agg, posA, nodelist=[node],
                node_color="#AEE6FF" if node.startswith("Evidence") else "#FFD700",
                node_size=3000, ax=axA
            )

        nx.draw_networkx_edges(
            G_agg, posA, arrows=True, arrowsize=20, width=2, ax=axA
        )

        agg_labels = {
            node: f"{G_agg.nodes[node]['label']}\n{G_agg.nodes[node]['text'][:60]}..."
            for node in G_agg.nodes()
        }
        nx.draw_networkx_labels(G_agg, posA, agg_labels, font_size=9, ax=axA)
        axA.axis("off")
        st.pyplot(figA)

    # ==========================
    # Refinement Graph (Option A)
    # ==========================
    # if len(evidences_list) > 0:
    #     st.markdown("#### Refinement Graph (Premise → Logical Path → Claim)")

    #     G_ref = nx.DiGraph()

    #     premise = evidences_list[0]

    #     # Nodes
    #     G_ref.add_node("Premise", label="Premise", text=premise)
    #     G_ref.add_node("Initial Link", label="Initial Link", text="Basic logical relation")
    #     G_ref.add_node(
    #         "Refined Logic",
    #         label="Refined Logic",
    #         text="Improved explanation"
    #     )
    #     G_ref.add_node("Claim", label="Claim", text=claims_list[0])

    #     # Edges
    #     G_ref.add_edge("Premise", "Initial Link")
    #     G_ref.add_edge("Initial Link", "Refined Logic")
    #     G_ref.add_edge("Refined Logic", "Claim")

    #     figR, axR = plt.subplots(figsize=(12, 6))
    #     posR = nx.spring_layout(G_ref, seed=10, k=1.3)

    #     # Draw nodes
    #     for node in G_ref.nodes():
    #         nx.draw_networkx_nodes(
    #             G_ref, posR, nodelist=[node],
    #             node_color="#E6CCFF" if "Link" in node or "Logic" in node else "#B4F4B4",
    #             node_size=3000, ax=axR
    #         )

    #     nx.draw_networkx_edges(G_ref, posR, arrows=True, arrowsize=22, width=2, ax=axR)

    #     ref_labels = {
    #         node: f"{G_ref.nodes[node]['label']}\n{G_ref.nodes[node]['text'][:60]}..."
    #         for node in G_ref.nodes()
    #     }
    #     nx.draw_networkx_labels(G_ref, posR, ref_labels, font_size=9, ax=axR)

    #     axR.axis("off")
    #     st.pyplot(figR)


    # if len(claims_list) == 0:
    #     st.warning("No claims detected – please provide argumentative text.")
    # else:
    #     # Aggregation reasoning
    #     if len(evidences_list) >= 2:
    #         st.markdown("### Aggregation Explanation")
    #         with st.spinner("Analyzing how multiple evidence points support your claim..."):
    #             agg_output = run_aggregation_explanation(
    #                 claims_list[0], 
    #                 evidences_list[:3]
    #             )
    #         display_explanation_with_feedback(
    #             "How Multiple Premises Support Your Claim:",
    #             agg_output,
    #             "aggregation"
    #         )
        
    #     # Refinement reasoning
    #     if len(evidences_list) > 0:
    #         st.markdown("### Refinement Explanation")
    #         with st.spinner("Refining the logical link between premise and claim..."):
    #             ref_output = run_refinement_explanation(
    #                 claims_list[0], 
    #                 evidences_list[0]
    #             )
    #         display_explanation_with_feedback(
    #             "Logical Link Between Premise and Claim:",
    #             ref_output,
    #             "refinement"
    #         )

    # # ========================================================
    # # Step 5: Overall Feedback
    # # ========================================================
    # st.subheader("Step 3: Overall Feedback")
    # with st.spinner("Generating comprehensive feedback via Gemini..."):
    #     feedback = run_feedback_explanation(essay_text)
    
    # display_explanation_with_feedback(
    #     "Comprehensive Essay Feedback:",
    #     feedback,
    #     "overall_feedback"
    # )

    # st.success("Analysis complete!")

elif analyze_button:
    st.warning("Please enter some essay text first!")

# ============================================================
# Display previous analysis if exists
# ============================================================
if st.session_state.analysis_complete and st.session_state.segments_df is not None and not analyze_button:
    st.info("Showing previous analysis. Click 'Analyze Essay' to run a new analysis.")
    st.dataframe(st.session_state.segments_df, use_container_width=True)

# ============================================================
# Sidebar: Feedback Log
# ============================================================
if len(st.session_state.feedback_log) > 0:
    st.sidebar.markdown("---")
    st.sidebar.subheader("Feedback Log")
    st.sidebar.markdown(f"Total feedback entries: {len(st.session_state.feedback_log)}")
    
    if st.sidebar.button("Export Feedback"):
        feedback_json = json.dumps(st.session_state.feedback_log, indent=2)
        st.sidebar.download_button(
            label="Download Feedback JSON",
            data=feedback_json,
            file_name="feedback_log.json",
            mime="application/json"
        )

# ============================================================
# Footer
# ============================================================
st.markdown("---")
st.markdown(
    "Developed using **Transformers** + **LangGraph** + **Gemini**"
)