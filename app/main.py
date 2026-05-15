"""
FastAPI application entry point.

This app exposes:
- the Jinja annotation page at /
- API routes under /api
- static files under /static
"""

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import ANNOTATOR_ID, STATIC_DIR, TEMPLATES_DIR
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

templates = Jinja2Templates(directory=TEMPLATES_DIR)

@app.get("/", include_in_schema=False)
def annotation_page(request: Request):
    """
    Render the main annotation interface.

    The frontend JavaScript will call the backend API to load tokens,
    save annotations, and update progress.
    """

    return templates.TemplateResponse(
        request=request,
        name="annotate.html",
        context={"annotator_id": ANNOTATOR_ID},
    )

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """
    Serve favicon for browser tab icon.
    """

    return FileResponse(STATIC_DIR / "favicon.ico")