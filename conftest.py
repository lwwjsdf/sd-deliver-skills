"""Root pytest configuration for sd-deliver-skills.

Provides shared fixtures and adds plugin script directories to sys.path so
that tests can import modules under test without manual path manipulation.
"""
import sys
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent


def pytest_configure(config):
    """Add every sd-*/scripts directory (and one-level subdirs) to sys.path."""
    for scripts_dir in sorted(REPO_ROOT.glob("sd-*/scripts")):
        if str(scripts_dir) not in sys.path:
            sys.path.insert(0, str(scripts_dir))
        # Scripts often import sibling modules assuming their own directory is
        # on sys.path (e.g. sd-infra/scripts/builder/render.py imports layout).
        for subdir in sorted(scripts_dir.iterdir()):
            if subdir.is_dir() and not subdir.name.startswith("_"):
                if str(subdir) not in sys.path:
                    sys.path.insert(0, str(subdir))

    # Shared review protocol used by sd-infra/scripts/review
    shared_review = REPO_ROOT / "shared" / "review"
    if shared_review.is_dir() and str(shared_review) not in sys.path:
        sys.path.insert(0, str(shared_review))

    # Shared OpenAPI client used by sd-quality/scripts/fetch_data.py
    shared_postman = REPO_ROOT / "shared" / "postman"
    if shared_postman.is_dir() and str(shared_postman) not in sys.path:
        sys.path.insert(0, str(shared_postman))


@pytest.fixture(scope="session")
def repo_root():
    """Return the repository root path."""
    return REPO_ROOT


@pytest.fixture
def temp_dir():
    """Provide a temporary directory as a Path, cleaned up after the test."""
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp)


@pytest.fixture
def sample_tracking_plan():
    """Return a minimal tracking-plan dict for unit tests."""
    return {
        "project": "demo",
        "version": "1.0.0",
        "events": [
            {
                "event": "OrderPaid",
                "properties": [
                    {"name": "order_id", "type": "string", "required": True},
                    {"name": "amount", "type": "number", "required": True},
                ],
            },
            {
                "event": "ProductViewed",
                "properties": [
                    {"name": "product_id", "type": "string", "required": True},
                ],
            },
        ],
        "users": [
            {"name": "user_type", "type": "string", "required": True},
        ],
    }
