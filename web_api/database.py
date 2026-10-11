from __future__ import annotations

from sqlalchemy import Engine, create_engine, inspect, text


def create_database_engine(database_url: str) -> Engine:
    connect_args = {"connect_timeout": 10} if database_url.startswith("postgresql") else {}
    return create_engine(database_url, pool_pre_ping=True, pool_recycle=300, connect_args=connect_args)


def table_exists(engine: Engine, table_name: str) -> bool:
    return inspect(engine).has_table(table_name)


def ensure_audit_table(engine: Engine) -> None:
    id_type = "INTEGER PRIMARY KEY AUTOINCREMENT" if engine.dialect.name == "sqlite" else "BIGSERIAL PRIMARY KEY"
    with engine.begin() as connection:
        connection.execute(
            text(
                f"""
                CREATE TABLE IF NOT EXISTS pipeline_audit_log (
                    id {id_type},
                    pipeline VARCHAR(40) NOT NULL,
                    status VARCHAR(24) NOT NULL,
                    requested_by VARCHAR(40) NOT NULL,
                    started_at TIMESTAMP NOT NULL,
                    finished_at TIMESTAMP NULL,
                    record_count INTEGER NULL,
                    message TEXT NULL
                )
                """
            )
        )

