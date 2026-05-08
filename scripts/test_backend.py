"""
Simple backend integration test.

This script verifies that:

1. Tokens exist in the database.
2. Token assignments exist.
3. get_next_token() returns the expected token.
4. create_annotation() writes successfully.
5. Annotated tokens are skipped.
6. get_progress() returns sensible values.

Before running this test script run the following from the project root:
1. uv run python -m scripts.init_db
2. uv run python -m scripts.import_tokens
3. uv run python -m scripts.import_assignments

Then to test: uv run python -m scripts.test_backend

NOTE: Ian has pilot data in /data/ (not pushed to github) -- message him for testing data
"""

from sqlalchemy import func, select

from app import crud
from app.database import SessionLocal
from app.models import Annotation, Token, TokenAssignment
from app.schemas import AnnotationCreate


TEST_ANNOTATOR = "ian"


def print_header(title: str) -> None:
    print()
    print("=" * 60)
    print(title)
    print("=" * 60)


def main() -> None:
    """
    Run a simple end-to-end backend test.
    """

    db = SessionLocal()

    try:
        # ---------------------------------------------------------
        # 1. Verify token import
        # ---------------------------------------------------------

        print_header("CHECKING TOKENS")

        token_count = db.scalar(
            select(func.count()).select_from(Token)
        )

        print(f"Token count: {token_count}")

        if token_count == 0:
            raise RuntimeError("No tokens found in database.")

        # ---------------------------------------------------------
        # 2. Verify assignment import
        # ---------------------------------------------------------

        print_header("CHECKING TOKEN ASSIGNMENTS")

        assignment_count = db.scalar(
            select(func.count()).select_from(TokenAssignment)
        )

        print(f"Assignment count: {assignment_count}")

        if assignment_count == 0:
            raise RuntimeError("No token assignments found.")

        # ---------------------------------------------------------
        # 3. Get next token BEFORE annotation
        # ---------------------------------------------------------

        print_header("FETCHING NEXT TOKEN")

        token = crud.get_next_token(
            db=db,
            annotator_id=TEST_ANNOTATOR,
        )

        if token is None:
            raise RuntimeError(
                f"No available tokens for annotator '{TEST_ANNOTATOR}'."
            )

        print(f"Next token ID: {token.id}")
        print(f"Word: {token.word}")
        print(f"Auto winner panel: {token.auto_winner_panel}")

        # Save token ID to verify skipping behavior later
        first_token_id = token.id

        # ---------------------------------------------------------
        # 4. Create annotation
        # ---------------------------------------------------------

        print_header("CREATING ANNOTATION")

        annotation_in = AnnotationCreate(
            token_id=token.id,
            annotator_id=TEST_ANNOTATOR,
            decision="accept_auto",
            panel_f1=token.auto_winner_panel,
            panel_f2=token.auto_winner_panel,
            panel_f3=token.auto_winner_panel,
            panel_f4=token.auto_winner_panel,
            notes="Backend test annotation",
        )

        annotation = crud.create_annotation(
            db=db,
            annotation_in=annotation_in,
        )

        print(f"Created annotation ID: {annotation.id}")

        # ---------------------------------------------------------
        # 5. Verify token skipping behavior
        # ---------------------------------------------------------

        print_header("VERIFYING NEXT TOKEN SKIPS ANNOTATED TOKEN")

        next_token = crud.get_next_token(
            db=db,
            annotator_id=TEST_ANNOTATOR,
        )

        if next_token is None:
            print("No remaining tokens after annotation.")
        else:
            print(f"Next token after annotation: {next_token.id}")

            if next_token.id == first_token_id:
                raise RuntimeError(
                    "Annotated token was NOT skipped correctly."
                )

        # ---------------------------------------------------------
        # 6. Verify progress reporting
        # ---------------------------------------------------------

        print_header("CHECKING PROGRESS")

        progress = crud.get_progress(
            db=db,
            annotator_id=TEST_ANNOTATOR,
        )

        print(progress)

        print()
        print("Backend test completed successfully.")

    finally:
        db.close()


if __name__ == "__main__":
    main()