from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
from sqlalchemy import Engine, text

from .config import Settings
from .database import create_database_engine


YEARS = ("2024-25", "2025-26", "2026-27")
YEAR_IDS = {year: index for index, year in enumerate(YEARS, start=1)}
GOOGLE_SCOPES = (
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
)

STUDENT_SOURCE_COLUMNS = (
    "sno", "adm_no", "name", "class", "gender", "mother_name", "father_name",
    "pen_number", "dob", "phone_no", "religion", "caste", "sub_caste",
    "second_lang", "remarks", "class_nos", "joined_year", "grade_id",
    "student_aadhar", "father_aadhar", "mother_aadhar", "apaar_id",
)
STUDENT_LIST_COLUMNS = (
    "adm_no", "name", "gender", "mother_name", "father_name", "pen_number",
    "dob", "phone_no", "religion", "caste", "sub_caste", "second_lang",
    "remarks", "student_aadhar", "father_aadhar", "mother_aadhar", "apaar_id",
)
STUDENTS_COLUMNS = (
    "adm_no", "class_nos", "grade_id", "academic_year_id", "status_id", "branch_id",
)
FEE_SOURCE_COLUMNS = (
    "sno", "adm_no", "student_name", "class", "gender", "fb_no", "term1", "term2",
    "term3", "term4", "total_fee_paid", "discount_concession", "exempted",
    "total_fee_due", "permissionupto", "fine", "payment_status", "classno", "acno",
    "concession_type", "staff_name",
)
FEE_COLUMNS = (
    "sno", "adm_no", "fb_no", "term1", "term2", "term3", "term4",
    "total_fee_paid", "discount_concession", "exempted", "total_fee_due", "fine",
    "classno", "staff", "staff_id", "academic_year_id", "total_fees", "payment_status_id",
)


@dataclass(frozen=True)
class SyncResult:
    students: int
    student_list: int
    fees: int


