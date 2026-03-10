"""
explanation_engine.py
----------------------
This module implements the Graph-of-Thought (GoT) reasoning system
using LangGraph and Google Gemini.

It provides three types of explanations:
1. Aggregation Graph  -> explains how multiple premises support a claim.
2. Refinement Graph   -> explains how a single premise supports a claim.
3. Feedback Generator -> provides overall essay feedback.
"""

from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
from typing import TypedDict, List
import os

# ============================================================
# Initialize Gemini model
# ============================================================
# Make sure GOOGLE_API_KEY is set in environment
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    print("⚠️  Warning: GOOGLE_API_KEY not found in environment variables")

llm = ChatGoogleGenerativeAI(
    model="models/gemini-2.5-flash",   # ✅ updated model name
    temperature=0.2,
    google_api_key=api_key
)



# ============================================================
# State definitions for LangGraph
# ============================================================
class AggregationState(TypedDict):
    claim: str
    premises: List[str]
    summary: str
    connection: str
    refined: str


class RefinementState(TypedDict):
    claim: str
    premise: str
    reasoning: str
    refined: str


# ============================================================
# 1️⃣ Aggregation Graph - combines multiple premises
# ============================================================
def summarize_premises_node(state: AggregationState) -> AggregationState:
    """Summarize all premises briefly."""
    premises = state["premises"]
    joined = "\n- ".join(premises)
    prompt = f"""Summarize the following premises briefly and clearly:
- {joined}

Provide a *very short* 1-2 sentence summary (max 20 words).
"""
    
    response = llm.invoke(prompt)
    content = response.content if hasattr(response, "content") else str(response)
    
    state["summary"] = content
    return state


def connect_to_claim_node(state: AggregationState) -> AggregationState:
    """Explain how premises support the claim."""
    summary = state["summary"]
    claim = state["claim"]
    
    prompt = f"""Explain logically how these premises collectively support the claim.

Claim: {claim}

Premises Summary: {summary}

Explain briefly (max 3 bullet points) how the premises support the claim.
Use plain, clear language.
"""
    
    response = llm.invoke(prompt)
    content = response.content if hasattr(response, "content") else str(response)
    
    state["connection"] = content
    return state


def refine_aggregation_node(state: AggregationState) -> AggregationState:
    """Refine the explanation for clarity."""
    explanation = state["connection"]
    
    prompt = f"""Refine the following reasoning to improve clarity and logical coherence:

{explanation}

Rewrite in 2-3 clear lines. Keep it concise and avoid repetition.
"""
    
    response = llm.invoke(prompt)
    content = response.content if hasattr(response, "content") else str(response)
    
    state["refined"] = content
    return state


def run_aggregation_explanation(claim_text: str, premises_list: List[str]) -> str:
    """
    Aggregates reasoning across multiple premises to explain
    how they collectively support the given claim.
    
    Returns: Final refined explanation (string)
    """
    print("🧠 Running GoT Aggregation Graph...")
    
    # Build the StateGraph
    workflow = StateGraph(AggregationState)
    
    # Add nodes
    workflow.add_node("summarize", summarize_premises_node)
    workflow.add_node("connect", connect_to_claim_node)
    workflow.add_node("refine", refine_aggregation_node)
    
    # Add edges
    workflow.set_entry_point("summarize")
    workflow.add_edge("summarize", "connect")
    workflow.add_edge("connect", "refine")
    workflow.add_edge("refine", END)
    
    # Compile and run
    app = workflow.compile()
    
    result = app.invoke({
        "claim": claim_text,
        "premises": premises_list,
        "summary": "",
        "connection": "",
        "refined": ""
    })
    
    print("✅ Aggregation reasoning complete.")
    return result.get("refined", "No explanation generated.")


# ============================================================
# 2️⃣ Refinement Graph - refines single premise-claim link
# ============================================================
def generate_reasoning_node(state: RefinementState) -> RefinementState:
    """Generate initial reasoning for premise-claim link."""
    premise = state["premise"]
    claim = state["claim"]
    
    prompt = f"""Explain logically how the following premise supports the claim.

Premise: {premise}

Claim: {claim}

Provide a 2-3 line summary, focusing only on the key logical link.
"""
    
    response = llm.invoke(prompt)
    content = response.content if hasattr(response, "content") else str(response)
    
    state["reasoning"] = content
    return state


def improve_reasoning_node(state: RefinementState) -> RefinementState:
    """Refine the reasoning for better clarity."""
    explanation = state["reasoning"]
    
    prompt = f"""Refine this reasoning for clarity and stronger logic:

{explanation}

Keep it short — max 2 sentences. Focus on clarity.
"""
    
    response = llm.invoke(prompt)
    content = response.content if hasattr(response, "content") else str(response)
    
    state["refined"] = content
    return state


def run_refinement_explanation(claim_text: str, premise_text: str) -> str:
    """
    Refines reasoning for a single premise-claim link.
    
    Returns: Final refined explanation (string)
    """
    print("🔍 Running GoT Refinement Graph...")
    
    # Build the StateGraph
    workflow = StateGraph(RefinementState)
    
    # Add nodes
    workflow.add_node("generate", generate_reasoning_node)
    workflow.add_node("refine", improve_reasoning_node)
    
    # Add edges
    workflow.set_entry_point("generate")
    workflow.add_edge("generate", "refine")
    workflow.add_edge("refine", END)
    
    # Compile and run
    app = workflow.compile()
    
    result = app.invoke({
        "claim": claim_text,
        "premise": premise_text,
        "reasoning": "",
        "refined": ""
    })
    
    print("✅ Refinement reasoning complete.")
    return result.get("refined", "No explanation generated.")


# ============================================================
# 3️⃣ Feedback-based explanation
# ============================================================
def run_feedback_explanation(essay_text: str) -> str:
    """
    Generates short, concise, point-wise feedback using Gemini.
    Each bullet appears on a new line in Streamlit.
    """

    print("💬 Running concise feedback generator...")

    prompt = f"""
You are an expert essay evaluator.

Produce VERY concise bullet-point feedback.
RULES:
- Only bullet points
- Each bullet MUST start with "•"
- Each bullet MUST be returned on a NEW LINE
- No paragraphs
- 3–4 bullets per section

Output format:

### ✅ Strengths
• point  
• point  
• point  

### ⚠️ Weaknesses
• point  
• point  
• point  

### 🔧 Actionable Improvements
• point  
• point  
• point  

Essay:
{essay_text}
"""

    response = llm.invoke(prompt)
    content = response.content if hasattr(response, "content") else str(response)

    # --- FIX: Force each bullet to appear on its own line in Streamlit ---
    content = content.replace("•", "\n•")     # new line before every bullet
    content = content.replace("\n•", "\n\n•")  # double newline for markdown rendering

    print("✅ Concise feedback generation complete.")
    return content


