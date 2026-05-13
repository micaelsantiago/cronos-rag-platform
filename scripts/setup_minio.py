"""Creates the MinIO bucket on first run. Safe to re-run — idempotent."""

import sys

from minio import Minio
from minio.error import S3Error


def setup_bucket() -> None:
    from app.core.config import settings

    client = Minio(
        settings.MINIO_ENDPOINT,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=settings.MINIO_USE_SSL,
    )

    try:
        if client.bucket_exists(settings.MINIO_BUCKET):
            print(f"Bucket '{settings.MINIO_BUCKET}' already exists — skipping.")
        else:
            client.make_bucket(settings.MINIO_BUCKET)
            print(f"Bucket '{settings.MINIO_BUCKET}' created successfully.")
    except S3Error as e:
        print(f"MinIO error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    setup_bucket()
