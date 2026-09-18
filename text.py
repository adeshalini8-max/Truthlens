from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(
    prefix="/api/fact-check",
    tags=["Text Fact Checking"]
)


class TextRequest(BaseModel):
    text: str


@router.post("/text")
def fact_check_text(request: TextRequest):

    text = request.text.strip()

    if not text:
        return {
            "success": False,
            "message": "Please provide some text."
        }

    return {
        "success": True,
        "type": "text",
        "claim": text,
        "verdict": "UNVERIFIED",
        "explanation": "Live evidence checking will be connected next.",
        "sources": []
    }