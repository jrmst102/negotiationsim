"""
Storage layer — DigitalOcean Spaces (S3-compatible) + local filesystem fallback.
=================================================================================
Provides a thin abstraction for reading/writing text objects. Falls back to
local filesystem when SPACES_ACCESS_KEY_ID is not set.
"""

from __future__ import annotations

import io
import uuid
from pathlib import Path
from typing import Protocol

from app.storage.config import SpacesConfig, load_spaces_config, spaces_configured


class Store(Protocol):
    """Minimal key-value store interface."""
    def read_text(self, key: str) -> str: ...
    def write_text(self, key: str, text: str, content_type: str = "text/csv") -> None: ...
    def exists(self, key: str) -> bool: ...
    def list_keys(self, prefix: str) -> list[str]: ...
    def delete(self, key: str) -> None: ...


class LocalStore:
    """Store backed by the local filesystem (development fallback)."""

    def __init__(self, root: Path | str = Path(".")) -> None:
        self._root = Path(root)

    def _resolve(self, key: str) -> Path:
        return self._root / key

    def read_text(self, key: str) -> str:
        return self._resolve(key).read_text(encoding="utf-8")

    def write_text(self, key: str, text: str, content_type: str = "text/csv") -> None:
        path = self._resolve(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def exists(self, key: str) -> bool:
        return self._resolve(key).exists()

    def list_keys(self, prefix: str) -> list[str]:
        base = self._resolve(prefix)
        if not base.exists():
            return []
        if base.is_file():
            return [prefix]
        return sorted(
            str(p.relative_to(self._root))
            for p in base.rglob("*")
            if p.is_file()
        )

    def delete(self, key: str) -> None:
        path = self._resolve(key)
        if path.exists():
            path.unlink()


class SpacesStore:
    """Store backed by a DigitalOcean Spaces (S3-compatible) bucket."""

    def __init__(self, cfg: SpacesConfig) -> None:
        import boto3
        self._bucket = cfg.bucket
        self._s3 = boto3.client(
            "s3",
            region_name=cfg.region,
            endpoint_url=cfg.endpoint_url,
            aws_access_key_id=cfg.access_key_id,
            aws_secret_access_key=cfg.secret_access_key,
        )

    def _tmp_key(self, key: str) -> str:
        return f"{key}.tmp.{uuid.uuid4().hex[:12]}"

    def read_text(self, key: str) -> str:
        resp = self._s3.get_object(Bucket=self._bucket, Key=key)
        return resp["Body"].read().decode("utf-8")

    def write_text(self, key: str, text: str, content_type: str = "text/csv") -> None:
        tmp = self._tmp_key(key)
        self._s3.put_object(Bucket=self._bucket, Key=tmp, Body=text.encode("utf-8"), ContentType=content_type)
        self._s3.copy_object(Bucket=self._bucket, Key=key, CopySource={"Bucket": self._bucket, "Key": tmp})
        self._s3.delete_object(Bucket=self._bucket, Key=tmp)

    def exists(self, key: str) -> bool:
        try:
            self._s3.head_object(Bucket=self._bucket, Key=key)
            return True
        except self._s3.exceptions.ClientError:
            return False

    def list_keys(self, prefix: str) -> list[str]:
        keys: list[str] = []
        paginator = self._s3.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self._bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                k = obj["Key"]
                if not k.endswith(".tmp"):
                    keys.append(k)
        return sorted(keys)

    def delete(self, key: str) -> None:
        self._s3.delete_object(Bucket=self._bucket, Key=key)


# ── Singleton accessor ───────────────────────────────────────────────

_store_instance: Store | None = None


def get_store() -> Store:
    """Return the global Store instance (created on first call)."""
    global _store_instance
    if _store_instance is not None:
        return _store_instance

    if spaces_configured():
        cfg = load_spaces_config()
        _store_instance = SpacesStore(cfg)
    else:
        project_root = Path(__file__).resolve().parent.parent.parent
        _store_instance = LocalStore(root=project_root / "data" / "simulations")

    return _store_instance


def reset_store() -> None:
    global _store_instance
    _store_instance = None


def set_store(store: Store) -> None:
    global _store_instance
    _store_instance = store
