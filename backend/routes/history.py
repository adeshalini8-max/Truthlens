from fastapi import APIRouter
import json
import os

router = APIRouter(
    prefix="/api/fact-check",
    tags=["Fact Check History"]
)

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

HISTORY_PATH = os.path.join(
    BASE_DIR,
    "history.json"
)


@router.get("/history")
def get_history():

    try:
        with open(
            HISTORY_PATH,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        return {
            "success": True,
            "checks": data.get(
                "checks",
                []
            )
        }

    except FileNotFoundError:

        return {
            "success": True,
            "checks": []
        }

    except json.JSONDecodeError:

        return {
            "success": False,
            "checks": [],
            "message": "History file is invalid."
        }

    except Exception as e:

        return {
            "success": False,
            "checks": [],
            "message": str(e)
        }