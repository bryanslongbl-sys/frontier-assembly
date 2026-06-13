"""Persistence layer with two interchangeable backends.

- ObjectStore: S3-compatible Nebius Object Storage (production / Serverless Job).
- LocalStore:  the local filesystem (so judges can run a full debate with NO bucket,
               only a NEBIUS_API_KEY — maximum reproducibility).

Both expose the same put_json / get_json / put_text interface, so the orchestrator
is storage-agnostic.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from shared.config import S3_BUCKET, S3_ENDPOINT, S3_REGION


def _to_text(payload: BaseModel | dict | Any) -> str:
    if isinstance(payload, BaseModel):
        return payload.model_dump_json(indent=2)
    return json.dumps(payload, indent=2, default=str)


class ObjectStore:
    """S3-compatible Nebius Object Storage."""

    def __init__(self, bucket: str | None = None, endpoint_url: str | None = None) -> None:
        import boto3

        self.bucket = bucket or S3_BUCKET
        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint_url or S3_ENDPOINT,
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            region_name=S3_REGION,
        )

    def put_json(self, key: str, payload: BaseModel | dict) -> None:
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=_to_text(payload).encode("utf-8"),
            ContentType="application/json",
        )

    def get_json(self, key: str) -> dict:
        obj = self.client.get_object(Bucket=self.bucket, Key=key)
        return json.loads(obj["Body"].read().decode("utf-8"))

    def put_text(self, key: str, text: str, content_type: str = "text/plain") -> None:
        self.client.put_object(
            Bucket=self.bucket, Key=key, Body=text.encode("utf-8"), ContentType=content_type
        )


class LocalStore:
    """Filesystem mirror of ObjectStore for local dev / reproducible judge runs."""

    def __init__(self, root: str = "artifacts") -> None:
        self.root = Path(root)
        self.bucket = str(self.root)

    def _path(self, key: str) -> Path:
        p = self.root / key
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    def put_json(self, key: str, payload: BaseModel | dict) -> None:
        self._path(key).write_text(_to_text(payload), encoding="utf-8")

    def get_json(self, key: str) -> dict:
        return json.loads(self._path(key).read_text(encoding="utf-8"))

    def put_text(self, key: str, text: str, content_type: str = "text/plain") -> None:
        self._path(key).write_text(text, encoding="utf-8")
