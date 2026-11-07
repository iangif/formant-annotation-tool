"""
API routes for frontend.
"""

from fastapi import APIRouter

from app.routes.annotations import router as annotations_router
from app.routes.notes import router as notes_router
from app.routes.batches import router as batches_router
from app.routes.tokens import router as tokens_router
from app.routes.files import router as files_router
from app.routes.fasttrack import router as fasttrack_router
from app.routes.praat import router as praat_router

try:
    # Adjudication needs the lab-only `formants-export` package. Without it
    # (e.g. the public demo), the annotation app still runs.
    from app.routes.adjudication import router as adjudication_router
except ImportError:
    adjudication_router = None

router = APIRouter(prefix="/api")

router.include_router(batches_router)
router.include_router(tokens_router)
router.include_router(annotations_router)
router.include_router(notes_router)
router.include_router(files_router)
router.include_router(fasttrack_router)
router.include_router(praat_router)
if adjudication_router is not None:
    router.include_router(adjudication_router)
