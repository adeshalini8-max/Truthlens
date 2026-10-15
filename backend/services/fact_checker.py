
import json
import os
from difflib import SequenceMatcher
from urllib.parse import urlparse

import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

from services.search_service import search_web


# ==============================
# PATHS AND MODEL SETTINGS
# ==============================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATABASE_PATH = os.path.join(BASE_DIR, "truthlens_database_1000.json")
HISTORY_PATH = os.path.join(BASE_DIR, "history.json")

MODEL_NAME = "facebook/bart-large-mnli"

_tokenizer = None
_model = None


# ==============================
# LOAD PRETRAINED MODEL
# ==============================

def load_nli_model():
    global _tokenizer, _model

    if _tokenizer is None or _model is None:
        print("Loading TruthLens evidence analysis model...")

        _tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        _model = AutoModelForSequenceClassification.from_pretrained(
            MODEL_NAME
        )
        _model.eval()

        print("Evidence analysis model loaded.")

    return _tokenizer, _model


# ==============================
# EVIDENCE COMPARISON
# ==============================

def compare_evidence(claim, evidence):
    """
    Compare a claim with a search-result snippet.

    The evidence is the premise and the claim is the hypothesis.
    Model scores are inference scores, not factual probabilities.
    """

    if not evidence or len(evidence.strip()) < 20:
        return {
            "supports": 0.0,
            "refutes": 0.0,
            "neutral": 1.0
        }

    tokenizer, model = load_nli_model()

    inputs = tokenizer(
        evidence,
        claim,
        return_tensors="pt",
        truncation=True,
        max_length=512
    )

    with torch.no_grad():
        logits = model(**inputs).logits[0]
        probabilities = torch.softmax(logits, dim=-1).tolist()

    labels = model.config.id2label

    label_scores = {
        str(labels[i]).lower(): float(probabilities[i])
        for i in range(len(probabilities))
    }

    def find_score(label_name):
        for label, score in label_scores.items():
            if label_name in label:
                return score
        return 0.0

    return {
        "supports": find_score("entailment"),
        "refutes": find_score("contradiction"),
        "neutral": find_score("neutral")
    }


# ==============================
# MANUAL DATABASE
# ==============================

def load_database():
    try:
        with open(DATABASE_PATH, "r", encoding="utf-8") as file:
            data = json.load(file)

        if isinstance(data, dict):
            return data.get("records", [])

        return data if isinstance(data, list) else []

    except FileNotFoundError:
        print("DATABASE ERROR: truthlens_database_1000.json not found")
    except json.JSONDecodeError:
        print("DATABASE ERROR: Invalid JSON")
    except Exception as e:
        print("DATABASE ERROR:", e)

    return []


def similarity_score(user_claim, database_claim):
    return SequenceMatcher(
        None,
        user_claim.lower().strip(),
        database_claim.lower().strip()
    ).ratio()


def search_manual_database(claim):
    records = load_database()

    best_match = None
    best_score = 0.0

    for record in records:
        database_claim = record.get("claim", "").strip()

        if not database_claim:
            continue

        score = similarity_score(claim, database_claim)

        if score > best_score:
            best_score = score
            best_match = record

    # Use a stricter threshold to reduce accidental fuzzy matches.
    if best_match and best_score >= 0.90:
        result = dict(best_match)
        result["match_score"] = round(best_score * 100, 2)
        return result

    return None


# ==============================
# HISTORY
# ==============================

def load_history():
    try:
        with open(HISTORY_PATH, "r", encoding="utf-8") as file:
            data = json.load(file)

        if not isinstance(data, dict):
            return {"checks": []}

        if not isinstance(data.get("checks"), list):
            data["checks"] = []

        return data

    except FileNotFoundError:
        return {"checks": []}
    except json.JSONDecodeError:
        print("HISTORY ERROR: Invalid JSON")
        return {"checks": []}
    except Exception as e:
        print("HISTORY ERROR:", e)
        return {"checks": []}


def save_to_history(result):
    try:
        history = load_history()

        history["checks"].insert(0, result)
        history["checks"] = history["checks"][:50]

        with open(HISTORY_PATH, "w", encoding="utf-8") as file:
            json.dump(
                history,
                file,
                indent=2,
                ensure_ascii=False
            )

    except Exception as e:
        print("HISTORY SAVE ERROR:", e)


# ==============================
# SOURCE HELPERS
# ==============================

def get_source_domain(source):
    url = source.get("url", "")
    domain = urlparse(url).netloc.lower()

    if domain.startswith("www."):
        domain = domain[4:]

    if domain:
        return domain

    return source.get("source", "").lower().strip()


