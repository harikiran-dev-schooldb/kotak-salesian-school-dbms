from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR / ".env")


def _as_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _origins() -> list[str]:
    raw = os.getenv(
        "WEB_ALLOWED_ORIGINS",
        "https://kotak-school-data-hub.buzzycoot64.chatgpt.site,http://127.0.0.1:4173,http://localhost:4173",
    )
    return [value.strip().rstrip("/") for value in raw.split(",") if value.strip()]


@dataclass(slots=True)
class Settings:
    database_url: str = field(default_factory=lambda: os.getenv("DATABASE_URL", ""))
    environment: str = field(default_factory=lambda: os.getenv("ENVIRONMENT", "development"))
    admin_api_key: str = field(default_factory=lambda: os.getenv("ADMIN_API_KEY", ""))
    viewer_api_key: str = field(default_factory=lambda: os.getenv("VIEWER_API_KEY", ""))
    auth_disabled: bool = field(default_factory=lambda: _as_bool("AUTH_DISABLED", False))
    allowed_origins: list[str] = field(default_factory=_origins)
    backup_dir: Path = field(
        default_factory=lambda: Path(os.getenv("BACKUP_DIR", ROOT_DIR / "postgres_backups"))
    )
    pg_dump_path: str = field(default_factory=lambda: os.getenv("PG_DUMP_PATH", "pg_dump"))
    db_user: str = field(default_factory=lambda: os.getenv("DB_USER", ""))
    db_password: str = field(default_factory=lambda: os.getenv("DB_PASSWORD", ""))
    db_host: str = field(default_factory=lambda: os.getenv("DB_HOST", ""))
    db_port: str = field(default_factory=lambda: os.getenv("DB_PORT", "5432"))
    db_name: str = field(default_factory=lambda: os.getenv("DB_NAME", ""))
    enable_pipeline_execution: bool = field(
        default_factory=lambda: _as_bool("ENABLE_PIPELINE_EXECUTION", False)
    )

    def validate(self) -> None:
        if not self.database_url:
            raise RuntimeError("DATABASE_URL is required")
        if self.environment.lower() == "production" and self.auth_disabled:
            raise RuntimeError("AUTH_DISABLED cannot be enabled in production")
        if not self.auth_disabled and (not self.admin_api_key or not self.viewer_api_key):
            raise RuntimeError("ADMIN_API_KEY and VIEWER_API_KEY are required")

    def pipeline_command(self, pipeline: str) -> str:
        key = f"REFRESH_{pipeline.upper()}_COMMAND"
        return os.getenv(key, "").strip()

