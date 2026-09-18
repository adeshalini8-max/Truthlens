from fastapi import APIRouter, UploadFile, File

router = APIRouter(
    prefix="/api/fact-check",
    tags=["Image Fact Checking"]
)


@router.post("/image")
async def fact_check_image(
    file: UploadFile = File(...)
):

    return {
        "success": True,
        "type": "image",
        "filename": file.filename,
        "content_type": file.content_type,
        "verdict": "UNVERIFIED",
        "message": "Image received successfully. OCR processing will be added next."
    }