def analyze_sources(claim, search_results):
    analyzed_sources = []

    for source in search_results:
        title = source.get("title", "")
        snippet = source.get("snippet", "")
        evidence = f"{title}. {snippet}".strip()

        if len(evidence) < 20:
            continue

        try:
            scores = compare_evidence(claim, evidence)

        except Exception as e:
            print("EVIDENCE ANALYSIS ERROR:", e)

            scores = {
                "supports": 0.0,
                "refutes": 0.0,
                "neutral": 1.0
            }

        analyzed_sources.append({
            "title": title,
            "url": source.get("url", ""),
            "snippet": snippet,
            "source": source.get(
                "source",
                get_source_domain(source)
            ),
            "published": source.get("published", ""),
            "relevance": source.get("relevance", 0),
            "evidence_analysis": scores
        })

    return analyzed_sources


# ==============================
# VERDICT DECISION
# ==============================

def decide_verdict(sources):
    """
    Aggregate evidence by distinct domain.

    Multiple pages from the same domain count as one domain.
    Conflicting evidence results in UNVERIFIED.
    """

    domain_scores = {}

    for source in sources:
        scores = source.get("evidence_analysis", {})
        domain = get_source_domain(source)

        if not domain:
            continue

        support = scores.get("supports", 0.0)
        refute = scores.get("refutes", 0.0)

        if domain not in domain_scores:
            domain_scores[domain] = {
                "supports": 0.0,
                "refutes": 0.0
            }

        # Keep the strongest score per domain.
        domain_scores[domain]["supports"] = max(
            domain_scores[domain]["supports"],
            support
        )

        domain_scores[domain]["refutes"] = max(
            domain_scores[domain]["refutes"],
            refute
        )

    supporting = []
    refuting = []

    for domain, scores in domain_scores.items():
        support = scores["supports"]
        refute = scores["refutes"]

        if support >= 0.70 and support > refute:
            supporting.append(support)

        elif refute >= 0.70 and refute > support:
            refuting.append(refute)

    # Do not force a verdict when strong evidence conflicts.
    if supporting and refuting:
        return (
            "UNVERIFIED",
            0,
            "The retrieved sources contain conflicting evidence. "
            "Review the source context before deciding."
        )

    if len(supporting) >= 2:
        score = round(
            sum(supporting) / len(supporting) * 100,
            2
        )

        return (
            "SUPPORTED",
            score,
            "At least two distinct domains contain evidence consistent "
            "with the claim according to the NLI model. Check the "
            "linked sources and their context."
        )

    if len(refuting) >= 2:
        score = round(
            sum(refuting) / len(refuting) * 100,
            2
        )

        return (
            "REFUTED",
            score,
            "At least two distinct domains contain evidence contradictory "
            "to the claim according to the NLI model. Check the linked "
            "sources and their context."
        )

    return (
        "UNVERIFIED",
        0,
        "There is insufficient independent evidence for a reliable "
        "verdict. Unverified does not mean false."
    )


# ==============================
# MAIN FACT CHECK
# ==============================

def check_claim(claim: str):
    claim = (claim or "").strip()

    if not claim:
        result = {
            "claim": "",
            "verdict": "UNVERIFIED",
            "confidence": 0,
            "explanation": "No claim was provided.",
            "sources": [],
            "checked_by": "TruthLens"
        }

        save_to_history(result)
        return result

    # ------------------------------
    # LIVE WEB SEARCH FIRST
    # ------------------------------

    try:
        search_results = search_web(claim) or []

    except Exception as e:
        print("WEB SEARCH ERROR:", e)
        search_results = []

    # ------------------------------
    # ANALYZE SEARCH EVIDENCE
    # ------------------------------

    sources = analyze_sources(claim, search_results)

    if sources:
        verdict, confidence, explanation = decide_verdict(sources)

        result = {
            "claim": claim,
            "verdict": verdict,
            "confidence": confidence,
            "explanation": explanation,
            "sources": sources,
            "database_match": False,
            "checked_by": "TruthLens Live Search + NLI"
        }

    else:
        # ------------------------------
        # DATABASE FALLBACK
        # ------------------------------

        database_match = search_manual_database(claim)

        if database_match:
            result = {
                "claim": claim,
                "verdict": database_match.get(
                    "verdict",
                    "UNVERIFIED"
                ),
                "confidence": database_match.get(
                    "match_score",
                    0
                ),
                "explanation": database_match.get(
                    "explanation",
                    ""
                ),
                "topic": database_match.get("topic", ""),
                "sources": database_match.get("sources", []),
                "database_match": True,
                "database_id": database_match.get("id", ""),
                "checked_by": "TruthLens Manual Database Fallback"
            }

        else:
            result = {
                "claim": claim,
                "verdict": "UNVERIFIED",
                "confidence": 0,
                "explanation": (
                    "No usable live web evidence or sufficiently close "
                    "database match was found. Try rephrasing the claim "
                    "or checking reliable sources directly."
                ),
                "sources": [],
                "database_match": False,
                "checked_by": "TruthLens"
            }

    # ------------------------------
    # SAVE HISTORY
    # ------------------------------

    save_to_history(result)

    return result
