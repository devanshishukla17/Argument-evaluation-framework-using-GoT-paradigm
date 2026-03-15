import networkx as nx
import math
from difflib import SequenceMatcher


def text_similarity(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def softmax(scores):

    exp_scores = [math.exp(s) for s in scores]
    total = sum(exp_scores)

    return [s / total for s in exp_scores]


def get_claim_node(G):

    for node, data in G.nodes(data=True):
        if data.get("label") == "Claim":
            return node, data.get("text")

    return None, None


def extract_reasoning_paths(G, claim_node):

    paths = []

    for node in G.nodes():

        if node == claim_node:
            continue

        try:
            path = nx.shortest_path(G, source=node, target=claim_node)

            if len(path) >= 2:
                paths.append(path)

        except:
            pass

    return paths


def path_to_reasoning(G, path):

    texts = []

    for node in path:

        node_data = G.nodes[node]
        label = node_data.get("label")
        text = node_data.get("text")

        texts.append(f"{label}: {text}")

    reasoning = "\n\n".join(texts)

    return reasoning


def score_path(reasoning, claim, other_paths):

    relevance = text_similarity(reasoning, claim)

    length = len(reasoning.split())

    completeness = min(length / 40, 1)

    diversity_scores = [
        text_similarity(reasoning, p)
        for p in other_paths
    ]

    if diversity_scores:
        diversity = 1 - max(diversity_scores)
    else:
        diversity = 1

    score = (
        0.5 * relevance +
        0.3 * completeness +
        0.2 * diversity
    )

    return score


def run_got_reasoning(G):

    claim_node, claim_text = get_claim_node(G)

    if claim_node is None:
        return {"error": "No claim detected in argument graph"}

    paths = extract_reasoning_paths(G, claim_node)

    if not paths:
        return {"error": "No reasoning paths found"}

    reasoning_paths = []

    previous = []

    for p in paths:

        reasoning = path_to_reasoning(G, p)

        score = score_path(reasoning, claim_text, previous)

        reasoning_paths.append({
            "text": reasoning,
            "score": score,
            "path": p
        })

        previous.append(reasoning)

    scores = [p["score"] for p in reasoning_paths]

    probabilities = softmax(scores)

    for i in range(len(reasoning_paths)):
        reasoning_paths[i]["probability"] = probabilities[i]
        
    best = max(reasoning_paths, key=lambda x: (x["probability"], x["score"], -len(x["path"]))
)

    return {
        "thoughts": [(i, reasoning_paths[i]) for i in range(len(reasoning_paths))],
        "paths": reasoning_paths,
        "best_thought": best["text"],
        "best_score": best["score"],
        "best_probability": best["probability"],
        "best_path": best["path"]
    }