"""
pipeline_utils.py
------------------
Robust utilities to load the fine-tuned discourse model and run inference.

Features:
- load_discourse_model(): loads tokenizer + model from ./stage1_model
- predict_discourse_segments(): tokenize essay text (sentence-splitting with NLTK),
  classify each sentence, handle long sentences via sliding-window chunking,
  and return a pandas.DataFrame with columns: text, predicted_discourse_type, confidence
"""
import os
import nltk

# ✅ Use your actual AFML nltk_data folder instead of AppData\Roaming
NLTK_DATA_PATH = r"C:\Desktop\3rd year\AFML5\AFML\nltk_data"
os.makedirs(NLTK_DATA_PATH, exist_ok=True)
nltk.data.path.append(NLTK_DATA_PATH)

# ✅ Just check, don’t auto-download (we already ran setup_nltk.py)
try:
    nltk.data.find("corpora/wordnet")
    nltk.data.find("corpora/omw-1.4")
    nltk.data.find("tokenizers/punkt")
    print("✅ NLTK data found and ready to use.")
except LookupError:
    print("⚠️  NLTK data missing! Please run setup_nltk.py again before running the app.")

# ✅ all other imports come AFTER this
from typing import List, Tuple, Optional, Dict, Any
import torch
import pandas as pd
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from collections import Counter
from nltk.tokenize import sent_tokenize




# ----------------------------
# CONFIG - change if needed
# ----------------------------
MODEL_PATH = os.path.join(os.path.dirname(__file__), "stage1_model")
LABEL_LIST = [
    "Lead",
    "Position",
    "Claim",
    "Counterclaim",
    "Rebuttal",
    "Evidence",
    "Concluding Statement",
]
ID_TO_LABEL = {i: label for i, label in enumerate(LABEL_LIST)}
MAX_LENGTH = 512
CHUNK_STRIDE = 128
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


# ----------------------------
# Model / Tokenizer loading
# ----------------------------
def load_discourse_model(model_path: Optional[str] = None) -> Tuple[AutoModelForSequenceClassification, AutoTokenizer]:
    """
    Load the tokenizer and fine-tuned sequence classification model.

    Args:
        model_path: optional path override (defaults to MODEL_PATH)

    Returns:
        model, tokenizer (model is in eval() mode and moved to DEVICE)
    """
    path = model_path or MODEL_PATH
    if not os.path.isdir(path):
        raise FileNotFoundError(
            f"Model folder not found at {path}. "
            f"Make sure you extracted stage1_model there."
        )

    print(f"📦 Loading model from: {path}  (device={DEVICE})")
    tokenizer = AutoTokenizer.from_pretrained(path, use_fast=True)
    model = AutoModelForSequenceClassification.from_pretrained(path)
    model.to(DEVICE)
    model.eval()
    return model, tokenizer


# ----------------------------
# Helper: split into sentences
# ----------------------------
def split_into_sentences(text: str) -> List[str]:
    """
    Use NLTK's sent_tokenize to split the essay into sentences.
    """
    if not text or not text.strip():
        return []
    sentences = sent_tokenize(text)
    sentences = [s.strip() for s in sentences if s.strip()]
    return sentences


# ----------------------------
# Helper: chunk long text into overlapping windows
# ----------------------------
def chunk_text_for_tokenizer(
    text: str, 
    tokenizer, 
    max_length: int = MAX_LENGTH, 
    stride: int = CHUNK_STRIDE
) -> List[Dict[str, Any]]:
    """
    Break a long piece of text into overlapping chunks suitable for the tokenizer.
    Returns a list of tokenized input dicts ready to pass to the model.
    """
    enc = tokenizer(text, return_offsets_mapping=True, add_special_tokens=False)
    input_ids = enc["input_ids"]
    offsets = enc.get("offset_mapping")

    if len(input_ids) <= max_length - tokenizer.num_special_tokens_to_add():
        return [tokenizer(
            text, 
            return_tensors="pt", 
            truncation=True, 
            padding=True, 
            max_length=max_length
        )]

    chunks = []
    start = 0
    window = max_length - tokenizer.num_special_tokens_to_add()
    
    while start < len(input_ids):
        end = min(start + window, len(input_ids))
        
        if offsets:
            char_start = offsets[start][0]
            char_end = offsets[end - 1][1]
            text_span = text[char_start:char_end]
        else:
            text_span = tokenizer.decode(
                input_ids[start:end], 
                skip_special_tokens=True, 
                clean_up_tokenization_spaces=True
            )
        
        tokenized = tokenizer(
            text_span, 
            return_tensors="pt", 
            truncation=True, 
            padding=True, 
            max_length=max_length
        )
        chunks.append(tokenized)
        
        if end == len(input_ids):
            break
        start += (window - stride)
    
    return chunks


