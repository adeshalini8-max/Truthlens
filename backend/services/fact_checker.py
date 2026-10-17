
import json
import os
import re
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import urlparse

import torch
from transformers import pipeline

from services.search_service import search_web


# =========================================================
# PATHS AND CONFIGURATION
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_PATH = BASE_DIR / "truthlens_database_1000.json"
HISTORY_PATH = BASE_DIR / "history.json"

MODEL_NAME = "facebook/bart-large-mnli"
SUPPORT_THRESHOLD = 0.70
REFUTE_THRESHOLD = 0.70

_nli_pipeline = None


# =========================================================
# MODEL LOADING
# =========================================================

def load_nli_model():
    """Load the NLI model once and reuse it."""
    global _nli_pipeline

    if _nli_pipeline is None:
        device = 0 if torch.cuda.is_available() else -1

        _nli_pipeline = pipeline(
            "text-classification",
            model=MODEL_NAME,
            tokenizer=MODEL_NAME,
            device=device,
            truncation=True
        )

    return _nli_pipeline


# =========================================================
# GENERAL HELPERS
# =========================================================

def normalize_text(text):
    """Normalize text for matching."""
    text = str(text or "").lower()
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def tokenize(text):
    """Return useful words from text."""
    stop_words = {
        "the", "a", "an", "is", "are", "was", "were",
        "be", "been", "being", "to", "of", "in", "on",
        "at", "for", "and", "or", "but", "by", "with",
        "as", "it", "this", "that", "from", "has", "have",
        "had", "do", "does", "did", "its", "their", "they",
        "he", "she", "we", "you", "i", "who", "which"
    }

    return {
        word for word in normalize_text(text).split()
        if len(word) > 1 and word not in stop_words
    }


def safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def get_source_domain(source):
    """Return a normalized domain for an external source."""
    url = source.get("url", "")

    if not url:
        return ""

    try:
        domain = urlparse(url).netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
        return domain
    except Exception:
        return ""


# =========================================================
# LOCAL DATABASE
# =========================================================

def load_local_database():
    """Load the existing local fact-check database safely."""
    if not DATABASE_PATH.exists():
        return []

    try:
        with open(DATABASE_PATH, "r", encoding="utf-8") as file:
            data = json.load(file)

        if isinstance(data, list):
            return data

        if isinstance(data, dict):
            records = data.get("records", [])
            return records if isinstance(records, list) else []

    except (OSError, json.JSONDecodeError) as error:
        print(f"Database loading error: {error}")

    return []


def retrieve_database_evidence(claim, limit=5):
    """
    Retrieve matching local records.

    Local records are useful context but are not counted as
    independent external websites in the final verdict.
    """
    records = load_local_database()
    claim_normalized = normalize_text(claim)
    claim_tokens = tokenize(claim)
    matches = []

    for record in records:
        if not isinstance(record, dict):
            continue

        record_claim = record.get("claim", "")
        record_normalized = normalize_text(record_claim)
        record_tokens = tokenize(record_claim)

        if not record_normalized:
            continue

        if not claim_tokens:
            overlap = 0.0
        else:
            overlap = len(claim_tokens & record_tokens) / len(claim_tokens)

        similarity = SequenceMatcher(
            None,
            claim_normalized,
            record_normalized
        ).ratio()

        score = (0.65 * overlap) + (0.35 * similarity)

        if score < 0.12:
            continue

        matches.append({
            "id": record.get("id"),
            "title": record_claim,
            "claim": record_claim,
            "verdict": record.get("verdict", "UNVERIFIED"),
            "explanation": record.get("explanation", ""),
            "topic": record.get("topic", ""),
            "keywords": record.get("keywords", []),
            "sources": record.get("sources", []),
            "verified_date": record.get("verified_date", ""),
            "url": "",
            "snippet": (
                f"Existing database verdict: "
                f"{record.get('verdict', 'UNVERIFIED')}. "
                f"{record.get('explanation', '')}"
            ),
            "source": "TruthLens Local Database",
            "evidence_type": "local_database",
            "relevance": round(score, 4)
        })

    matches.sort(
        key=lambda item: item["relevance"],
        reverse=True
    )

    return matches[:limit]


