from fastapi import APIRouter, UploadFile, File

router = APIRouter(
    prefix="/api/fact-check",
    tags=["Audio Fact Checking"]
)


@router.post("/audio")
async def fact_check_audio(
    file: UploadFile = File(...)
):

    return {
        "success": True,
        "type": "audio",
        "filename": file.filename,
        "content_type": file.content_type,
        "verdict": "UNVERIFIED",
        "message": "Audio received successfully. Speech-to-text processing will be added next."
    }