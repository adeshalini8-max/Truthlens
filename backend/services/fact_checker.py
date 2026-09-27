import json
import os
from difflib import SequenceMatcher

from services.search_service import search_web


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATABASE_PATH = os.path.join(
    BASE_DIR,
    "truthlens_database_1000.json"
)

HISTORY_PATH = os.path.join(
    BASE_DIR,
    "history.json"
)


# ==============================
# MANUAL DATABASE
# ==============================

def load_database():
    try:
        with open(
            DATABASE_PATH,
            "r",
            encoding="utf-8"
        ) as file:
            data = json.load(file)

        return data.get("records", [])

    except FileNotFoundError:
        print("DATABASE ERROR: truthlens_database_1000.json not found")
        return []

    except json.JSONDecodeError:
        print("DATABASE ERROR: Invalid JSON")
        return []

    except Exception as e:
        print("DATABASE ERROR:", e)
        return []


# ==============================
# HISTORY
# ==============================

def load_history():
    try:
        with open(
            HISTORY_PATH,
            "r",
            encoding="utf-8"
        ) as file:
            data = json.load(file)

        return data

    except FileNotFoundError:
        return {
            "checks": []
        }

    except json.JSONDecodeError:
        print("HISTORY ERROR: Invalid JSON")
        return {
            "checks": []
        }

    except Exception as e:
        print("HISTORY ERROR:", e)
        return {
            "checks": []
        }


def save_to_history(result):
    try:
        history = load_history()

        history["checks"].insert(
            0,
            result
        )

        # Latest 50 checks only
        history["checks"] = history["checks"][:50]

        with open(
            HISTORY_PATH,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                history,
                file,
                indent=2,
                ensure_ascii=False
            )

    except Exception as e:
        print("HISTORY SAVE ERROR:", e)


# ==============================
# SIMILARITY
# ==============================

def similarity_score(
    user_claim,
    database_claim
):

    user_claim = user_claim.lower().strip()

    database_claim = database_claim.lower().strip()

    return SequenceMatcher(
        None,
        user_claim,
        database_claim
    ).ratio()


def search_manual_database(claim):

    records = load_database()

    if not records:
        return None

    best_match = None

    best_score = 0

    for record in records:

        database_claim = record.get(
            "claim",
            ""
        ).strip()

        if not database_claim:
            continue

        score = similarity_score(
            claim,
            database_claim
        )

        if score > best_score:

            best_score = score

            best_match = record

    if best_match and best_score >= 0.75:

        result = dict(best_match)

        result["match_score"] = round(
            best_score * 100,
            2
        )

        return result

    return None


# ==============================
# MAIN FACT CHECK
# ==============================

def check_claim(claim: str):

    claim = claim.strip()

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


    # --------------------------
    # DATABASE SEARCH
    # --------------------------

    database_match = search_manual_database(
        claim
    )


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

            "topic": database_match.get(
                "topic",
                ""
            ),

            "sources": database_match.get(
                "sources",
                []
            ),

            "database_match": True,

            "database_id": database_match.get(
                "id",
                ""
            ),

            "checked_by": "TruthLens Manual Database"
        }

        save_to_history(result)

        return result


    # --------------------------
    # LIVE WEB SEARCH
    # --------------------------

    search_results = search_web(
        claim
    )

    sources = []

    for result in search_results:

        sources.append({
            "title": result.get(
                "title",
                ""
            ),

            "url": result.get(
                "url",
                ""
            ),

            "snippet": result.get(
                "snippet",
                ""
            ),

            "source": result.get(
                "source",
                ""
            ),

            "published": result.get(
                "published",
                ""
            ),

            "relevance": result.get(
                "relevance",
                0
            )
        })


    # --------------------------
    # EXPLANATION
    # --------------------------

    if sources:

        explanation = (
            "No sufficiently close match was found "
            "in the TruthLens manual database. "
            "Relevant web evidence was retrieved, "
            "but it requires further comparison "
            "before assigning a final verdict."
        )

    else:

        explanation = (
            "No sufficiently close match was found "
            "in the TruthLens manual database and "
            "no relevant web evidence was retrieved. "
            "The claim remains unverified."
        )


    result = {

        "claim": claim,

        "verdict": "UNVERIFIED",

        "confidence": 0,

        "explanation": explanation,

        "sources": sources,

        "database_match": False,

        "checked_by": "TruthLens Live Search"
    }


    # --------------------------
    # SAVE HISTORY
    # --------------------------

    save_to_history(
        result
    )


    return result