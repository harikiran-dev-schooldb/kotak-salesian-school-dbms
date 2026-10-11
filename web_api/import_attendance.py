from __future__ import annotations

import argparse
import csv
import os
import subprocess
import tempfile
from collections.abc import Iterator
from datetime import date, datetime
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_SOURCES = (
    ROOT_DIR / "source_data" / "AttendanceReport_2024_2025.csv",
    ROOT_DIR / "source_data" / "attendance_data.csv",
)


def academic_year_id(attendance_date: date) -> int:
    start_year = attendance_date.year if attendance_date.month >= 6 else attendance_date.year - 1
    mapping = {2024: 1, 2025: 2, 2026: 3}
    if start_year not in mapping:
        raise ValueError(f"Unsupported academic year beginning {start_year}")
    return mapping[start_year]


def _integer(value: str) -> int:
    return int(float(str(value).strip()))


def normalized_rows(source: Path) -> Iterator[tuple[str, str, int, int, int, int, int, str]]:
    with source.open(newline="", encoding="utf-8-sig") as handle:
        first_line = handle.readline()
        handle.seek(0)
        is_processed = "AdmissionNo" in first_line and "AttendanceStatusId" in first_line
        if is_processed:
            rows = csv.DictReader(handle)
            for row in rows:
                attendance_date = datetime.strptime(row["Date"].strip(), "%Y-%m-%d").date()
                yield (
                    attendance_date.isoformat(),
                    str(row["AdmissionNo"]).strip(),
                    _integer(row["ClassNo"]),
                    _integer(row["gradeId"]),
                    _integer(row["branchId"]),
                    _integer(row["AttendanceStatusId"]),
                    academic_year_id(attendance_date),
                    source.name,
                )
            return

        rows = csv.reader(handle)
        for row in rows:
            if len(row) != 7:
                continue
            _, raw_date, admission_no, class_no, grade_id, branch_id, status_id = row
            attendance_date = datetime.strptime(raw_date.strip(), "%Y-%m-%d").date()
            yield (
                attendance_date.isoformat(),
                admission_no.strip(),
                _integer(class_no),
                _integer(grade_id),
                _integer(branch_id),
                _integer(status_id),
                academic_year_id(attendance_date),
                source.name,
            )


def create_backup(database_url: str, backup_dir: Path, pg_dump_path: str) -> Path:
    parsed = make_url(database_url)
    if not all((parsed.username, parsed.password, parsed.host, parsed.database)):
        raise RuntimeError("DATABASE_URL must include username, password, host, and database")
    backup_dir.mkdir(parents=True, exist_ok=True)
    target = backup_dir / f"attendance_before_import_{datetime.now():%Y-%m-%d_%H-%M-%S}.dump"
    command = [
        pg_dump_path,
        "-U", parsed.username,
        "-h", parsed.host,
        "-p", str(parsed.port or 5432),
        "-F", "c",
        "-b",
        "-f", str(target),
        parsed.database,
    ]
    subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
        timeout=600,
        env={**os.environ, "PGPASSWORD": parsed.password},
    )
    if not target.is_file() or target.stat().st_size == 0:
        raise RuntimeError("Database backup verification failed")
    return target


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS attendance_report (
    id BIGSERIAL PRIMARY KEY,
    date DATE NOT NULL,
    admission_no VARCHAR(32) NOT NULL,
    class_no INTEGER,
    grade_id INTEGER,
    branch_id INTEGER,
    attendance_status_id SMALLINT NOT NULL CHECK (attendance_status_id BETWEEN 0 AND 4),
    academic_year_id SMALLINT NOT NULL,
    source_file TEXT NOT NULL,
    imported_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (date, admission_no, academic_year_id)
);
CREATE INDEX IF NOT EXISTS ix_attendance_report_year_date
    ON attendance_report (academic_year_id, date);
CREATE INDEX IF NOT EXISTS ix_attendance_report_student
    ON attendance_report (academic_year_id, admission_no);
"""


def import_source(engine, source: Path) -> int:
    columns = (
        "date", "admission_no", "class_no", "grade_id", "branch_id",
        "attendance_status_id", "academic_year_id", "source_file",
    )
    with tempfile.NamedTemporaryFile(mode="w+", newline="", encoding="utf-8") as temporary:
        writer = csv.writer(temporary)
        count = 0
        for row in normalized_rows(source):
            writer.writerow(row)
            count += 1
        temporary.flush()
        temporary.seek(0)

        raw_connection = engine.raw_connection()
        try:
            with raw_connection.cursor() as cursor:
                cursor.execute("""
                    CREATE TEMP TABLE attendance_import_stage (
                        date DATE, admission_no VARCHAR(32), class_no INTEGER,
                        grade_id INTEGER, branch_id INTEGER,
                        attendance_status_id SMALLINT, academic_year_id SMALLINT,
                        source_file TEXT
                    ) ON COMMIT DROP
                """)
                cursor.copy_expert(
                    f"COPY attendance_import_stage ({','.join(columns)}) FROM STDIN WITH (FORMAT CSV)",
                    temporary,
                )
                cursor.execute("""
                    INSERT INTO attendance_report
                        (date, admission_no, class_no, grade_id, branch_id,
                         attendance_status_id, academic_year_id, source_file)
                    SELECT date, admission_no, class_no, grade_id, branch_id,
                           attendance_status_id, academic_year_id, source_file
                    FROM attendance_import_stage
                    ON CONFLICT (date, admission_no, academic_year_id) DO UPDATE SET
                        class_no=EXCLUDED.class_no,
                        grade_id=EXCLUDED.grade_id,
                        branch_id=EXCLUDED.branch_id,
                        attendance_status_id=EXCLUDED.attendance_status_id,
                        source_file=EXCLUDED.source_file,
                        imported_at=NOW()
                """)
            raw_connection.commit()
        except Exception:
            raw_connection.rollback()
            raise
        finally:
            raw_connection.close()
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description="Create and populate attendance_report safely")
    parser.add_argument("--apply", action="store_true", help="write to PostgreSQL after a verified backup")
    parser.add_argument("--source", action="append", type=Path, dest="sources")
    args = parser.parse_args()

    sources = tuple(args.sources or DEFAULT_SOURCES)
    missing = [str(source) for source in sources if not source.is_file()]
    if missing:
        raise FileNotFoundError(f"Attendance source files not found: {', '.join(missing)}")
    counts = {str(source): sum(1 for _ in normalized_rows(source)) for source in sources}
    print(f"Validated {sum(counts.values()):,} source rows across {len(sources)} files")
    if not args.apply:
        print("Dry run complete; pass --apply to back up PostgreSQL and import")
        return

    load_dotenv(ROOT_DIR / ".env")
    database_url = os.getenv("DATABASE_URL", "")
    if not database_url:
        raise RuntimeError("DATABASE_URL is required")
    backup = create_backup(
        database_url,
        Path(os.getenv("BACKUP_DIR", ROOT_DIR / "postgres_backups")),
        os.getenv("PG_DUMP_PATH", "/opt/homebrew/bin/pg_dump"),
    )
    engine = create_engine(database_url, pool_pre_ping=True)
    try:
        with engine.begin() as connection:
            for statement in filter(str.strip, SCHEMA_SQL.split(";")):
                connection.execute(text(statement))
        imported = sum(import_source(engine, source) for source in sources)
        with engine.connect() as connection:
            stored = connection.execute(text("SELECT COUNT(*) FROM attendance_report")).scalar_one()
        print(f"Backup verified: {backup}")
        print(f"Imported {imported:,} rows; attendance_report now contains {stored:,} unique records")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
