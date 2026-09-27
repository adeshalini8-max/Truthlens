from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes.text import router as text_router
from routes.image import router as image_router
from routes.audio import router as audio_router
from routes.video import router as video_router
from routes.history import router as history_router


app = FastAPI(
    title="TruthLens API",
    description="Multimodal misinformation fact-checking backend",
    version="1.0.0"
)


# ==============================
# CORS
# ==============================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==============================
# ROUTES
# ==============================

app.include_router(text_router)
app.include_router(image_router)
app.include_router(audio_router)
app.include_router(video_router)
app.include_router(history_router)


# ==============================
# HOME
# ==============================

@app.get("/")
def home():

    return {
        "message": "TruthLens Backend is Running"
    }


# ==============================
# HEALTH CHECK
# ==============================

@app.get("/api/health")
def health():

    return {
        "status": "healthy",
        "message": "TruthLens API is working"
    }