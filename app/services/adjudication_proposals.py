"""Application service for browser-only automatic reconciliation proposals.

This service intentionally has no storage dependency.  It reads the current
conflict, asks ``formants_export`` to create the same recipe used by final
resolution, and optionally renders that recipe as a PNG.
"""

from __future__ import annotations

from formants_export.adjudication_proposals import (
    AutomaticAdjudicationProposal,
    create_automatic_adjudication_proposal,
)
from app.services import adjudication


def _proposal_context(
    payload: dict,
) -> tuple[dict, list[dict], AutomaticAdjudicationProposal]:
    """Resolve one request to its current token, sources, and recipe."""

    detail = adjudication.conflict_detail(token_id=payload["token_id"])
    annotations = detail["annotations"]
    proposal = create_automatic_adjudication_proposal(
        method=payload["method"],
        token=detail,
        annotations=annotations,
        random_seed=payload.get("random_seed", 0),
        include_needs_correction=payload.get("include_needs_correction", False),
    )
    return detail, annotations, proposal


def automatic_proposal(*, payload: dict) -> dict:
    """Return a machine-readable proposal without rendering or saving it."""

    _, _, proposal = _proposal_context(payload)
    return proposal.as_dict()


def automatic_proposal_preview(*, payload: dict) -> bytes:
    """Render the current deterministic proposal without writing a decision."""

    from formants_export.adjudication_rendering import (
        render_automatic_proposal_spectrogram,
    )

    token, annotations, proposal = _proposal_context(payload)
    pickle_path = adjudication._candidate_pickle_path(token)
    if not pickle_path.is_file():
        raise FileNotFoundError(pickle_path)
    return render_automatic_proposal_spectrogram(
        proposal,
        token,
        annotations,
        pickle_path.parent,
        maximum_frequency=token.get("max_plotting_frequency"),
    )
