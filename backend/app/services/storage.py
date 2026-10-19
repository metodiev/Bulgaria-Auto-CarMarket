from __future__ import annotations

import logging
from functools import cached_property

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import Settings, settings as default_settings

logger = logging.getLogger(__name__)


class StorageError(Exception):
    pass


class ObjectStorage:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or default_settings

    @property
    def endpoint_url(self) -> str:
        endpoint = self.settings.s3_endpoint
        if self.settings.s3_secure and endpoint.startswith("http://"):
            return "https://" + endpoint[len("http://") :]
        return endpoint

    @cached_property
    def client(self):
        return boto3.client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.settings.s3_access_key,
            aws_secret_access_key=self.settings.s3_secret_key,
            region_name="us-east-1",
            config=Config(
                signature_version="s3v4",
                connect_timeout=3,
                read_timeout=3,
                retries={"max_attempts": 2, "mode": "standard"},
                s3={"addressing_style": "path"},
            ),
        )

    def ensure_bucket(self) -> None:
        try:
            self.client.head_bucket(Bucket=self.settings.s3_bucket)
            return
        except ClientError as exc:
            code = str(exc.response.get("Error", {}).get("Code", ""))
            if code not in {"404", "NoSuchBucket", "NotFound"}:
                raise StorageError(f"Cannot access bucket: {exc}") from exc
        try:
            self.client.create_bucket(Bucket=self.settings.s3_bucket)
        except (BotoCoreError, ClientError) as exc:
            raise StorageError(f"Cannot create bucket: {exc}") from exc

    def put_bytes(self, key: str, data: bytes, content_type: str) -> str:
        self.ensure_bucket()
        try:
            self.client.put_object(
                Bucket=self.settings.s3_bucket,
                Key=key,
                Body=data,
                ContentType=content_type,
                Metadata={"app": "bulgaria-auto-carmarket"},
            )
        except (BotoCoreError, ClientError) as exc:
            raise StorageError(f"Cannot upload object {key!r}: {exc}") from exc
        return key

    def health_check(self) -> bool:
        try:
            self.client.head_bucket(Bucket=self.settings.s3_bucket)
            return True
        except Exception:
            return False


storage = ObjectStorage()