# =========================================================
# LIVE WEB SEARCH
# =========================================================

def retrieve_web_evidence(claim, limit=10):
    """Fetch evidence using the existing search service."""
    try:
        results = search_web(claim)
    except Exception as error:
        print(f"Live search error: {error}")
        return []

    if not isinstance(results, list):
        return []

    cleaned_results = []
    seen_urls = set()

    for result in results:
        if not isinstance(result, dict):
            continue

        url = result.get("url", "")
        title = result.get("title", "")
        snippet = result.get("snippet", "")

        if not url or not (title or snippet):
            continue

        normalized_url = url.rstrip("/").lower()

        if normalized_url in seen_urls:
            continue

        seen_urls.add(normalized_url)

        cleaned_results.append({
            **result,
            "title": title,
            "url": url,
            "snippet": snippet,
            "source": result.get("source") or get_source_domain(result),
            "evidence_type": "web",
            "relevance": safe_float(result.get("relevance", 0))
        })

        if len(cleaned_results) >= limit:
            break

    return cleaned_results


# =========================================================
# NATURAL LANGUAGE INFERENCE
# =========================================================

def compare_evidence(claim, evidence):
    """
    Compare a claim against one evidence passage.

    NLI labels are SUPPORTS, REFUTES and NEUTRAL.
    Model scores are not factual probabilities.
    """
    text = str(evidence or "").strip()

    if not text:
        return {
            "supports": 0.0,
            "refutes": 0.0,
            "neutral": 1.0,
            "label": "NEUTRAL"
        }

    # Avoid passing extremely long webpages/snippets to the model.
    text = text[:1800]

    try:
        model = load_nli_model()

        result = model({
            "text": text,
            "text_pair": str(claim)
        })

        if isinstance(result, list):
            result = result[0]

        label = str(result.get("label", "")).upper()
        score = safe_float(result.get("score", 0.0))

        scores = {
            "supports": 0.0,
            "refutes": 0.0,
            "neutral": 0.0
        }

        if "ENTAILMENT" in label or "SUPPORT" in label:
            scores["supports"] = score
            scores["label"] = "SUPPORTS"

        elif "CONTRADICTION" in label or "REFUTE" in label:
            scores["refutes"] = score
            scores["label"] = "REFUTES"

        else:
            scores["neutral"] = score
            scores["label"] = "NEUTRAL"

        return scores

    except Exception as error:
        print(f"NLI analysis error: {error}")

        return {
            "supports": 0.0,
            "refutes": 0.0,
            "neutral": 1.0,
            "label": "NEUTRAL",
            "error": str(error)
        }


def analyze_sources(claim, sources):
    """Attach NLI scores to each retrieved evidence item."""
    analyzed = []

    for source in sources:
        item = dict(source)

        evidence_text = " ".join([
            str(item.get("title", "")),
            str(item.get("snippet", "")),
            str(item.get("explanation", ""))
        ]).strip()

        item["evidence_analysis"] = compare_evidence(
            claim,
            evidence_text
        )

        item["domain"] = get_source_domain(item)

        analyzed.append(item)

    return analyzed


# =========================================================
# VERDICT DECISION
# =========================================================