# ----------------------------
# Helper: aggregate chunk predictions
# ----------------------------
def aggregate_chunk_predictions(
    chunk_logits_list: List[torch.Tensor]
) -> Tuple[int, float]:
    """
    Given logits tensors for chunks of the same sentence,
    aggregate them using majority vote.
    Returns: (pred_label_id, confidence)
    """
    probs_list = [
        torch.nn.functional.softmax(l, dim=-1).squeeze(0).cpu().numpy() 
        for l in chunk_logits_list
    ]
    argmaxes = [int(p.argmax()) for p in probs_list]
    majority = Counter(argmaxes).most_common()
    top_label, count = majority[0]
    avg_confidence = float(sum(p[top_label] for p in probs_list) / len(probs_list))
    return int(top_label), float(avg_confidence)


# ----------------------------
# Main: predict discourse segments
# ----------------------------
def predict_discourse_segments(
    essay_text: str, 
    model, 
    tokenizer, 
    max_chunk_len: int = MAX_LENGTH, 
    stride: int = CHUNK_STRIDE
) -> pd.DataFrame:
    """
    Given essay text, split into sentences and classify each sentence.
    
    Returns:
        pd.DataFrame with columns ['text', 'predicted_discourse_type', 'confidence']
    """
    sentences = split_into_sentences(essay_text)
    results = []

    for sent in sentences:
        enc = tokenizer(sent, add_special_tokens=True, truncation=False)
        token_len = len(enc["input_ids"])
        need_chunk = token_len > (max_chunk_len - tokenizer.num_special_tokens_to_add())

        if not need_chunk:
            inputs = tokenizer(
                sent,
                return_tensors="pt",
                truncation=True,
                padding=True,
                max_length=max_chunk_len
            )
            inputs = {k: v.to(DEVICE) for k, v in inputs.items()}
            
            with torch.no_grad():
                outputs = model(**inputs)
                logits = outputs.logits
                probs = torch.nn.functional.softmax(logits, dim=-1).squeeze(0).cpu().numpy()
                pred_id = int(probs.argmax())
                confidence = float(probs[pred_id])
        else:
            chunk_inputs = chunk_text_for_tokenizer(
                sent, tokenizer, max_length=max_chunk_len, stride=stride
            )
            chunk_logits = []
            for tk in chunk_inputs:
                tk = {k: v.to(DEVICE) for k, v in tk.items()}
                with torch.no_grad():
                    out = model(**tk)
                    chunk_logits.append(out.logits.cpu())
            pred_id, confidence = aggregate_chunk_predictions(chunk_logits)

        results.append({
            "text": sent,
            "predicted_discourse_type": ID_TO_LABEL.get(pred_id, "Unknown"),
            "confidence": round(confidence, 4)
        })

    df = pd.DataFrame(results)
    return df


# ----------------------------
# Small interactive test
# ----------------------------
if __name__ == "__main__":
    try:
        model, tokenizer = load_discourse_model()
        sample = (
            "School uniforms should be mandatory. "
            "Studies show uniforms increase focus by 15%. "
            "Therefore, all schools should adopt uniform policies."
        )
        df = predict_discourse_segments(sample, model, tokenizer)
        print(df.to_string(index=False))
    except Exception as e:
        print("Quick test failed:", str(e))
        print("Make sure the model folder exists at:", MODEL_PATH)