"""
API routes for frontend.
"""

from fastapi import APIRouter

from app.routes.annotations import router as annotations_router
from app.routes.batches import router as batches_router
from app.routes.tokens import router as tokens_router
from app.routes.files import router as files_router
from app.routes.fasttrack import router as fasttrack_router
from app.routes.praat import router as praat_router

router = APIRouter(prefix="/api")

router.include_router(batches_router)
router.include_router(tokens_router)
router.include_router(annotations_router)
router.include_router(files_router)
router.include_router(fasttrack_router)
router.include_router(praat_router)