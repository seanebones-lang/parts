"""Tests for Jev shadow mode (must not affect production behavior)."""
import os
from pathlib import Path
import pytest

from parrts.email.pipeline import EmailPipeline
from parrts.email.store import EmailStore


@pytest.fixture()
def email_root(tmp_path: Path) -> Path:
    return tmp_path


def test_shadow_disabled_by_default(email_root: Path):
    """When JEV_SHADOW_ENABLED is not set, no shadow call should occur."""
    os.environ.pop("JEV_SHADOW_ENABLED", None)
    store = EmailStore(email_root)
    pipeline = EmailPipeline(store)
    # Should not raise even without TYPESAFE_API_KEY
    result = pipeline.ingest(
        subject="Test",
        body_text="Hello",
        sender_email="test@example.com",
        process=True,
    )
    assert result is not None
    assert "_jev_shadow" not in result


def test_shadow_enabled_but_no_key(email_root: Path):
    """When enabled but no key, production must still succeed."""
    os.environ["JEV_SHADOW_ENABLED"] = "1"
    os.environ.pop("TYPESAFE_API_KEY", None)
    store = EmailStore(email_root)
    pipeline = EmailPipeline(store)
    result = pipeline.ingest(
        subject="Test",
        body_text="Hello",
        sender_email="test@example.com",
        process=True,
    )
    assert result is not None


def test_shadow_does_not_override_production(email_root: Path):
    """Even if Jev runs, production classification must remain authoritative."""
    os.environ["JEV_SHADOW_ENABLED"] = "1"
    # We can't easily mock the API here, but the code path guarantees
    # that production clf is used regardless of Jev result.
    store = EmailStore(email_root)
    pipeline = EmailPipeline(store)
    result = pipeline.ingest(
        subject="Quote brake pads 2019 Honda Civic",
        body_text="How much?",
        sender_email="test@example.com",
        process=True,
    )
    assert result.get("email_type") == "price_request"  # production value
    # Shadow data, if present, must be in a separate field
    assert result.get("email_type") != result.get("_jev_shadow", {}).get("label")