def decide_verdict(sources):
    """
    Decide a verdict using independent external domains.

    Local database entries do not count as external sources.
    Strong evidence on both sides results in UNVERIFIED.
    """
    domain_scores = {}

    for source in sources:
        if source.get("evidence_type") == "local_database":
            continue

        domain = get_source_domain(source)

        if not domain:
            continue

        analysis = source.get("evidence_analysis", {})

        support = safe_float(analysis.get("supports"))
        refute = safe_float(analysis.get("refutes"))

        if domain not in domain_scores:
            domain_scores[domain] = {
                "supports": 0.0,
                "refutes": 0.0
            }

        # Multiple pages from one website count as one domain.
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

        if support >= SUPPORT_THRESHOLD and support > refute:
            supporting.append((domain, support))

        if refute >= REFUTE_THRESHOLD and refute > support:
            refuting.append((domain, refute))

    # Both sides have strong evidence: do not force a verdict.
    if supporting and refuting:
        return (
            "UNVERIFIED",
            0,
            "Strong evidence appears on both sides. The retrieved "
            "passages may refer to different dates, definitions, "
            "or contexts. Review the sources before deciding."
        )

    if len(supporting) >= 2:
        confidence = round(
            sum(score for _, score in supporting)
            / len(supporting) * 100,
            2
        )

        return (
            "SUPPORTED",
            confidence,
            "At least two distinct external domains contain evidence "
            "that the NLI model considers consistent with the claim. "
            "This score is not a factual probability."
        )

    if len(refuting) >= 2:
        confidence = round(
            sum(score for _, score in refuting)
            / len(refuting) * 100,
            2
        )

        return (
            "REFUTED",
            confidence,
            "At least two distinct external domains contain evidence "
            "that the NLI model considers contradictory to the claim. "
            "This score is not a factual probability."
        )

    return (
        "UNVERIFIED",
        0,
        "There is not enough independent, consistent external evidence "
        "to assign a reliable verdict. Unverified does not mean false."
    )


# =========================================================
# HISTORY
# =========================================================

def save_history(result):
    """Save recent claim-check results."""
    try:
        if HISTORY_PATH.exists():
            with open(HISTORY_PATH, "r", encoding="utf-8") as file:
                history = json.load(file)

            if not isinstance(history, list):
                history = []
        else:
            history = []

        history.insert(0, result)
        history = history[:50]

        with open(HISTORY_PATH, "w", encoding="utf-8") as file:
            json.dump(
                history,
                file,
                ensure_ascii=False,
                indent=2
            )

    except (OSError, json.JSONDecodeError) as error:
        print(f"History save error: {error}")


# =========================================================
# MAIN FACT-CHECK FUNCTION
# =========================================================

def check_claim(claim):
    """
    Fact-check a claim using live web search, local retrieval,
    and the BART MNLI model.
    """
    if not isinstance(claim, str) or not claim.strip():
        return {
            "claim": claim,
            "verdict": "UNVERIFIED",
            "confidence": 0,
            "explanation": "Please enter a non-empty claim.",
            "sources": [],
            "checked_by": "TruthLens"
        }

    claim = claim.strip()

    # 1. Retrieve external web evidence.
    web_sources = retrieve_web_evidence(claim)

    # 2. Retrieve matching local database records.
    local_sources = retrieve_database_evidence(claim)

    # 3. Combine results and analyze evidence.
    combined_sources = web_sources + local_sources
    analyzed_sources = analyze_sources(claim, combined_sources)

    # 4. Decide the verdict using external domains only.
    verdict, confidence, explanation = decide_verdict(
        analyzed_sources
    )

    # 5. If there is no usable web evidence, be transparent.
    web_domains = {
        get_source_domain(source)
        for source in analyzed_sources
        if source.get("evidence_type") != "local_database"
        and get_source_domain(source)
    }

    if not web_domains:
        explanation = (
            "Live external evidence could not be retrieved. "
            "Local database matches are shown for reference only "
            "and are not enough by themselves to verify this claim."
        )

    result = {
        "claim": claim,
        "verdict": verdict,
        "confidence": confidence,
        "explanation": explanation,
        "sources": analyzed_sources,
        "checked_by": "TruthLens Live Search + Local Database + BART NLI"
    }

    save_history(result)

    return result


# =========================================================
# COMPATIBILITY ALIAS
# =========================================================

def fact_check(claim):
    """Alias for projects importing fact_check instead of check_claim."""
    return check_claim(claim)
