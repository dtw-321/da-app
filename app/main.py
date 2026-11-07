import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes_workflow import router as workflow_router
from app.config.settings import settings
from app.core.paths import FRONTEND_DIR, ensure_dirs
from app.database.connection import Base, engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

app = FastAPI(title=settings.PROJECT_NAME, version="3.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list or ["http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    ensure_dirs()
    if settings.AUTO_CREATE_TABLES:
        from app.database import models  # noqa: F401
        Base.metadata.create_all(bind=engine)


app.include_router(workflow_router)

if FRONTEND_DIR.exists():
    app.mount("/frontend", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/frontend/index.html")


@app.get("/api/health", tags=["System"])
def health():
    return {"status": "online", "env": settings.ENV, "version": app.version}
