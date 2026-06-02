from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.api.router import router
from backend.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="High-performance image compression and conversion API",
    version="1.0.0"
)

# Allow cross-origin requests from the Streamlit frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this to the frontend origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix=settings.API_V1_STR)

@app.get("/health")
async def health_check():
    return {"status": "ok"}
