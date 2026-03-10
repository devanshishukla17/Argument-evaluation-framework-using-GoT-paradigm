import networkx as nx


# ==========================================================
# Graph Reasoning State (GRS)
# Stores the evolving thought graph
# ==========================================================

class GraphReasoningState:

    def __init__(self):
        self.thought_graph = nx.DiGraph()

    def add_thought(self, node_id, text, score=0):
        self.thought_graph.add_node(node_id, text=text, score=score)

    def add_edge(self, src, dst):
        self.thought_graph.add_edge(src, dst)

    def get_thoughts(self):
        return list(self.thought_graph.nodes(data=True))


# ==========================================================
# Extract Argument Components
# ==========================================================

def extract_components(argument_graph):

    claims = []
    evidences = []
    counterclaims = []
    rebuttals = []

    for node, data in argument_graph.nodes(data=True):

        label = data.get("label")

        if label == "Claim":
            claims.append(data.get("text"))

        elif label == "Evidence":
            evidences.append(data.get("text"))

        elif label == "Counterclaim":
            counterclaims.append(data.get("text"))

        elif label == "Rebuttal":
            rebuttals.append(data.get("text"))

    return claims, evidences, counterclaims, rebuttals


# ==========================================================
# Thought Generation
# ==========================================================

def generate_thoughts(claim, evidences):

    thoughts = []

    for ev in evidences:

        thought = f"""
Evidence: "{ev}"

This evidence contributes to supporting the claim:
"{claim}"
"""

        thoughts.append(thought.strip())

    return thoughts


# ==========================================================
# Thought Expansion
# ==========================================================

def expand_thought(thought, claim):

    expansion = f"""
{thought}

Therefore this reasoning strengthens the argument that:
"{claim}"
"""

    return expansion.strip()


# ==========================================================
# Thought Scoring
# ==========================================================

def score_thought(thought):

    score = 0.5

    length = len(thought.split())

    if length > 20:
        score += 0.2

    if "evidence" in thought.lower():
        score += 0.2

    if "therefore" in thought.lower():
        score += 0.1

    return min(score, 1.0)


# ==========================================================
# Controller (Main GoT Pipeline)
# ==========================================================

def run_got_reasoning(argument_graph):

    claims, evidences, counterclaims, rebuttals = extract_components(argument_graph)

    if not claims:
        return {"error": "No claims detected"}

    claim = claims[0]

    if not evidences:
        evidences = ["Implicit reasoning from essay context"]

    grs = GraphReasoningState()

    # ------------------------------------------------------
    # Stage 1: Generate initial thoughts
    # ------------------------------------------------------

    thoughts = generate_thoughts(claim, evidences)

    previous_node = None

    for i, thought in enumerate(thoughts):

        score = score_thought(thought)

        node_id = f"T{i}"

        grs.add_thought(node_id, thought, score)

        if previous_node:
            grs.add_edge(previous_node, node_id)

        previous_node = node_id

    # ------------------------------------------------------
    # Stage 2: Expand reasoning graph
    # ------------------------------------------------------

    expanded_nodes = []

    for node_id, data in grs.get_thoughts():

        expanded = expand_thought(data["text"], claim)

        score = score_thought(expanded)

        new_id = f"{node_id}_E"

        expanded_nodes.append((node_id, new_id, expanded, score))

    for src, nid, text, score in expanded_nodes:

        grs.add_thought(nid, text, score)
        grs.add_edge(src, nid)

    # ------------------------------------------------------
    # Select best thought
    # ------------------------------------------------------

    thoughts = grs.get_thoughts()

    best = max(thoughts, key=lambda x: x[1]["score"])

    return {
        "thoughts": thoughts,
        "best_thought": best[1]["text"],
        "best_score": best[1]["score"]
    }