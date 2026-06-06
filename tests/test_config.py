from __future__ import annotations

from text_ingestion.config import Settings


def test_settings_accept_existing_minio_env_aliases(monkeypatch) -> None:
    monkeypatch.setenv("MINIO_ENDPOINT", "http://localhost:9000")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "minioadmin")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "minioadmin")

    settings = Settings()

    assert settings.minio_endpoint_url == "http://localhost:9000"
    assert settings.minio_access_key == "minioadmin"
    assert settings.minio_secret_key == "minioadmin"
