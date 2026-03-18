"""
Storage configuration — reads DigitalOcean Spaces credentials from env vars.
=============================================================================
Required environment variables (only when Spaces is enabled):

    SPACES_ACCESS_KEY_ID
    SPACES_SECRET_ACCESS_KEY
    SPACES_REGION          (default: sfo3)
    SPACES_BUCKET          (default: negotiation-sim)
    SPACES_ENDPOINT        (default: https://sfo3.digitaloceanspaces.com)

If ``SPACES_ACCESS_KEY_ID`` is **not** set the system falls back to local
filesystem I/O (no cloud dependency required for development).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(_PROJECT_ROOT / ".env")


@dataclass(frozen=True)
class SpacesConfig:
    """Immutable snapshot of Spaces connection details."""
    access_key_id: str
    secret_access_key: str
    region: str
    bucket: str
    endpoint_url: str


def spaces_configured() -> bool:
    """Return True if Spaces credentials are present in the environment."""
    return bool(os.environ.get("SPACES_ACCESS_KEY_ID"))


def load_spaces_config() -> SpacesConfig:
    """Build a SpacesConfig from environment variables."""
    access_key = os.environ.get("SPACES_ACCESS_KEY_ID", "").strip()
    secret_key = os.environ.get("SPACES_SECRET_ACCESS_KEY", "").strip()

    if not access_key:
        raise EnvironmentError("SPACES_ACCESS_KEY_ID is not set.")
    if not secret_key:
        raise EnvironmentError("SPACES_SECRET_ACCESS_KEY is not set.")

    return SpacesConfig(
        access_key_id=access_key,
        secret_access_key=secret_key,
        region=os.environ.get("SPACES_REGION", "sfo3").strip(),
        bucket=os.environ.get("SPACES_BUCKET", "negotiation-sim").strip(),
        endpoint_url=os.environ.get(
            "SPACES_ENDPOINT", "https://sfo3.digitaloceanspaces.com"
        ).strip(),
    )
