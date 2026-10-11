from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Engine, inspect, text


YEAR_LABELS = {1: "2024-25", 2: "2025-26", 3: "2026-27"}


def _scalar(engine: Engine, statement: str, params: dict[str, Any] | None = None, default: Any = 0) -> Any:
    with engine.connect() as connection:
        value = connection.execute(text(statement), params or {}).scalar()
    return default if value is None else value


def _rows(engine: Engine, statement: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    with engine.connect() as connection:
        return [dict(row) for row in connection.execute(text(statement), params or {}).mappings()]


def _tables(engine: Engine) -> set[str]:
    return set(inspect(engine).get_table_names())


def _number(value: Any) -> float:
    if isinstance(value, Decimal):
        return float(value)
    return float(value or 0)


def mask_identifier(value: Any) -> str:
    text_value = str(value or "").strip()
    if not text_value:
        return "—"
    return f"ADM•••{text_value[-4:]}"


def serialize_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def overview(engine: Engine, academic_year_id: int) -> dict[str, Any]:
    tables = _tables(engine)
    student_count = _scalar(
        engine,
        "SELECT COUNT(*) FROM students WHERE academic_year_id=:year",
        {"year": academic_year_id},
    ) if "students" in tables else 0
    fee_row = {"collected": 0, "pending": 0, "concessions": 0, "expected": 0}
    if "fees_table" in tables:
        fee_row = _rows(
            engine,
            """
            SELECT COALESCE(SUM(total_fee_paid),0) AS collected,
                   COALESCE(SUM(total_fee_due),0) AS pending,
                   COALESCE(SUM(discount_concession),0) AS concessions,
                   COALESCE(SUM(total_fees),0) AS expected
            FROM fees_table WHERE academic_year_id=:year
            """,
            {"year": academic_year_id},
        )[0]
    unmatched = _scalar(engine, "SELECT COUNT(*) FROM atom_missing_records") if "atom_missing_records" in tables else 0
    attendance = attendance_summary(engine, academic_year_id)
    return {
        "academic_year_id": academic_year_id,
        "academic_year": YEAR_LABELS.get(academic_year_id, str(academic_year_id)),
        "students": int(student_count),
        "fees_collected": _number(fee_row["collected"]),
        "pending_fees": _number(fee_row["pending"]),
        "concessions": _number(fee_row["concessions"]),
        "expected_fees": _number(fee_row["expected"]),
        "attendance_percent": attendance["attendance_percent"],
        "attendance_available": attendance["available"],
        "unmatched_transactions": int(unmatched),
    }


def students(
    engine: Engine,
    academic_year_id: int,
    search: str,
    grade_id: str | None,
    status_id: int | None,
    limit: int,
    offset: int,
    reveal_identity: bool = False,
) -> dict[str, Any]:
    params: dict[str, Any] = {"year": academic_year_id, "limit": limit, "offset": offset}
    clauses = ["s.academic_year_id=:year"]
    if search:
        searchable = ["LOWER(s.adm_no) LIKE :search", "LOWER(COALESCE(s.grade_id,'')) LIKE :search"]
        if reveal_identity:
            searchable.append("LOWER(COALESCE(sl.name,'')) LIKE :search")
        clauses.append(f"({' OR '.join(searchable)})")
        params["search"] = f"%{search.lower()}%"
    if grade_id:
        clauses.append("s.grade_id=:grade")
        params["grade"] = grade_id
    if status_id is not None:
        clauses.append("s.status_id=:status")
        params["status"] = status_id
    where = " AND ".join(clauses)
    total = _scalar(
        engine,
        f"SELECT COUNT(*) FROM students s LEFT JOIN student_list sl ON sl.adm_no=s.adm_no WHERE {where}",
        params,
    )
    rows = _rows(
        engine,
        f"""
        SELECT s.adm_no, sl.name, s.class_nos, s.grade_id, s.status_id, s.branch_id
        FROM students s
        LEFT JOIN student_list sl ON sl.adm_no=s.adm_no
        WHERE {where}
        ORDER BY s.grade_id, s.adm_no LIMIT :limit OFFSET :offset
        """,
        params,
    )
    status_labels = {1: "Continuing", 2: "Left", 3: "New", 4: "Alumni", 5: "TC applied"}
    items = [
        {
            "admission_no": row["adm_no"] if reveal_identity else mask_identifier(row["adm_no"]),
            "student": (row["name"] or "—") if reveal_identity else f"Student {str(row['adm_no'])[-4:]}",
            "class_nos": row["class_nos"],
            "grade": row["grade_id"],
            "status_id": row["status_id"],
            "status": status_labels.get(row["status_id"], "Unknown"),
            "branch_id": row["branch_id"],
        }
        for row in rows
    ]
    return {
        "total": int(total),
        "limit": limit,
        "offset": offset,
        "identity_visible": reveal_identity,
        "items": items,
    }


def fees(engine: Engine, academic_year_id: int, limit: int = 20) -> dict[str, Any]:
    summary = overview(engine, academic_year_id)
    items: list[dict[str, Any]] = []
    if "daywise_fees_collection" in _tables(engine):
        rows = _rows(
            engine,
            """
            SELECT "SNo" AS receipt, "AdmissionNo" AS admission_no, "Date" AS payment_date,
                   "ReceivedAmount" AS amount, account_name, payment_mode
            FROM daywise_fees_collection
            WHERE academic_year_id=:year ORDER BY "Date" DESC NULLS LAST LIMIT :limit
            """ if engine.dialect.name != "sqlite" else """
            SELECT "SNo" AS receipt, "AdmissionNo" AS admission_no, "Date" AS payment_date,
                   "ReceivedAmount" AS amount, account_name, payment_mode
            FROM daywise_fees_collection
            WHERE academic_year_id=:year ORDER BY "Date" DESC LIMIT :limit
            """,
            {"year": academic_year_id, "limit": limit},
        )
        items = [
            {
                "receipt": row["receipt"],
                "admission_no": mask_identifier(row["admission_no"]),
                "payment_date": serialize_value(row["payment_date"]),
                "amount": _number(row["amount"]),
                "account_name": row["account_name"],
                "payment_mode": row["payment_mode"],
            }
            for row in rows
        ]
    return {"summary": summary, "recent_payments": items}


def attendance_summary(engine: Engine, academic_year_id: int) -> dict[str, Any]:
    if "attendance_report" not in _tables(engine):
        return {"available": False, "attendance_percent": None, "present": 0, "absent": 0, "total": 0, "by_grade": [], "low_attendance": [], "latest_date": None, "latest_attendance_percent": None}
    columns = {column["name"] for column in inspect(engine).get_columns("attendance_report")}
    status_column = "attendance_status_id" if "attendance_status_id" in columns else "attendancestatusid"
    admission_column = "admission_no" if "admission_no" in columns else "admissionno"
    grade_column = "grade_id" if "grade_id" in columns else "gradeid"
    year_filter = " WHERE academic_year_id=:year" if "academic_year_id" in columns else ""
    params = {"year": academic_year_id} if year_filter else {}
    row = _rows(
        engine,
        f"""
        SELECT SUM(CASE WHEN {status_column}=2 THEN 1 ELSE 0 END) AS present,
               SUM(CASE WHEN {status_column}=1 THEN 1 ELSE 0 END) AS absent
        FROM attendance_report{year_filter}
        """,
        params,
    )[0]
    present, absent = int(row["present"] or 0), int(row["absent"] or 0)
    total = present + absent
    latest_date = _scalar(
        engine,
        f"SELECT MAX(date) FROM attendance_report{year_filter}",
        params,
        None,
    )
    latest_present = latest_absent = 0
    by_grade: list[dict[str, Any]] = []
    if latest_date is not None:
        latest = _rows(
            engine,
            f"""
            SELECT SUM(CASE WHEN {status_column}=2 THEN 1 ELSE 0 END) AS present,
                   SUM(CASE WHEN {status_column}=1 THEN 1 ELSE 0 END) AS absent
            FROM attendance_report
            WHERE date=:latest_date{" AND academic_year_id=:year" if "academic_year_id" in columns else ""}
            """,
            {**params, "latest_date": latest_date},
        )[0]
        latest_present, latest_absent = int(latest["present"] or 0), int(latest["absent"] or 0)
        grade_rows = _rows(
            engine,
            f"""
            SELECT {grade_column} AS grade,
                   SUM(CASE WHEN {status_column}=2 THEN 1 ELSE 0 END) AS present,
                   SUM(CASE WHEN {status_column}=1 THEN 1 ELSE 0 END) AS absent
            FROM attendance_report
            WHERE date=:latest_date{" AND academic_year_id=:year" if "academic_year_id" in columns else ""}
            GROUP BY {grade_column} ORDER BY {grade_column}
            """,
            {**params, "latest_date": latest_date},
        )
        by_grade = [
            {
                "grade": grade["grade"],
                "attendance_percent": round(int(grade["present"] or 0) / max(int(grade["present"] or 0) + int(grade["absent"] or 0), 1) * 100, 2),
            }
            for grade in grade_rows
            if int(grade["present"] or 0) + int(grade["absent"] or 0) > 0
        ]
    low_rows = _rows(
        engine,
        f"""
        SELECT {admission_column} AS admission_no, {grade_column} AS grade,
               SUM(CASE WHEN {status_column}=2 THEN 1 ELSE 0 END) AS present,
               SUM(CASE WHEN {status_column}=1 THEN 1 ELSE 0 END) AS absent
        FROM attendance_report{year_filter}
        GROUP BY {admission_column}, {grade_column}
        HAVING SUM(CASE WHEN {status_column} IN (1,2) THEN 1 ELSE 0 END) > 0
           AND (100.0 * SUM(CASE WHEN {status_column}=2 THEN 1 ELSE 0 END) /
                SUM(CASE WHEN {status_column} IN (1,2) THEN 1 ELSE 0 END)) < 75
        ORDER BY (100.0 * SUM(CASE WHEN {status_column}=2 THEN 1 ELSE 0 END) /
                  SUM(CASE WHEN {status_column} IN (1,2) THEN 1 ELSE 0 END)) ASC
        LIMIT 50
        """,
        params,
    )
    low_attendance = []
    for student in low_rows:
        student_present, student_absent = int(student["present"] or 0), int(student["absent"] or 0)
        low_attendance.append({
            "admission_no": mask_identifier(student["admission_no"]),
            "grade": student["grade"],
            "present": student_present,
            "absent": student_absent,
            "attendance_percent": round(student_present / (student_present + student_absent) * 100, 2),
        })
    latest_total = latest_present + latest_absent
    return {
        "available": True,
        "attendance_percent": round((present / total * 100), 2) if total else None,
        "present": present,
        "absent": absent,
        "total": total,
        "latest_date": serialize_value(latest_date),
        "latest_attendance_percent": round(latest_present / latest_total * 100, 2) if latest_total else None,
        "by_grade": by_grade,
        "low_attendance": low_attendance,
    }


def concessions(engine: Engine, academic_year_id: int, limit: int = 50) -> dict[str, Any]:
    if "fee_concession_report" not in _tables(engine):
        return {"total_amount": 0, "beneficiaries": 0, "items": []}
    summary = _rows(
        engine,
        """
        SELECT COALESCE(SUM(discount_given),0) AS total_amount,
               COUNT(DISTINCT student_number) AS beneficiaries
        FROM fee_concession_report WHERE academic_year_id=:year
        """,
        {"year": academic_year_id},
    )[0]
    rows = _rows(
        engine,
        """
        SELECT date, student_number, discount_given, academic_year_id
        FROM fee_concession_report WHERE academic_year_id=:year
        ORDER BY date DESC LIMIT :limit
        """,
        {"year": academic_year_id, "limit": limit},
    )
    return {
        "total_amount": _number(summary["total_amount"]),
        "beneficiaries": int(summary["beneficiaries"] or 0),
        "items": [
            {
                "date": serialize_value(row["date"]),
                "student_number": mask_identifier(row["student_number"]),
                "discount_given": _number(row["discount_given"]),
                "academic_year_id": row["academic_year_id"],
            }
            for row in rows
        ],
    }


def unmatched_transactions(engine: Engine, limit: int = 50) -> dict[str, Any]:
    if "atom_missing_records" not in _tables(engine):
        return {"total": 0, "amount": 0, "items": []}
    summary = _rows(
        engine,
        "SELECT COUNT(*) AS total, COALESCE(SUM(amount),0) AS amount FROM atom_missing_records",
    )[0]
    rows = _rows(
        engine,
        """
        SELECT id, admission_no, amount, net_amount_to_be_paid, txn_date,
               settlement_date, description FROM atom_missing_records
        ORDER BY txn_date DESC LIMIT :limit
        """,
        {"limit": limit},
    )
    return {
        "total": int(summary["total"] or 0),
        "amount": _number(summary["amount"]),
        "items": [
            {
                "transaction": f"AT•••{str(row['id']).zfill(5)}",
                "admission_no": mask_identifier(row["admission_no"]),
                "amount": _number(row["amount"]),
                "net_amount_to_be_paid": _number(row["net_amount_to_be_paid"]),
                "txn_date": serialize_value(row["txn_date"]),
                "settlement_date": serialize_value(row["settlement_date"]),
                "description": row["description"],
            }
            for row in rows
        ],
    }


def pipeline_status(engine: Engine) -> dict[str, Any]:
    table_map = {
        "students": "students",
        "fees": "fees_table",
        "daywise": "daywise_fees_collection",
        "concessions": "fee_concession_report",
        "transactions": "atom_transaction_report",
        "attendance": "attendance_report",
    }
    existing = _tables(engine)
    items = []
    for pipeline, table in table_map.items():
        available = table in existing
        count = _scalar(engine, f'SELECT COUNT(*) FROM "{table}"') if available else 0
        items.append({"pipeline": pipeline, "table": table, "available": available, "record_count": int(count)})
    return {"items": items}


def audit_entries(engine: Engine, limit: int = 50) -> list[dict[str, Any]]:
    if "pipeline_audit_log" not in _tables(engine):
        return []
    rows = _rows(
        engine,
        """
        SELECT id, pipeline, status, requested_by, started_at, finished_at, record_count, message
        FROM pipeline_audit_log ORDER BY id DESC LIMIT :limit
        """,
        {"limit": limit},
    )
    return [{key: serialize_value(value) for key, value in row.items()} for row in rows]

