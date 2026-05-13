"""
FastAPI application entry point.

This app exposes:
- API routes under /api
- static files under /static
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import ANNOTATOR_ID, STATIC_DIR
from app.routes.api import router as api_router

app = FastAPI(
    title="Formant Annotation Tool",
    description="Local web app for validating pre-generated formant candidates.",
    version="0.1.0",
)

app.include_router(api_router)

if STATIC_DIR.exists():
    app.mount(
        "/static",
        StaticFiles(directory=STATIC_DIR),
        name="static",
    )

@app.get("/", include_in_schema=False)
def health_check() -> dict:
    """
    Minimal root endpoint for now.
    This will later render Jinja annotation pages.
    """

    return {
        "status": "ok",
        "annotator_id": ANNOTATOR_ID,
        "message": "Formant Annotation Tool API is running.",
    }