def _required_environment(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


def _service_account_client() -> gspread.Client:
    raw = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    if raw:
        try:
            account_info = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_JSON is not valid JSON") from exc
        credentials = Credentials.from_service_account_info(account_info, scopes=GOOGLE_SCOPES)
    else:
        credential_path = os.getenv("GOOGLE_JSON_STUDENT_PATH_2024_25", "").strip()
        if not credential_path:
            raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_JSON is required")
        credentials = Credentials.from_service_account_file(credential_path, scopes=GOOGLE_SCOPES)
    return gspread.authorize(credentials)


def _sheet_reference(kind: str, year: str) -> str:
    suffix = year.replace("-", "_")
    primary = f"GOOGLE_{kind}_SHEET_{suffix}"
    legacy = f"GOOGLE_SHEET_TITLE_{suffix}" if kind == "STUDENT" else f"GOOGLE_JSON_FEE_PATH_{suffix}"
    value = os.getenv(primary, os.getenv(legacy, "")).strip()
    if not value:
        raise RuntimeError(f"{primary} is required")
    return value


def _open_spreadsheet(client: gspread.Client, reference: str):
    match = re.search(r"/spreadsheets/d/([a-zA-Z0-9_-]+)", reference)
    if match:
        return client.open_by_key(match.group(1))
    if re.fullmatch(r"[a-zA-Z0-9_-]{30,}", reference):
        return client.open_by_key(reference)
    return client.open(reference)


def _worksheet_frame(client: gspread.Client, reference: str, worksheet: str) -> pd.DataFrame:
    sheet = _open_spreadsheet(client, reference).worksheet(worksheet)
    records = sheet.get_all_records(head=3, default_blank="")
    frame = pd.DataFrame(records)
    frame.columns = frame.columns.astype(str).str.strip()
    return frame


def _student_frames(client: gspread.Client) -> tuple[pd.DataFrame, pd.DataFrame]:
    unique_key = os.getenv("GOOGLE_STUDENT_UNIQUE_KEY", os.getenv("UNIQUE_KEY", "ADM_NO")).strip()
    yearly: dict[str, pd.DataFrame] = {}
    tc_lists: dict[str, set[str]] = {}

    for year in YEARS:
        reference = _sheet_reference("STUDENT", year)
        frame = _worksheet_frame(client, reference, "Overall")
        if unique_key not in frame.columns:
            raise RuntimeError(f"Student sheet {year} is missing the configured unique column")
        if len(frame.columns) != len(STUDENT_SOURCE_COLUMNS):
            raise RuntimeError(
                f"Student sheet {year} has {len(frame.columns)} columns; expected {len(STUDENT_SOURCE_COLUMNS)}"
            )
        frame = frame.dropna(subset=[unique_key]).copy()
        frame[unique_key] = frame[unique_key].astype(str).str.strip()
        frame = frame[frame[unique_key] != ""]
        frame.columns = STUDENT_SOURCE_COLUMNS
        frame["adm_no"] = frame["adm_no"].astype(str).str.strip()
        frame["grade_id"] = pd.to_numeric(frame["grade_id"], errors="coerce")
        frame["academic_year"] = year
        yearly[year] = frame

        if year != YEARS[-1]:
            try:
                tc_frame = _worksheet_frame(client, reference, os.getenv("TC_APPLIED_SHEET_NAME", "TC LIST"))
                tc_column = unique_key if unique_key in tc_frame.columns else tc_frame.columns[0]
                tc_lists[year] = set(tc_frame[tc_column].dropna().astype(str).str.strip())
            except gspread.WorksheetNotFound:
                tc_lists[year] = set()

    for index, year in enumerate(YEARS):
        current = yearly[year]
        current_codes = set(current["adm_no"])
        previous_codes = set(yearly[YEARS[index - 1]]["adm_no"]) if index else set()
        next_codes = set(yearly[YEARS[index + 1]]["adm_no"]) if index < len(YEARS) - 1 else set()
        left_codes = current_codes - next_codes if next_codes else set()
        new_codes = current_codes - previous_codes if previous_codes else set()
        graduate_codes: set[str] = set()
        if next_codes and current["grade_id"].notna().any():
            maximum_grade = current["grade_id"].max()
            graduate_codes = set(
                current.loc[(current["grade_id"] == maximum_grade) & current["adm_no"].isin(left_codes), "adm_no"]
            )

        def status_for(admission_number: str) -> int:
            if admission_number in tc_lists.get(year, set()):
                return 5
            if admission_number in graduate_codes:
                return 4
            if admission_number in new_codes:
                return 3
            if admission_number in left_codes:
                return 2
            return 1

        current["status_id"] = current["adm_no"].map(status_for)

    combined = pd.concat([yearly[year] for year in YEARS], ignore_index=True)
    combined["gender"] = combined["gender"].astype(str).str.upper().str.strip()
    combined["dob"] = pd.to_datetime(combined["dob"], dayfirst=True, errors="coerce").dt.date
    combined["academic_year_id"] = combined["academic_year"].map(YEAR_IDS)
    combined["branch_id"] = 3
    combined.loc[combined["grade_id"].between(1, 3), "branch_id"] = 1
    combined.loc[combined["grade_id"].between(4, 8), "branch_id"] = 2

    students = combined.loc[:, STUDENTS_COLUMNS].copy()
    students["grade_id"] = students["grade_id"].astype("Int64").astype(str).replace("<NA>", None)
    students = students.drop_duplicates(subset=["adm_no", "academic_year_id"], keep="last")

    master = combined.sort_values(
        ["academic_year_id", "adm_no"], ascending=[False, True]
    ).drop_duplicates(subset=["adm_no"], keep="first")
    student_list = master.loc[:, STUDENT_LIST_COLUMNS].copy()
    return student_list, students


def _fee_frame(client: gspread.Client) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for year in YEARS:
        reference = _sheet_reference("FEE", year)
        frame = _worksheet_frame(client, reference, "Overall Sheet")
        if len(frame.columns) != len(FEE_SOURCE_COLUMNS):
            raise RuntimeError(
                f"Fee sheet {year} has {len(frame.columns)} columns; expected {len(FEE_SOURCE_COLUMNS)}"
            )
        frame.columns = FEE_SOURCE_COLUMNS
        frame["academic_year_id"] = YEAR_IDS[year]
        frames.append(frame)

    fees = pd.concat(frames, ignore_index=True)
    fees["adm_no"] = fees["adm_no"].astype(str).str.strip()
    fees["student_name"] = fees["student_name"].astype(str).str.strip()
    fees = fees[(fees["adm_no"] != "") & (fees["student_name"] != "")].copy()
    numeric_columns = (
        "term1", "term2", "term3", "term4", "total_fee_paid", "discount_concession",
        "exempted", "total_fee_due", "fine",
    )
    for column in numeric_columns:
        fees[column] = pd.to_numeric(fees[column], errors="coerce").fillna(0)
    fees["classno"] = pd.to_numeric(fees["classno"], errors="coerce").astype("Int64")
    fees["payment_status"] = fees["payment_status"].fillna("Unknown").astype(str).str.strip().replace("", "Unknown")
    payment_statuses = {value: index for index, value in enumerate(sorted(fees["payment_status"].unique()), start=1)}
    fees["payment_status_id"] = fees["payment_status"].map(payment_statuses)
    fees["staff_name"] = fees["staff_name"].fillna("").astype(str).str.strip()
    staff_names = sorted(value for value in fees["staff_name"].unique() if value)
    staff_ids = {value: index for index, value in enumerate(staff_names, start=1)}
    fees["staff"] = (fees["staff_name"] != "").astype(int)
    fees["staff_id"] = fees["staff_name"].map(staff_ids).astype("Int64")
    fees["total_fees"] = (
        fees["total_fee_paid"] + fees["discount_concession"] + fees["total_fee_due"] + fees["exempted"]
    ).round().astype(int)
    fees = fees.drop_duplicates(subset=["adm_no", "academic_year_id"], keep="last")
    fees = fees.sort_values(["academic_year_id", "classno", "adm_no"], na_position="last")
    fees["sno"] = range(1, len(fees) + 1)
    return fees.loc[:, FEE_COLUMNS].copy()


def _validate(student_list: pd.DataFrame, students: pd.DataFrame, fees: pd.DataFrame) -> None:
    minimum_rows = int(os.getenv("GOOGLE_SYNC_MIN_ROWS", "10"))
    for name, frame in (("student_list", student_list), ("students", students), ("fees", fees)):
        if len(frame) < minimum_rows:
            raise RuntimeError(f"Refusing to sync {name}: only {len(frame)} rows were produced")
    if students["adm_no"].isna().any() or fees["adm_no"].isna().any():
        raise RuntimeError("Refusing to sync rows with missing admission numbers")
    expected_years = set(YEAR_IDS.values())
    if set(students["academic_year_id"].unique()) != expected_years:
        raise RuntimeError("Student output does not contain every configured academic year")
    if set(fees["academic_year_id"].unique()) != expected_years:
        raise RuntimeError("Fee output does not contain every configured academic year")


def _clean_for_sql(frame: pd.DataFrame) -> pd.DataFrame:
    return frame.astype(object).where(pd.notna(frame), None)


def _replace_database(engine: Engine, student_list: pd.DataFrame, students: pd.DataFrame, fees: pd.DataFrame) -> None:
    master_columns = ", ".join(STUDENT_LIST_COLUMNS)
    master_updates = ", ".join(
        f"{column} = COALESCE(EXCLUDED.{column}, student_list.{column})"
        for column in STUDENT_LIST_COLUMNS if column != "adm_no"
    )
    with engine.begin() as connection:
        locked = connection.execute(text("SELECT pg_try_advisory_xact_lock(73194211)")).scalar_one()
        if not locked:
            raise RuntimeError("Another Google Sheets sync is already running")

        _clean_for_sql(student_list).to_sql("sync_student_list_staging", connection, if_exists="replace", index=False, method="multi", chunksize=500)
        _clean_for_sql(students).to_sql("sync_students_staging", connection, if_exists="replace", index=False, method="multi", chunksize=500)
        _clean_for_sql(fees).to_sql("sync_fees_staging", connection, if_exists="replace", index=False, method="multi", chunksize=500)

        connection.execute(text(f"""
            INSERT INTO student_list ({master_columns})
            SELECT {master_columns} FROM sync_student_list_staging
            ON CONFLICT (adm_no) DO UPDATE SET {master_updates}
        """))
        connection.execute(text("DELETE FROM students WHERE academic_year_id = ANY(:year_ids)"), {"year_ids": list(YEAR_IDS.values())})
        connection.execute(text(f"INSERT INTO students ({', '.join(STUDENTS_COLUMNS)}) SELECT {', '.join(STUDENTS_COLUMNS)} FROM sync_students_staging"))
        connection.execute(text("DELETE FROM fees_table WHERE academic_year_id = ANY(:year_ids)"), {"year_ids": list(YEAR_IDS.values())})
        connection.execute(text(f"INSERT INTO fees_table ({', '.join(FEE_COLUMNS)}) SELECT {', '.join(FEE_COLUMNS)} FROM sync_fees_staging"))
        connection.execute(text("SELECT setval(pg_get_serial_sequence('students','id'), COALESCE(MAX(id), 1), MAX(id) IS NOT NULL) FROM students"))
        connection.execute(text("SELECT setval(pg_get_serial_sequence('fees_table','sno'), COALESCE(MAX(sno), 1), MAX(sno) IS NOT NULL) FROM fees_table"))
        connection.execute(text("DROP TABLE sync_student_list_staging, sync_students_staging, sync_fees_staging"))


def run_sync(*, dry_run: bool = False) -> SyncResult:
    started_at = datetime.now(timezone.utc)
    client = _service_account_client()
    student_list, students = _student_frames(client)
    fees = _fee_frame(client)
    _validate(student_list, students, fees)
    result = SyncResult(students=len(students), student_list=len(student_list), fees=len(fees))
    if not dry_run:
        settings = Settings()
        settings.validate()
        engine = create_database_engine(settings.database_url)
        try:
            _replace_database(engine, student_list, students, fees)
        finally:
            engine.dispose()
    elapsed = (datetime.now(timezone.utc) - started_at).total_seconds()
    print(
        f"Google Sheets sync {'validated' if dry_run else 'completed'}: "
        f"students={result.students}, student_list={result.student_list}, fees={result.fees}, "
        f"elapsed_seconds={elapsed:.1f}"
    )
    return result


def main(argv: Iterable[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Synchronize validated Google Sheets data to PostgreSQL")
    parser.add_argument("--dry-run", action="store_true", help="Fetch and validate without changing PostgreSQL")
    arguments = parser.parse_args(list(argv) if argv is not None else None)
    run_sync(dry_run=arguments.dry_run)


if __name__ == "__main__":
    main()
