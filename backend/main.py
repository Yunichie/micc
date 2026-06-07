from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.router import router
from backend.core.config import settings
from backend.utils import image as image_utils


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start the image process pool on startup, shut it down on teardown.

    Previously the ProcessPoolExecutor was created at module-import time which
    caused worker process leaks on Uvicorn hot-reload and multi-worker
    deployments because the pool was never explicitly shut down.
    """
    image_utils.init_pool()
    yield
    image_utils.shutdown_pool()


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="High-performance image compression and conversion API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Conversion-Stats"],
)

app.include_router(router, prefix=settings.API_V1_STR)


@app.get("/health")
async def health_check():
    return {"status": "ok"}
