from __future__ import annotations

from text_ingestion.config import get_settings
from text_ingestion.storage import MinIORawStore

if __name__ == "__main__":
    settings = get_settings()
    store = MinIORawStore(
        endpoint_url=settings.minio_endpoint_url,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        bucket=settings.minio_bucket,
        region=settings.minio_region,
        secure=settings.minio_secure,
    )
    store.ensure_bucket()
    print(f"Ensured MinIO bucket exists: {settings.minio_bucket}")
