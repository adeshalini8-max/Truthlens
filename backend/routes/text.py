from fastapi import APIRouter
from pydantic import BaseModel

from services.fact_checker import check_claim


router = APIRouter(
    prefix="/api/fact-check",
    tags=["Text Fact Checking"]
)


class TextRequest(BaseModel):
    text: str


@router.post("/text")
def fact_check_text(request: TextRequest):

    claim = request.text.strip()

    if not claim:
        return {
            "success": False,
            "message": "Please provide some text."
        }

    result = check_claim(claim)

    return {
        "success": True,
        "type": "text",
        **result
    }