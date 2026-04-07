# 🧠 EssayEvalAI — AI-Powered Essay Evaluation Framework

A production-grade, modular essay analysis system using **Graph-of-Thought (GoT)** reasoning, **Devil's Advocate** critique agents, dynamic argument graphs, and a polished multi-page Streamlit interface.

---

## 🚀 Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the app
streamlit run app.py
```

Open your browser at `http://localhost:8501`

---

## 📋 Features

### 1. Discourse Classification
Classifies each sentence into 18 categories:
- Lead, Position, Claim, Evidence, Counterclaim, Rebuttal
- Assumption, Premise, Supporting Fact, Example
- Cause-Effect Relation, Strong Evidence, Weak Evidence
- Missing Evidence, Unsupported Claim, Bias Indicator, Logical Fallacy
- Concluding Statement

### 2. Argument Graph
- Dynamically selects graph type based on essay structure
- Standard, Debate, Unsupported Claim, Hidden Assumption, and Contradiction graphs
- Interactive PyVis and Plotly network charts

### 3. Graph-of-Thought (GoT)
- Generates 4 reasoning branches: Causal, Adversarial, Assumption, Evidence Quality
- Scores each branch on: Confidence, Completeness, Diversity
- Merges into a synthesised best path
- Produces a final verdict

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

### 5. Scoring (0–10)
- Overall Score
- Evidence Coverage
- Logical Consistency
- Counterargument Quality
- Bias Score
- Readability
- Grammar

### 6. Feedback
- **Student view**: Annotated essay, colour-coded by category, sentence-level feedback
- **Teacher view**: Full analysis, all GoT branches, devil agent findings
- Filterable by: Strengths, Weaknesses, Missing Evidence, Suggestions

### 7. Export
- **CSV**: Classified discourse table
- **JSON**: Full analysis dump
- **PDF**: Professional report (uses fpdf2 → reportlab → plain text fallback)

---

## 📁 File Structure

```
essay_evaluator/
│
├── app.py                    # Main entry point, routing, session state
├── dashboard.py              # Overview metrics dashboard
├── student_dashboard.py      # Student-friendly feedback view
├── teacher_dashboard.py      # Teacher-grade complete analysis
│
├── discourse_classifier.py   # Sentence classification (18 categories)
├── graph_builder.py          # Argument & GoT graph construction
├── got_engine.py             # Graph-of-Thought reasoning engine
├── devil_agents.py           # 7 Devil's Advocate critique agents
├── explanation_engine.py     # Human-readable feedback generation
├── visualization.py          # Plotly + PyVis interactive charts
├── export_utils.py           # CSV / JSON / PDF export
├── styles.py                 # Dark/light theme CSS
│
├── requirements.txt
└── README.md
```

---

## 🧭 Navigation

| Page | Description |
|---|---|
| 🏠 Home Dashboard | Overview metrics, best reasoning path, score breakdown |
| 🗺 Full Argument Graph | Interactive discourse relationship graph |
| 🧠 GoT Explorer | Branch timeline, radar, synthesised path |
| 🔀 Aggregation & Refinement | Statistics, heatmaps, evidence analysis |
| 👹 Devil's Advocate Review | All 7 agents, issue counts, detailed findings |
| 🎓 Student Dashboard | Annotated essay, filterable feedback |
| 👩‍🏫 Teacher Dashboard | Complete evaluation with all metrics |
| 📤 Export Report | Download CSV, JSON, or PDF |

---

## ⚙️ Configuration

- **Dark / Light Mode**: Toggle in the sidebar
- **Essay Input**: Type, paste, or upload `.txt` / `.pdf`
- **Sample Essay**: Click "Load Sample Essay" to demo with a school uniforms essay

---

## 📦 Dependencies

Key packages:
- `streamlit` — UI framework
- `networkx` — Graph construction
- `plotly` — Interactive charts
- `pyvis` — Network visualisation
- `pandas` / `numpy` — Data processing
- `fpdf2` / `reportlab` — PDF generation
- `PyPDF2` — PDF text extraction
- `textstat` — Readability scoring
- `nltk` / `spacy` — NLP utilities

---

## 🏗 Architecture

```
Essay Text
    │
    ▼
discourse_classifier.py  ──→  DataFrame (sentence, category, confidence)
    │
    ├──→ graph_builder.py     ──→  NetworkX DiGraph
    ├──→ got_engine.py        ──→  Reasoning branches + verdict
    ├──→ devil_agents.py      ──→  7-agent critique results
    └──→ explanation_engine.py──→  Student & teacher feedback
              │
              ▼
    visualization.py   ──→  Plotly / PyVis charts
    styles.py          ──→  Dark/light CSS
    export_utils.py    ──→  CSV / JSON / PDF
              │
              ▼
    app.py (Streamlit) ──→  Multi-page UI
```

---

## 📄 License

MIT License. Free to use, modify, and distribute.
