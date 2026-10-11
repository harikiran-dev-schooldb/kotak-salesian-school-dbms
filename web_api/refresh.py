from __future__ import annotations

import os
import shlex
import subprocess
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import Engine, text

if __package__:
    from .config import Settings
else:  # Vercel standalone-module mode.
    from config import Settings


PIPELINES = {"students", "fees", "daywise", "concessions", "transactions", "attendance", "all"}


class RefreshManager:
    def __init__(self, settings: Settings, engine: Engine):
        self.settings = settings
        self.engine = engine
        self._lock = threading.Lock()
        self._state_lock = threading.Lock()
        self._active: dict[str, Any] | None = None

    def state(self) -> dict[str, Any]:
        with self._state_lock:
            return dict(self._active) if self._active else {"status": "idle"}

    def start(self, pipeline: str, requested_by: str) -> dict[str, Any]:
        if pipeline not in PIPELINES:
            raise ValueError(f"Unknown pipeline: {pipeline}")
        if not self.settings.enable_pipeline_execution:
            raise RuntimeError("Pipeline execution is disabled on this server")
        command = self.settings.pipeline_command(pipeline)
        if not command:
            raise RuntimeError(f"No command configured for the {pipeline} pipeline")
        if not self._lock.acquire(blocking=False):
            raise RuntimeError("Another refresh is already running")
        started_at = datetime.now(timezone.utc)
        with self.engine.begin() as connection:
            audit_id = connection.execute(
                text(
                    """
                    INSERT INTO pipeline_audit_log
                        (pipeline,status,requested_by,started_at,message)
                    VALUES (:pipeline,'running',:requested_by,:started_at,'Refresh requested')
                    RETURNING id
                    """
                ),
                {"pipeline": pipeline, "requested_by": requested_by, "started_at": started_at},
            ).scalar_one()
        with self._state_lock:
            self._active = {"status": "running", "pipeline": pipeline, "started_at": started_at.isoformat(), "audit_id": audit_id}
        thread = threading.Thread(
            target=self._run,
            args=(pipeline, command, audit_id),
            daemon=True,
            name=f"refresh-{pipeline}",
        )
        thread.start()
        return self.state()

    def _backup(self) -> Path:
        required = [
            self.settings.db_user,
            self.settings.db_password,
            self.settings.db_host,
            self.settings.db_port,
            self.settings.db_name,
        ]
        if not all(required):
            raise RuntimeError("Database backup settings are incomplete")
        self.settings.backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        target = self.settings.backup_dir / f"backup_{self.settings.db_name}_{timestamp}.dump"
        command = [
            self.settings.pg_dump_path,
            "-U", self.settings.db_user,
            "-h", self.settings.db_host,
            "-p", self.settings.db_port,
            "-F", "c",
            "-b",
            "-f", str(target),
            self.settings.db_name,
        ]
        environment = {**os.environ, "PGPASSWORD": self.settings.db_password}
        subprocess.run(command, env=environment, check=True, capture_output=True, text=True, timeout=300)
        if not target.is_file() or target.stat().st_size == 0:
            raise RuntimeError("Backup verification failed")
        backups = sorted(self.settings.backup_dir.glob("*.dump"), key=lambda item: item.stat().st_mtime, reverse=True)
        for expired in backups[5:]:
            expired.unlink()
        return target

    def _run(self, pipeline: str, command: str, audit_id: int) -> None:
        status, message = "failed", "Refresh failed"
        try:
            backup = self._backup()
            result = subprocess.run(
                shlex.split(command),
                cwd=Path(__file__).resolve().parents[1],
                check=True,
                capture_output=True,
                text=True,
                timeout=3600,
                env={**os.environ, "PYTHONUNBUFFERED": "1"},
            )
            status = "succeeded"
            message = f"Backup verified: {backup.name}. {result.stdout[-1200:].strip()}"
        except Exception as exc:
            message = str(exc)[-2000:]
        finally:
            finished_at = datetime.now(timezone.utc)
            with self.engine.begin() as connection:
                connection.execute(
                    text(
                        """
                        UPDATE pipeline_audit_log
                        SET status=:status, finished_at=:finished_at, message=:message
                        WHERE id=:audit_id
                        """
                    ),
                    {"status": status, "finished_at": finished_at, "message": message, "audit_id": audit_id},
                )
            with self._state_lock:
                self._active = {"status": status, "pipeline": pipeline, "finished_at": finished_at.isoformat(), "audit_id": audit_id}
            self._lock.release()

