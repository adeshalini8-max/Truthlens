from fastapi import APIRouter, UploadFile, File

router = APIRouter(
    prefix="/api/fact-check",
    tags=["Video Fact Checking"]
)


@router.post("/video")
async def fact_check_video(
    file: UploadFile = File(...)
):

    return {
        "success": True,
        "type": "video",
        "filename": file.filename,
        "content_type": file.content_type,
        "verdict": "UNVERIFIED",
        "message": "Video received successfully. Video processing will be added next."
    }