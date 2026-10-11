from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("ADMIN_API_KEY", "import-admin-key")
os.environ.setdefault("VIEWER_API_KEY", "import-viewer-key")

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from web_api.config import Settings
from web_api.main import create_app


def build_client(tmp_path: Path) -> TestClient:
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE students (id INTEGER PRIMARY KEY, adm_no TEXT, class_nos TEXT, grade_id TEXT, academic_year_id INTEGER, status_id INTEGER, branch_id INTEGER)"))
        connection.execute(text("CREATE TABLE fees_table (sno INTEGER PRIMARY KEY, adm_no TEXT, total_fee_paid NUMERIC, total_fee_due NUMERIC, discount_concession NUMERIC, total_fees NUMERIC, academic_year_id INTEGER)"))
        connection.execute(text('CREATE TABLE daywise_fees_collection ("SNo" TEXT, "AdmissionNo" TEXT, "Date" TEXT, "ReceivedAmount" NUMERIC, academic_year_id INTEGER, account_name TEXT, payment_mode TEXT)'))
        connection.execute(text("CREATE TABLE fee_concession_report (id INTEGER PRIMARY KEY, date TEXT, student_number TEXT, discount_given NUMERIC, academic_year_id INTEGER)"))
        connection.execute(text("CREATE TABLE atom_missing_records (id INTEGER PRIMARY KEY, admission_no TEXT, amount NUMERIC, net_amount_to_be_paid NUMERIC, txn_date TEXT, settlement_date TEXT, description TEXT)"))
        connection.execute(text("CREATE TABLE attendance_report (id INTEGER PRIMARY KEY, date TEXT, admission_no TEXT, class_no INTEGER, grade_id INTEGER, branch_id INTEGER, attendance_status_id INTEGER, academic_year_id INTEGER, source_file TEXT)"))
        connection.execute(text("INSERT INTO students VALUES (1,'KSS00123','10','10',3,1,1),(2,'KSS00456','9','9',3,3,1)"))
        connection.execute(text("INSERT INTO fees_table VALUES (1,'KSS00123',10000,2000,500,12500,3)"))
        connection.execute(text("INSERT INTO daywise_fees_collection VALUES ('R1','KSS00123','2026-10-10',10000,3,'School fee','Online')"))
        connection.execute(text("INSERT INTO fee_concession_report VALUES (1,'2026-10-09','KSS00123',500,3)"))
        connection.execute(text("INSERT INTO atom_missing_records VALUES (1,'KSS00456',2000,1980,'2026-10-10','2026-10-11','SUCCESS')"))
        connection.execute(text("INSERT INTO attendance_report VALUES (1,'2026-10-10','KSS00123',1,10,1,2,3,'test.csv'),(2,'2026-10-10','KSS00456',2,9,1,1,3,'test.csv'),(3,'2026-10-11','KSS00123',1,10,1,2,3,'test.csv'),(4,'2026-10-11','KSS00456',2,9,1,1,3,'test.csv')"))
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        environment="test",
        admin_api_key="admin-test-key",
        viewer_api_key="viewer-test-key",
        auth_disabled=False,
        allowed_origins=["http://testserver"],
        enable_pipeline_execution=False,
    )
    return TestClient(create_app(settings=settings, engine=engine))


def test_authentication_required(tmp_path: Path):
    with build_client(tmp_path) as client:
        response = client.get("/api/overview")
        assert response.status_code == 401


def test_overview_uses_live_aggregates(tmp_path: Path):
    with build_client(tmp_path) as client:
        response = client.get("/api/overview?academic_year_id=3", headers={"X-API-Key": "viewer-test-key"})
        assert response.status_code == 200
        payload = response.json()
        assert payload["students"] == 2
        assert payload["fees_collected"] == 10000
        assert payload["pending_fees"] == 2000
        assert payload["attendance_available"] is True
        assert payload["attendance_percent"] == 50


def test_students_are_masked(tmp_path: Path):
    with build_client(tmp_path) as client:
        response = client.get("/api/students", headers={"X-API-Key": "viewer-test-key"})
        assert response.status_code == 200
        payload = response.json()
        assert payload["items"][0]["admission_no"] == "ADM•••0123"
        assert "KSS00123" not in response.text


def test_viewer_cannot_refresh(tmp_path: Path):
    with build_client(tmp_path) as client:
        response = client.post("/api/refresh/students", headers={"X-API-Key": "viewer-test-key"})
        assert response.status_code == 403


def test_disabled_refresh_is_safe(tmp_path: Path):
    with build_client(tmp_path) as client:
        response = client.post("/api/refresh/students", headers={"X-API-Key": "admin-test-key"})
        assert response.status_code == 503
        assert "disabled" in response.json()["detail"].lower()


def test_attendance_uses_present_status_two_and_masks_students(tmp_path: Path):
    with build_client(tmp_path) as client:
        response = client.get("/api/attendance?academic_year_id=3", headers={"X-API-Key": "viewer-test-key"})
        assert response.status_code == 200
        payload = response.json()
        assert payload["attendance_percent"] == 50
        assert payload["latest_attendance_percent"] == 50
        assert payload["latest_date"] == "2026-10-11"
        assert payload["low_attendance"][0]["admission_no"].startswith("ADM•••")
        assert "KSS00456" not in response.text


def test_health_reports_missing_database_configuration():
    settings = Settings(
        database_url="",
        environment="production",
        admin_api_key="admin-test-key",
        viewer_api_key="viewer-test-key",
    )

    with TestClient(create_app(settings=settings)) as client:
        response = client.get("/health")

    assert response.status_code == 503
    assert response.json() == {
        "status": "configuration_error",
        "detail": "DATABASE_URL is required",
    }
