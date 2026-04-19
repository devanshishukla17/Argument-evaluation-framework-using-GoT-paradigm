# 🧠 EssayEvalAI — AI-Powered Essay Evaluation with REAL Graph-of-Thought

A production-grade essay analysis system with a **genuine Graph-of-Thought (GoT)** reasoning
pipeline (Besta et al., 2023), Devil's Advocate critique agents, dynamic argument graphs,
and a polished multi-page Streamlit interface.

---

## 🚀 Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set your Anthropic API key
export ANTHROPIC_API_KEY=sk-ant-...

# 3. Run
streamlit run app.py
```

Open your browser at `http://localhost:8501`

---

## 🧠 Real Graph-of-Thought — How It Works

The old fake GoT used hardcoded branch templates with hardcoded confidence values.
The new GoT executes **4 actual LLM calls** that implement the true GoT paradigm:

```
Essay + Discourse Data
        │
        ▼
┌─────────────────────────────────────────────────────────┐
│  STEP 1: GENERATE                                       │
│  Claude independently generates 4 thought-node chains:  │
│  • Causal Chain (claim → evidence → conclusion flow)    │
│  • Adversarial  (counterclaim/rebuttal dialectic)       │
│  • Assumption Audit (hidden premises)                   │
│  • Evidence Quality (strong vs weak vs missing)         │
│  Each branch has 3-6 discrete thought nodes.            │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│  STEP 2: SCORE                                          │
│  Claude scores every thought node independently:        │
│  • logical_validity  (0.0 – 1.0)                       │
│  • evidence_support  (0.0 – 1.0)                       │
│  • completeness      (0.0 – 1.0)                       │
│  Composite = 0.4×validity + 0.4×evidence + 0.2×compl.  │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│  STEP 3: AGGREGATE (the real GoT step)                  │
│  Claude reasons OVER the whole scored graph:            │
│  • Identifies cross-branch reinforcing signals          │
│  • Identifies cross-branch contradictions               │
│  • Derives graph-level verdict (not per-branch)         │
│  • Selects strongest reasoning path across branches     │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│  STEP 4: REFINE                                         │
│  Claude produces final Toulmin scoring using:           │
│  • The aggregated graph-level insights                  │
│  • Top-scoring nodes across all branches                │
│  • Discourse statistics                                 │
│  Outputs: T1-T6 trait scores, verdict, strengths,      │
│  weaknesses, improvements, GoT synthesis note           │
└─────────────────────────────────────────────────────────┘
```

**Why this is genuinely different from old fake GoT:**
- Old: deterministic Python filtering into hardcoded templates; confidence = hardcoded floats
- New: LLM generates novel thought nodes; LLM scores them; LLM reasons OVER the graph structure;
  LLM synthesises across branches before scoring — true graph-structured reasoning

---

## 📋 Features

### 1. Real Graph-of-Thought Pipeline
- 4 LLM calls: Generate → Score → Aggregate → Refine
- Cross-branch convergence and contradiction detection
- Graph-level verdict (emergent from graph structure, not per-branch)
- Strongest reasoning path selected by the LLM itself

### 2. Discourse Classification
- 18 categories: Lead, Position, Claim, Evidence, Counterclaim, Rebuttal,
  Assumption, Premise, Supporting Fact, Example, Cause-Effect Relation,
  Strong Evidence, Weak Evidence, Missing Evidence, Unsupported Claim,
  Bias Indicator, Logical Fallacy, Concluding Statement

### 3. Argument Graph
- Dynamically selects graph type based on essay structure
- Standard, Debate, Unsupported Claim, Hidden Assumption, Contradiction graphs
- Interactive PyVis and Plotly network charts

### 4. Devil's Advocate (7 Agents)
| Agent | Focus |
|---|---|
| ⚖️ Logical Devil | Fallacies, contradictions, unsupported claims |
| 🧭 Ethical Devil | Discrimination, harmful framing, fairness |
| 🔬 Domain Devil | Domain-specific factual gaps |
| 🌍 Cultural Devil | Bias, overgeneralisation, cultural narrowness |
| ⚔️ Counterargument Devil | Strongest opposing arguments |
| 🔍 Evidence Devil | Weak vs strong evidence audit |
| 📚 Pedagogy Devil | Clarity, structure, writing quality |

### 5. Toulmin Scoring (0–10)
- T1 Claim Clarity, T2 Evidence Quality, T3 Warrant/Reasoning
- T4 Counterargument, T5 Rebuttal Quality, T6 Structural Cohesion
- Raw 0-16 → normalised 0-10
- **Now scored by the LLM using GoT graph insights**, not just rule-based

### 6. Feedback Views
- **Student view**: Annotated essay, colour-coded, sentence-level feedback
- **Teacher view**: Full analysis, all GoT branches, devil agent findings

---

## 📁 File Structure

```
essay_evaluator/
├── app.py                    # Main entry point — wires GoT pipeline into UI
├── got_engine.py             # ★ REAL GoT: 4-step LLM pipeline
├── dashboard.py              # Overview metrics dashboard
├── student_dashboard.py      # Student feedback view
├── teacher_dashboard.py      # Teacher complete analysis
├── discourse_classifier.py   # Sentence classification (18 categories)
├── graph_builder.py          # Argument & GoT graph construction (NetworkX)
├── devil_agents.py           # 7 Devil's Advocate agents
├── explanation_engine.py     # Human-readable feedback generation
├── visualization.py          # Plotly + PyVis interactive charts
├── styles.py                 # Dark/light theme CSS
├── requirements.txt
└── README.md
```

---

## ⚙️ Configuration

- **API Key**: Set `ANTHROPIC_API_KEY` environment variable
- **Model**: `claude-opus-4-20250514` (configurable in `got_engine.py` → `_MODEL`)
- **Fallback**: If API is unavailable, local Toulmin scoring activates automatically
- **Dark / Light Mode**: Toggle in sidebar

---

## 📦 Key Dependencies

- `streamlit` — UI framework
- `anthropic` — Claude API client (real GoT engine)
- `networkx` — Graph construction
- `plotly` / `pyvis` — Interactive charts
- `pandas` / `numpy` — Data processing

---

## 🏗 Architecture

```
Essay Text
    │
    ▼
discourse_classifier.py  ──→  DataFrame (sentence, category, confidence)
    │
    ├──→ graph_builder.py       ──→  NetworkX DiGraph
    ├──→ got_engine.py          ──→  4-step GoT pipeline (Claude API)
    │       ├── Generate nodes  (LLM call 1)
    │       ├── Score nodes     (LLM call 2)
    │       ├── Aggregate graph (LLM call 3)
    │       └── Refine verdict  (LLM call 4)
    ├──→ devil_agents.py        ──→  7-agent critique results
    └──→ explanation_engine.py  ──→  Student & teacher feedback
              │
              ▼
    visualization.py    ──→  Plotly / PyVis charts
    styles.py           ──→  Dark/light CSS
              │
              ▼
    app.py (Streamlit)  ──→  Multi-page UI
```

---

## 📄 License

MIT License. Free to use, modify, and distribute.
