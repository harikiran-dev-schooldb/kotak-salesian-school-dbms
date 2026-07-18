# %% [markdown]
# <h1 align="center"><b>KOTAK SALESIAN SCHOOL</b></h1>
# 

# %% [markdown]
# <h2 align="center"><b>STUDENTS DATABASE MANAGEMENT</b></h2>

# %% [markdown]
# ## **Import Required Libraries**

# %%
import os
import glob
import pandas as pd
import numpy as np
import sys
import datetime
import subprocess
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
import urllib.parse
from dotenv import load_dotenv
import warnings
from bs4 import BeautifulSoup
import requests
import logging
from io import StringIO
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time

# ================= ENV =================
load_dotenv()

# %% [markdown]
# ## **Backup Files Before running New**

# %%
BASE_DIR = os.getenv("BASE_DIR")
if not BASE_DIR:
    raise ValueError("❌ BASE_DIR not found in .env")

OUTPUT_DIR = os.path.join(BASE_DIR, "output_data")
os.makedirs(OUTPUT_DIR, exist_ok=True)

SOURCE_DIR = os.path.join(BASE_DIR, "source_data")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# PostgreSQL Credentials
POSTGRES_CREDENTIALS = {
    "username": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
    "database": os.getenv("DB_NAME"),
}

password = urllib.parse.quote(POSTGRES_CREDENTIALS["password"])
conn_url = (
    f"postgresql+psycopg2://{POSTGRES_CREDENTIALS['username']}:{password}"
    f"@{POSTGRES_CREDENTIALS['host']}:{POSTGRES_CREDENTIALS['port']}/"
    f"{POSTGRES_CREDENTIALS['database']}"
)

engine = create_engine(conn_url)

# Backup Config
BACKUP_DIR = os.getenv("BACKUP_DIR")
DB_DUMP_PATH = os.getenv("PG_DUMP_PATH")

print("Using BACKUP_DIR:", BACKUP_DIR)
print("Using DB_DUMP_PATH:", DB_DUMP_PATH)

# ✅ Ensure backup directory exists
os.makedirs(BACKUP_DIR, exist_ok=True)

# ✅ DELETE PREVIOUS BACKUPS
old_backups = glob.glob(os.path.join(BACKUP_DIR, "*.sql"))

for file in old_backups:
    try:
        os.remove(file)
        print(f"🗑️ Deleted old backup: {file}")
    except Exception as e:
        print(f"⚠️ Unable to delete {file}: {e}")

# ✅ Generate new backup filename
timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
backup_file = os.path.join(
    BACKUP_DIR,
    f"backup_{POSTGRES_CREDENTIALS['database']}_{timestamp}.sql"
)

print(POSTGRES_CREDENTIALS)

# ✅ Run pg_dump
try:
    result = subprocess.run(
    [
        DB_DUMP_PATH,
        "-U", POSTGRES_CREDENTIALS["username"],
        "-h", POSTGRES_CREDENTIALS["host"],
        "-p", POSTGRES_CREDENTIALS["port"],
        "-F", "c",
        "-b",
        "-f", backup_file,
        POSTGRES_CREDENTIALS["database"],
    ],
    env={**os.environ, "PGPASSWORD": POSTGRES_CREDENTIALS["password"]},
    stdout=subprocess.DEVNULL,
    stderr=subprocess.PIPE,
    text=True,
    shell=True
)


    if result.returncode == 0:
        print(f"✅ Backup successful: {backup_file}")
    else:
        print(f"❌ Backup failed!\nError: {result.stderr}")

except FileNotFoundError:
    print(f"⚠️ pg_dump not found at {DB_DUMP_PATH}.")
except Exception as e:
    print(f"⚠️ An unexpected error occurred: {e}")


# %% [markdown]
# <h2 align="center"><b>STUDENT DETAILS</b></h2>

# %% [markdown]
# ## **Import Libraries & Define Credentials**

# %%
from datetime import date, datetime, timedelta
# * Google Sheets Config (from .env)
GOOGLE_JSON_STUDENT_PATHS = {
    "2024-25": os.getenv("GOOGLE_JSON_STUDENT_PATH_2024_25"),
    "2025-26": os.getenv("GOOGLE_JSON_STUDENT_PATH_2025_26"),
    "2026-27": os.getenv("GOOGLE_JSON_STUDENT_PATH_2026_27")
}

GOOGLE_SHEET_TITLES = {
    "2024-25": os.getenv("GOOGLE_SHEET_TITLE_2024_25"),
    "2025-26": os.getenv("GOOGLE_SHEET_TITLE_2025_26"),
    "2026-27": os.getenv("GOOGLE_SHEET_TITLE_2026_27")
}

UNIQUE_KEY = os.getenv("UNIQUE_KEY")


# * Table names
TABLE_NAME1 = "students"
TABLE_NAME2 = "student_list"

# %% [markdown]
# ## **Extract Data from Google Sheet**

# %%
# === FETCH GOOGLE SHEET ===
def fetch_data(sheet_title, worksheet_name="Overall", json_path=None):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(json_path, scope)
    client = gspread.authorize(creds)
    spreadsheet = client.open(sheet_title)
    sheet = spreadsheet.worksheet(worksheet_name)
    data = sheet.get_all_records(head=3)
    return pd.DataFrame(data)

# === CLEAN COLUMN NAMES ===
def clean_column_names(df):
    df.columns = df.columns.str.strip()
    return df

# %%
TC_APPLIED_SHEET_NAME = "TC LIST"

STATUS_CONTINUING = 1
STATUS_LEFT = 2
STATUS_NEW = 3
STATUS_ALUMNI = 4
STATUS_TC_APPLIED = 5


def get_status(adm_no, tc_set, graduate_set, left_set, new_set):
    if adm_no in tc_set:
        return STATUS_TC_APPLIED
    if adm_no in graduate_set:
        return STATUS_ALUMNI
    if adm_no in new_set:
        return STATUS_NEW
    if adm_no in left_set:
        return STATUS_LEFT
    return STATUS_CONTINUING


def load_student_year(year):
    df = clean_column_names(
        fetch_data(
            GOOGLE_SHEET_TITLES[year],
            "Overall",
            GOOGLE_JSON_STUDENT_PATHS[year],
        )
    )

    df.dropna(subset=[UNIQUE_KEY], inplace=True)
    df[UNIQUE_KEY] = df[UNIQUE_KEY].astype(str).str.strip()
    df["GRADES"] = pd.to_numeric(df["GRADES"], errors="coerce")
    df["academic_year"] = year

    return df


def load_tc_year(year):
    try:
        df = clean_column_names(
            fetch_data(
                GOOGLE_SHEET_TITLES[year],
                TC_APPLIED_SHEET_NAME,
                GOOGLE_JSON_STUDENT_PATHS[year],
            )
        )

        return set(
            df[UNIQUE_KEY]
            .dropna()
            .astype(str)
            .str.strip()
        )

    except Exception:
        return set()


def merge_and_tag():

    years = ["2024-25", "2025-26", "2026-27"]

    students = {year: load_student_year(year) for year in years}

    tc_lists = {
        year: load_tc_year(year)
        for year in years[:-1]
    }

    # -----------------------------
    # Calculate Status Year by Year
    # -----------------------------
    for i, year in enumerate(years):

        current = students[year]
        current_codes = set(current[UNIQUE_KEY])

        previous_codes = (
            set(students[years[i - 1]][UNIQUE_KEY])
            if i > 0
            else set()
        )

        next_codes = (
            set(students[years[i + 1]][UNIQUE_KEY])
            if i < len(years) - 1
            else set()
        )

        tc_set = tc_lists.get(year, set())

        left_set = current_codes - next_codes if next_codes else set()
        new_set = current_codes - previous_codes if previous_codes else set()

        graduate_set = set()

        if next_codes:
            max_grade = current["GRADES"].max()

            graduate_set = set(
                current[
                    (current["GRADES"] == max_grade)
                    & (current[UNIQUE_KEY].isin(left_set))
                ][UNIQUE_KEY]
            )

        current["status_id"] = current[UNIQUE_KEY].apply(
            lambda adm: get_status(
                adm,
                tc_set,
                graduate_set,
                left_set,
                new_set,
            )
        )

    return pd.concat(
        [students[y] for y in years],
        ignore_index=True,
    )

# %%
def clean_data(df):
    df = df.copy()

    # ✨ Rename columns to match your database structure
    df.columns = [
        "sno", "adm_no", "name", "class", "gender", "mother_name", "father_name",
        "pen_number", "dob", "phone_no", "religion", "caste", "sub_caste",
        "second_lang", "remarks", "class_nos", "joined_year", "grade_id","student_aadhar", "father_aadhar", "mother_aadhar","apaar_id",
        "academic_year", "status_id"
    ]

    # Lowercase and strip spaces for consistency
    df.columns = df.columns.str.strip().str.lower()

    # 🗓️ Convert DOB to PostgreSQL-friendly format
    df["dob"] = pd.to_datetime(df["dob"], format="%d-%m-%Y", errors='coerce').dt.strftime("%Y-%m-%d")

    # 🔢 Convert joined_year to integer
    df["joined_year"] = pd.to_numeric(df["joined_year"], errors="coerce").astype("Int64")

    # 🧹 Remove optional junk column
    if "apaar_status" in df.columns:
        df.drop(columns=["apaar_status"], inplace=True)

    # Capitalize gender and reset S.No
    df["gender"] = df["gender"].str.upper()
    df["sno"] = range(1, len(df) + 1)

    # 🟢 Clean text fields
    df["adm_no"] = df["adm_no"].astype(str).str.strip()
    df["name"] = df["name"].astype(str).str.strip()
    df["academic_year"] = df["academic_year"].astype(str).str.strip()
    

    conditions = [
        df["grade_id"].between(1, 3),   # grade_id from 1 to 3
        df["grade_id"].between(4, 8)    # grade_id from 4 to 8
    ]
    choices = [1, 2]  # branch_id values

    df["branch_id"] = np.select(conditions, choices, default=3)


    # Sort for visual clarity
    df = df.sort_values(by=["academic_year", "class_nos", "gender", "name"])

    # Prefer non-null mother/father names when dropping duplicates
    df_sorted = df.sort_values(
        by=["adm_no", "mother_name", "father_name"],
        ascending=[True, True, True],
        na_position='last'  # Non-null values come first
    )
    
    academic_year_map = {
    "2024-25": 1,
    "2025-26": 2,
    "2026-27": 3,
}

    df["academic_year_id"] = df["academic_year"].map(academic_year_map)
    
    # 🧾 Save CSV for auditing
    students_path = os.path.join(OUTPUT_DIR, "students_data.csv")
    df.to_csv(students_path, index=False)


    student_list_df = df_sorted.drop_duplicates(subset="adm_no", keep="first")[
        [
            "adm_no", "name", "gender", "mother_name", "father_name",
            "pen_number", "dob", "phone_no", "religion", "caste",
            "sub_caste", "second_lang", "remarks", "student_aadhar", "father_aadhar", "mother_aadhar","apaar_id"
        ]
    ]

    student_list_path = os.path.join(OUTPUT_DIR, "student_list.csv")
    student_list_df.to_csv(student_list_path, index=False)

    students_df = df[
        [
            "adm_no", "class_nos",
            "grade_id", "academic_year_id", "status_id","branch_id"
        ]
    ]


    print("✅ Cleaned and split data saved.")

    return student_list_df, students_df


# %%
def update_database(df, table_name):

    # Table creation logic
    table_create_sql = {
        "students": """
            CREATE TABLE IF NOT EXISTS students (
                id SERIAL PRIMARY KEY,
                adm_no VARCHAR,
                class_nos VARCHAR,
                grade_id VARCHAR,
                academic_year_id INT,
                status_id INT,
                branch_id INT
            );
        """,
        "student_list": """
            CREATE TABLE IF NOT EXISTS student_list (
                adm_no VARCHAR PRIMARY KEY,
                name VARCHAR,
                gender VARCHAR,
                mother_name VARCHAR,
                father_name VARCHAR,
                pen_number VARCHAR,
                dob DATE,
                phone_no VARCHAR,
                religion VARCHAR,
                caste VARCHAR,
                sub_caste VARCHAR,
                second_lang VARCHAR,
                remarks TEXT,
                student_aadhar VARCHAR,
                father_aadhar VARCHAR,
                mother_aadhar VARCHAR,
                apaar_id VARCHAR
            );
        """
    }

    try:
        with engine.begin() as conn:
            # ✅ Create table if it does not exist
            if table_name in table_create_sql:
                conn.execute(text(table_create_sql[table_name]))
                print(f"📦 Table '{table_name}' created if it didn't exist.")

            # 🗑️ Truncate before insert
            conn.execute(text(f"TRUNCATE TABLE {table_name} RESTART IDENTITY CASCADE;"))
            print(f"🧹 Old records deleted from '{table_name}'.")

        day_wise_df = df.replace({pd.NA: None, np.nan: None})
        print(f"⏳ Inserting data into '{table_name}'...")

        df.to_sql(name=table_name, con=engine, if_exists='append', index=False, method='multi', chunksize=500)

        with engine.connect() as conn:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name};"))
            count = result.scalar()
            print(f"✅ Insert complete. 📊 Table '{table_name}' now contains {count} records.\n")

    except Exception as e:
        print(f"❌ Error updating table '{table_name}': {e}")


# %% [markdown]
# ## **Clean Extracted Data**

# %%
if __name__ == "__main__":
    print("🚀 Starting full student import pipeline...\n")

    merged_df = merge_and_tag()
    student_list_df, students_df = clean_data(merged_df)

    # Update master (student_list) and academic (students) tables
    update_database(students_df, "students")
    update_database(student_list_df, "student_list")

    print("🎉 All done! Both 'student_list' and 'students' tables updated successfully.")


# %%
students_df[["adm_no", "academic_year_id", "status_id"]].head(10)

# %%
students_df[(students_df["academic_year_id"] == 3) & (students_df["status_id"] == 3)].sort_values(by=["adm_no"]).reset_index(drop=True).head(10)

# %%
student_list_df

# %%


# %% [markdown]
# <h2 align="center"><b>FEE REPORTS</b></h2>

# %% [markdown]
# ## **Import Necessary Libraries & Define Global Variables**

# %%
# * Google Sheets Config (from .env)
GOOGLE_JSON_FEE_DATA_PATHS = {
    "2024-25": os.getenv("GOOGLE_JSON_FEE_DATA_PATH_2024_25"),
    "2025-26": os.getenv("GOOGLE_JSON_FEE_DATA_PATH_2025_26"),
    "2026-27": os.getenv("GOOGLE_JSON_FEE_DATA_PATH_2026_27")
}

GOOGLE_JSON_FEE_PATHS = {
    "2024-25": os.getenv("GOOGLE_JSON_FEE_PATH_2024_25"),
    "2025-26": os.getenv("GOOGLE_JSON_FEE_PATH_2025_26"),
    "2026-27": os.getenv("GOOGLE_JSON_FEE_PATH_2026_27")
}

UNIQUE_KEY = os.getenv("UNIQUE_KEY")


TABLE_NAME = "fees_table"


# %% [markdown]
# ## **Function for Fetching Data**

# %%
# === FETCH GOOGLE SHEET ===
def fetch_data(sheet_title, worksheet_name="Overall Sheet", json_path=None):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(json_path, scope)
    client = gspread.authorize(creds)
    spreadsheet = client.open(sheet_title)
    sheet = spreadsheet.worksheet(worksheet_name)
    data = sheet.get_all_records(head=3)
    return pd.DataFrame(data)

# === CLEAN COLUMN NAMES ===
def clean_column_names(df):
    df.columns = df.columns.str.strip()
    return df

# %%
## **Merge and Tag Fees Data**
def merge_and_tag():
    df_2024 = clean_column_names(fetch_data(
        GOOGLE_JSON_FEE_PATHS["2024-25"], "Overall Sheet", GOOGLE_JSON_FEE_DATA_PATHS["2024-25"]
    ))

    df_2025 = clean_column_names(fetch_data(
        GOOGLE_JSON_FEE_PATHS["2025-26"], "Overall Sheet", GOOGLE_JSON_FEE_DATA_PATHS["2025-26"]
    ))

    df_2026 = clean_column_names(fetch_data(
        GOOGLE_JSON_FEE_PATHS["2026-27"], "Overall Sheet", GOOGLE_JSON_FEE_DATA_PATHS["2026-27"]
    ))

    df_2024["academic_year"] = "2024-25"
    df_2025["academic_year"] = "2025-26"
    df_2026["academic_year"] = "2026-27"

    return pd.concat([df_2024, df_2025, df_2026], ignore_index=True)

# %% [markdown]
# ## **Function for Cleaning Data**

# %%
def clean_data(df):
    df = df.iloc[:-7, :]  # Drop the last 7 rows (adjust if necessary)

    df.columns = ['SNo', 'ADM_NO', 'STUDENT_NAME', 'CLASS', "GENDER",'FB_NO',
                  'Term1', 'Term2', 'Term3', 'Term4', 'Total_Fee_Paid',
                  'Discount_Concession', 'Exempted', 'Total_Fee_Due', 'PermissionUpto',
                  'Fine', 'Payment_Status', 'ClassNo', "AcNo", 'Concession_type', 
                  "staff_name", "academic_year"]

    df.columns = df.columns.str.strip().str.lower()

    # 🚫 Remove blank admission numbers & student names
    df = df[df["adm_no"].astype(str).str.strip() != ""]
    df = df.dropna(subset=["adm_no"])
    df = df[df["student_name"].astype(str).str.strip() != ""]
    df = df.dropna(subset=["student_name"])

    # 🔢 Convert numeric columns
    columns_to_convert = ["term1", "term2", "term3", "term4", "total_fee_paid",
                          "discount_concession", 'exempted', "total_fee_due", "fine"]
    df[columns_to_convert] = df[columns_to_convert].apply(pd.to_numeric, errors='coerce').fillna(0)

    # ❌ Drop unused columns
    df = df.drop(columns=["acno", 'concession_type','gender'])

    # 🔢 Add serial number
    df["sno"] = range(1, len(df) + 1)

    # 💰 Calculate total fees
    df["total_fees"] = df["total_fee_paid"] + df["discount_concession"] + df["total_fee_due"] + df["exempted"]

    # 🆔 Academic year mapping
    year_map = {
    "2024-25": 1,
    "2025-26": 2,
    "2026-27": 3
}

    df["academic_year_id"] = df["academic_year"].map(year_map)
    df = df.sort_values(by=["academic_year_id", "classno", "student_name"], ascending=[True, True, True])

    # 📂 Save main fees report
    fees_path = os.path.join(OUTPUT_DIR, "fees_report.csv")
    df.to_csv(fees_path, index=False)

    # ✅ Ensure payment_status column exists
    if "payment_status" not in df.columns:
        df["payment_status"] = "Unknown"

    # 📂 Create payment status table
    payment_status_df = df[["payment_status"]].sort_values(by="payment_status").drop_duplicates().reset_index(drop=True).copy()
    payment_status_df["payment_status_id"] = range(1, len(payment_status_df) + 1)
    payment_status_df = payment_status_df[["payment_status_id", "payment_status"]]
    payment_status_path = os.path.join(OUTPUT_DIR, "payment_status_table.csv")
    payment_status_df.to_csv(payment_status_path, index=False)
    print("✅ Fees Report & Payment Status Table created successfully.\n")

    df["staff_name"] = df["staff_name"].fillna("").astype(str).str.strip()
    
    # 📂 Create staff child table
    df["staff"] = np.where(df['staff_name'].notnull() & df['staff_name'].str.strip().ne(''),1,0)    
    
    # ✅ Extract only staff records for the child table
    staff_child_df = df[df["staff"] == 1][["staff_name"]].drop_duplicates().reset_index(drop=True)

    # Assign staff IDs sequentially
    staff_child_df["staff_id"] = range(1, len(staff_child_df) + 1)


    # Save staff child table
    staff_child_path = os.path.join(OUTPUT_DIR, "staff_child_table.csv")
    staff_child_df.to_csv(staff_child_path, index=False)
    print("✅ Staff Child Table created successfully.\n")

    # --- Step 1: Merge Payment Status ---
    if "payment_status" in df.columns and "payment_status" in payment_status_df.columns:
        payment_status_df = payment_status_df.drop_duplicates(subset=["payment_status"])
        df = df.merge(payment_status_df, on="payment_status", how="left")

    # --- Step 2: Merge Staff Child ---
    # Drop duplicate merge keys to avoid _x / _y
    merge_keys = ["staff_name"]
    staff_child_clean = staff_child_df.drop(
        columns=[col for col in staff_child_df.columns if col in df.columns and col not in merge_keys],
        errors="ignore" 
    )
    df = df.merge(staff_child_clean, on=merge_keys, how="left")

    # Merge Payment Status first
    df = pd.merge(df, payment_status_df, on="payment_status", how="left")
    
    # --- Step 3: Final Cleanup ---
    # Drop any remaining _y columns
    df = df.drop(columns=[c for c in df.columns if c.endswith("_y")], errors="ignore")

    # Rename _x columns back to original
    df.columns = [c.replace("_x", "") for c in df.columns]

    # ❌ Drop extra columns before DB insert
    cols_to_drop = ["permissionupto", "payment_status", "student_name", "class", "staff_name", "academic_year"]
    df.drop(columns=[c for c in cols_to_drop if c in df.columns], inplace=True)

    df.columns = df.columns.str.lower().str.strip()

    return df


# %% [markdown]
# ## **Function for Updating the Database**

# %%
def table_exists(table_name):
    check_query = """
    SELECT EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_name = :table_name
    );
    """
    with engine.connect() as conn:
        result = conn.execute(text(check_query), {"table_name": table_name}).scalar()
    return result


def create_table():
    """Create table only if it does not exist"""
    print("🔧 create_table() function called.")  # Debug print
    table_name = "fees_table"
    
    if table_exists(table_name):
        print(f"✅ Table '{table_name}' already exists.")
        return

    create_table_query = """
    CREATE TABLE fees_table (
    sno SERIAL PRIMARY KEY,
    adm_no TEXT,
    fb_no TEXT,
    term1 NUMERIC DEFAULT 0,
    term2 NUMERIC DEFAULT 0,
    term3 NUMERIC DEFAULT 0,
    term4 NUMERIC DEFAULT 0,
    total_fee_paid NUMERIC DEFAULT 0,
    discount_concession NUMERIC DEFAULT 0,
    exempted NUMERIC DEFAULT 0,
    total_fee_due NUMERIC DEFAULT 0,
    fine NUMERIC DEFAULT 0,
    classno INTEGER,
    staff INTEGER,
    staff_id INTEGER,
    academic_year_id INTEGER NOT NULL,
    total_fees INTEGER DEFAULT 0,
    payment_status_id INTEGER
);
    """
    
    try:
        with engine.begin() as conn:
            conn.execute(text(create_table_query))
            print(f"✅ Table '{table_name}' created successfully.")
    except Exception as e:
        print(f"❌ Error creating table: {e}")


# %%
def update_database(df):

    try:
        with engine.begin() as conn:
            # ✅ Truncate existing table and reset serial ID
            conn.execute(text(f"TRUNCATE TABLE {TABLE_NAME} RESTART IDENTITY CASCADE;"))
            print(f"✅ All records from the '{TABLE_NAME}' table have been deleted.\n")

            # ✅ Add UNIQUE constraint on 'admissionno' (if it doesn't exist)
            conn.execute(text(f"""
                DO $$ 
                BEGIN 
                    -- Drop old constraint if exists
                    IF EXISTS (
                        SELECT 1 FROM information_schema.table_constraints 
                        WHERE table_name = '{TABLE_NAME}' AND constraint_name = 'unique_admissionno'
                    ) THEN
                        ALTER TABLE {TABLE_NAME} DROP CONSTRAINT unique_admissionno;
                    END IF;

                    -- Add new composite unique constraint if not exists
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.table_constraints 
                        WHERE table_name = '{TABLE_NAME}' AND constraint_name = 'unique_adm_year'
                    ) THEN
                        ALTER TABLE {TABLE_NAME} ADD CONSTRAINT unique_adm_year UNIQUE ("adm_no", "academic_year_id");
                    END IF;
                END $$;
            """))

            print(f"✅ Unique constraint on 'admissionno' ensured in the '{TABLE_NAME}' table.\n")

        print("✅ Table cleared. Proceeding with data insertion...\n")

        # ✅ Normalize column names
        df.columns = df.columns.str.lower()

        # ✅ Insert data in chunks
        df.to_sql(
            name=TABLE_NAME,
            con=engine,
            if_exists='append',
            index=False,
            method='multi',
            chunksize=1000
        )

        print(f"✅ {len(df)} records successfully inserted into '{TABLE_NAME}'.\n")

    except SQLAlchemyError as e:
        print(f"❌ An error occurred during database update: {e}")


# %% [markdown]
# ## **Main Execution Block**

# %%
if __name__ == "__main__":
    # * Merge and tag both years
    combined_df = merge_and_tag()
    print("✅ Raw data merged from both years.\n")

    # * Clean and process the merged data
    cleaned_df = clean_data(combined_df)
    print("✅ Data cleaned and transformed successfully.\n")
    print("✅ Final columns are:\n", cleaned_df.columns.to_list())

    # * Create table if it does not exist
    create_table()
    print("\n✅ Table check/creation complete.\n")

    # * Drop duplicates by adm_no + year before insert
    cleaned_df = cleaned_df.drop_duplicates(subset=["adm_no", "academic_year_id"])
    print(f"✅ Deduplicated. Final records to upload: {len(cleaned_df)}\n")

    # * Upload data using safe insertion
    update_database(cleaned_df)


# %%
staff_child_path = os.path.join(OUTPUT_DIR, "staff_child_table.csv")
staff_child_df = pd.read_csv(staff_child_path)
staff_child_df


# %% [markdown]
# <h2 align="center"><b>DAY WISE REPORTS</b></h2>

# %% [markdown]
# # ============================================
# # 📘 KOTAK SALESIAN SCHOOL
# # DAYWISE FEE COLLECTION DATA EXTRACTOR (FINAL CLEANED VERSION)
# # ============================================

# %% [markdown]
# ## **Import Required Libraries**

# %%
 # Load environment variables from .env

print("✅ Libraries imported successfully")

# --- LOGIN & TARGET URLs ---
login_url = "https://app.myskoolcom.tech/kotak_vizag/login"
urls_to_fetch = [
    "https://app.myskoolcom.tech/kotak_vizag/office_fee/fee_reports_day_wise_receipt_wise_print?academic_years_id=1",
    "https://app.myskoolcom.tech/kotak_vizag/office_fee/fee_reports_day_wise_receipt_wise_print?academic_years_id=7",
    "https://app.myskoolcom.tech/kotak_vizag/office_fee/fee_reports_day_wise_receipt_wise_print?academic_years_id=8"
]

TABLE_NAME = "daywise_fees_collection"

credentials = {
    "uname": os.getenv("APP_UNAME"),
    "psw": os.getenv("APP_PSW")
}

# %%
# --- FUNCTION: Determine Academic Year ---
def get_academic_year_from_url(url):
    if "academic_years_id=1" in url:
        return "2024-25"
    elif "academic_years_id=7" in url:
        return "2025-26"
    elif "academic_years_id=8" in url:
        return "2026-27"
    else:
        raise ValueError(f"Unexpected academic_years_id in URL: {url}")


# --- FUNCTION: Login ---
def login_to_website():
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/118.0.5993.70 Safari/537.36"
    })
    response = session.post(login_url, data=credentials, timeout=15)
    if "Invalid" in response.text or response.status_code != 200:
        print("❌ Login failed! Check credentials or site status.\n")
        return None
    print("✅ Login successful!\n")
    return session

# %%
# --- FUNCTION: Fetch & Split by Account ---
def fetch_account_sections(session, data_url):
    response = session.get(data_url, timeout=25)
    html = response.text

    # Stop before CANCELLED RECEIPTS section
    if "CANCELLED RECEIPTS" in html:
        html = html.split("CANCELLED RECEIPTS")[0]

    # Split by “Account Name” headings
    sections = html.split("Account Name:")
    sections = [f"Account Name:{s}" for s in sections if "S.No" in s or "<table" in s]
    print(f"🔍 Found {len(sections)} account section(s) in this page.")
    return sections

# --- FUNCTION: Extract Data From Table ---
def extract_data_from_table(table):
    try:
        rows = []
        header_row = table.find("tr")
        if not header_row:
            return None

        headers = [th.get_text(strip=True) for th in header_row.find_all("th")]
        if not headers:
            headers = [
                "S.No", "Receipt No.", "Class/Sec", "Student Number",
                "Student Name", "Date Added", "-", "Abacus / Vedic Maths",
                "TERM FEE 1", "TERM FEE 2", "Total Received Amount"
            ]

        for tr in table.find_all("tr")[1:]:
            cols = [td.get_text(strip=True) for td in tr.find_all("td")]
            if cols and any(cell.strip() for cell in cols):
                rows.append(cols)

        if not rows:
            return None

        headers = headers[:max(len(r) for r in rows)]
        df = pd.DataFrame(rows, columns=headers)
        return df

    except Exception as e:
        print(f"⚠️ Table extraction failed: {e}")
        return None


# --- FUNCTION: Extract Account Info + Table ---
def extract_account_data(section_html):
    soup = BeautifulSoup(section_html, "html.parser")
    text = soup.get_text(separator="\n")

    # Account and mode extraction
    account_name, payment_mode = None, None
    for line in text.splitlines():
        if "Account Name" in line:
            account_name = line.split(":")[-1].strip()
        if "Payment Mode" in line:
            payment_mode = line.split(":")[-1].strip()

    table = soup.find("table")
    if not table:
        print(f"⚠️ Skipping '{account_name}' (no table found).")
        return None, account_name, payment_mode

    df = extract_data_from_table(table)
    return df, account_name, payment_mode

# %%
# --- FUNCTION: Clean and Tag Data ---
def clean_and_tag_data(df, academic_year, account_name, payment_mode):
    df = df.copy()

    df.columns = (
        df.columns.str.strip()
        .str.lower()
        .str.replace(" ", "_")
        .str.replace(".", "", regex=False)
    )

    rename_map = {
        "student_number": "AdmissionNo",
        "date_added": "Date",
        "total_received_amount": "ReceivedAmount",
        "receipt_no": "ReceiptNo",
        "class_sec": "ClassSec",
        "student_name": "StudentName",
        "abacus_/_vediic_maths": "AbacusVedicMaths",
    }
    df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns}, inplace=True)

    # --- Convert data types ---
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], format="%d-%m-%Y", errors="coerce")
    if "ReceivedAmount" in df.columns:
        df["ReceivedAmount"] = pd.to_numeric(df["ReceivedAmount"], errors="coerce").fillna(0)
        df = df[df["ReceivedAmount"]>=400]

    # --- Add metadata ---
    df["academic_year_id"] = 1 if academic_year == "2024-25" else 2 if academic_year == "2025-26" else 3
    df["account_name"] = account_name or "Unknown"
    df["payment_mode"] = payment_mode or "Unknown"

    # --- Drop filler columns ---
    drop_cols = ["-", "abacus_vedic_maths", "term_fee", "term_fee1", "term_fee2"]
    df.drop(columns=[c for c in drop_cols if c in df.columns], inplace=True, errors="ignore")

    # --- Remove total/empty rows ---
    # A total row usually has all numeric values or starts with 0 / Totals / blank name
    df = df[~df.iloc[:, 0].astype(str).str.match(r"^(0|Totals?|)$", na=False)]  # skip "0" or "Totals"
    if "StudentName" in df.columns:
        df = df[df["StudentName"].astype(str).str.strip().ne("")]

    # --- Drop missing admission numbers ---
    if "AdmissionNo" in df.columns:
        df = df[df["AdmissionNo"].astype(str).str.strip() != ""]

    # --- Reset index ---
    df = df.reset_index(drop=True)

    return df

# %%
def update_database(df, truncate=True):
    

    # --- Define only the target DB columns ---
    target_columns = [
        "SNo",
        "AdmissionNo",
        "Date",
        "ReceivedAmount",
        "academic_year_id",
        "account_name",
        "payment_mode",
    ]

    # --- Normalize column names ---
    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(" ", "", regex=False)
        .str.replace(".", "", regex=False)
        .str.replace("/", "", regex=False)
        .str.replace("-", "", regex=False)
        .str.replace("_", "", regex=False)
    )

    # --- Map possible column variations to final schema ---
    rename_map = {
        "sno": "SNo",
        "admissionno": "AdmissionNo",
        "date": "Date",
        "receivedamount": "ReceivedAmount",
        "academicyearid": "academic_year_id",
        "accountname": "account_name",
        "paymentmode": "payment_mode",
    }

    # --- Apply renaming ---
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

    # --- Drop everything not in target columns ---
    df = df[[c for c in df.columns if c in target_columns]]

    # --- Add any missing columns as None ---
    for c in target_columns:
        if c not in df.columns:
            df[c] = None

    # --- Reorder columns cleanly ---
    df = df[target_columns]

    # --- Connect to PostgreSQL ---
    password = urllib.parse.quote_plus(POSTGRES_CREDENTIALS["password"] or "")
    engine = create_engine(
        f"postgresql+psycopg2://{POSTGRES_CREDENTIALS['username']}:{password}"
        f"@{POSTGRES_CREDENTIALS['host']}:{POSTGRES_CREDENTIALS['port']}/{POSTGRES_CREDENTIALS['database']}"
    )

    # --- Create table if not exists (clean structure) ---
    create_table_sql = f"""
    CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
        "SNo" TEXT,
        "AdmissionNo" TEXT,
        "Date" DATE,
        "ReceivedAmount" NUMERIC,
        "academic_year_id" INTEGER,
        "account_name" TEXT,
        "payment_mode" TEXT
    );
    """ 

    try:
        with engine.begin() as conn:
            conn.execute(text(create_table_sql))
            if truncate:
                conn.execute(text(f'TRUNCATE TABLE {TABLE_NAME};'))
                print(f"✅ Table '{TABLE_NAME}' ensured and truncated.\n")

        # --- Insert cleaned data into DB ---
        df.to_sql(
            name=TABLE_NAME,
            con=engine,
            if_exists='append',
            index=False,
            method='multi',
            chunksize=1000
        )
        print(f"✅ {len(df)} records inserted into '{TABLE_NAME}' successfully.\n")

    except Exception as e:
        print(f"⚠️ Error inserting data: {e}")


# %%
# --- MAIN FUNCTION ---
def main():
    session = login_to_website()
    if session is None:
        return

    all_dfs = []

    for url in urls_to_fetch:
        academic_year = get_academic_year_from_url(url)
        print(f"\n📄 Fetching data for academic year: {academic_year}")

        try:
            sections = fetch_account_sections(session, url)
            if not sections:
                print(f"⚠️ No account sections found for {academic_year}")
                continue

            year_dfs = []

            for idx, section in enumerate(sections, start=1):
                df, account_name, payment_mode = extract_account_data(section)
                if df is None or df.empty:
                    continue

                df = clean_and_tag_data(df, academic_year, account_name, payment_mode)
                if df.empty:
                    print(f"⚠️ Section {idx}: Skipped totals-only data ({account_name})")
                    continue

                year_dfs.append(df)
                print(f"✅ {academic_year} | Section {idx}: {len(df)} rows | Account: {account_name} | Mode: {payment_mode}")

            if year_dfs:
                combined_year = pd.concat(year_dfs, ignore_index=True)
                out_path = os.path.join(OUTPUT_DIR, f"daywise_fees_collection_{academic_year}.csv")
                combined_year.to_csv(out_path, index=False)
                print(f"💾 Saved {len(combined_year)} records for {academic_year}")
                all_dfs.append(combined_year)

        except Exception as e:
            print(f"⚠️ Error fetching {academic_year}: {e}")

    if all_dfs:
        final_df = pd.concat(all_dfs, ignore_index=True)
        master_path = os.path.join(OUTPUT_DIR, "daywise_fees_collection.csv")
        online_master_path = os.path.join(OUTPUT_DIR, "daywise_fees_collection_online.csv")
        final_df.to_csv(master_path, index=False)
        print("\n✅ Combined CSV saved successfully!")
        print(final_df["payment_mode"].unique())
        online_final_df = final_df[final_df["payment_mode"] == "Online Payment"].copy()
        online_final_df.to_csv(online_master_path, index=False)
        print(f"📊 Total Records Combined: {len(final_df)}")

        # --- Upload to Database ---
        update_database(final_df)
        print("✅ Database update complete.")
    else:
        print("\n❌ No valid data extracted from any academic year.")


# --- RUN ---
if __name__ == "__main__":
    main()


# %% [markdown]
# <h2 align="center"><b>FEE COLLECTION REPORT 2024-25</b></h2>

# %% [markdown]
# ## **Import Required Libraries**

# %%
# 📌 Logging
logging.basicConfig(filename="fee_collection_merge.log", level=logging.ERROR)

# 🔐 Credentials & URLs
login_url = "https://app.myskoolcom.tech/kotak_vizag/login"

urls = {
    "2024_25": "https://app.myskoolcom.tech/kotak_vizag/office_fee/fee_consolidate_report_print?&from=2024-04-01&academic_years_id=1&status=1&imageField=Search",
    "2025_26": "https://app.myskoolcom.tech/kotak_vizag/office_fee/fee_consolidate_report_print?&from=2025-04-01&academic_years_id=7&status=1&imageField=Search",
    "2026_27": "https://app.myskoolcom.tech/kotak_vizag/office_fee/fee_consolidate_report_print?&from=2026-04-01&academic_years_id=8&status=1&imageField=Search"
}

TABLE_NAME = "fees_collection"


# %%

# 🔑 Login
def login_to_website():
    session = requests.Session()
    response = session.post(login_url, data=credentials)
    if "Invalid" in response.text:
        print("❌ Login failed!")
        return None
    print("✅ Login successful!")
    return session


# %%
# 🧾 Convert HTML table to DataFrame
def table_to_dataframe(table):
    headers = [th.get_text(strip=True) for th in table.find_all("th")]
    rows = [[td.get_text(strip=True) for td in tr.find_all("td")] for tr in table.find_all("tr")[1:]]
    return pd.DataFrame(rows, columns=headers) if rows else None

# 📥 Fetch fee table from a given URL
def fetch_fee_table(session, url):
    response = session.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    tables = soup.find_all("table", class_="b-t")
    all_data = []

    for table in tables:
        df = table_to_dataframe(table)
        if df is not None:
            all_data.append(df)

    return pd.concat(all_data, ignore_index=True) if all_data else pd.DataFrame()

# %%
def clean_data(df, academic_year):
    df = df[~df.iloc[:, 0].astype(str).str.startswith("Total", na=False)].copy()
    df["Admin No."] = df["Admin No."].astype(str)

    if academic_year == "2025_26":
        df.columns = ['SNo', 'AdmissionNo', 'Name', 'Abacus1', 'TermFee1', 'TermFee2',
                      'Total_Fees', 'Abacus2', 'TermFee3', 'TermFee4',
                      'Total_Fee_Paid', 'Discount_Concession', 'Total_Due']
        df = df.drop(columns=["SNo", "Abacus1", "Abacus2", "TermFee1", "TermFee2", "TermFee3", "TermFee4"])

    elif academic_year == "2024_25":
        df.columns = ['SNo', 'AdmissionNo', 'Name', 'Abacus1', 'TermFee1',
                      'Total_Fees', 'Abacus2', 'TermFee2',
                      'Total_Fee_Paid', 'Discount_Concession', 'Total_Due']
        df = df.drop(columns=["SNo", "Abacus1", "Abacus2", "TermFee1", "TermFee2"])

    elif academic_year == "2026_27":
        df.columns = ['SNo', 'AdmissionNo', 'Name', 'Abacus1', 'TermFee1', 'TermFee2',
                      'Total_Fees', 'Abacus2', 'TermFee3', 'TermFee4',
                      'Total_Fee_Paid', 'Discount_Concession', 'Total_Due']
        df = df.drop(columns=["SNo", "Abacus1", "Abacus2", "TermFee1", "TermFee2", "TermFee3", "TermFee4"])

    else:
        raise ValueError(f"Unknown academic year structure: {academic_year}")

    # Convert numeric columns safely
    numeric_columns = ["Total_Fees", "Total_Fee_Paid", "Discount_Concession", "Total_Due"]
    for col in numeric_columns:
        df[col] = (
            df[col].astype(str)
            .str.replace(",", "", regex=False)
            .replace(["", "None", "nan", "NaN", np.nan], 0)
        )
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

    df["academic_year_id"] = 1 if academic_year =="2024_25" else 2 if academic_year == "2025_26" else 3

    df_2026 = df[df["academic_year_id"] == 3]
    df_2026.to_csv(os.path.join(OUTPUT_DIR, "fees_collection_2026_27_1.csv"), index=False)
    # df = df[~((df["AdmissionNo"].str.extract(r"(\d+)").astype(int) > 17164) & (df["academic_year_id"] == 1))].copy()

    master_path = os.path.join(OUTPUT_DIR, "fees_collection.csv")

    df.to_csv(master_path, index=False)
    df = df.drop(columns=["Name"])
    return df


# %%
def ensure_fees_collection_table(engine, table: str):
    create_table_sql = f"""
    CREATE TABLE IF NOT EXISTS {table} (
        id SERIAL PRIMARY KEY,
        admissionno TEXT,
        total_fee_paid INTEGER,
        academic_year_id INTEGER NOT NULL,
        total_fees INTEGER DEFAULT 0,
        discount_concession INTEGER DEFAULT 0,
        total_due INTEGER DEFAULT 0
    );
    """
    try:
        with engine.begin() as conn:
            conn.execute(text(create_table_sql))
        print(f"✅ Table '{table}' ensured.")
    except Exception as e:
        print(f"❌ Error creating table: {e}")



# %%
# 🛢️ Insert into PostgreSQL
def update_database(df, table_name):
    try:
        with engine.begin() as conn:
            print(f"⚠️ Deleting old records from '{table_name}'...")
            conn.execute(text(f"DELETE FROM {table_name};"))
            print(f"✅ Table '{table_name}' cleared.")
        df.columns = df.columns.str.lower()
        print(f"📥 Inserting {len(df)} rows...")
        df.to_sql(name=table_name, con=engine, if_exists='append', index=False, method='multi', chunksize=1000)
        print(f"✅ Inserted into '{table_name}' successfully.")
    except Exception as e:
        print(f"❌ Error inserting: {e}")
        logging.error(f"Database insert error: {e}")
    finally:
        engine.dispose()

# %%
# 🚀 Main Logic
def main():
    session = login_to_website()
    if session is None:
        return

    merged_df = pd.DataFrame()
    
    for year, url in urls.items():
        print(f"\n🔄 Fetching data for {year}...")
        raw_df = fetch_fee_table(session, url)
        if raw_df.empty:
            print(f"❌ No data for {year}!")
            continue
        clean_df = clean_data(raw_df, academic_year=year)
        merged_df = pd.concat([merged_df, clean_df], ignore_index=True)

    if merged_df.empty:
        print("❌ No data collected from any year!")
        return

    # Save CSV (optional)
    merged_df.to_csv(os.path.join(BASE_DIR, "output_data/merged_fee_collection"), index=False)
    print("📁 Saved to merged_fee_collection.csv")

    # Ensure table exists
    ensure_fees_collection_table(engine, TABLE_NAME)
    print("✅ Fees collection table ensured.")
    # Push to DB
    update_database(merged_df, TABLE_NAME)
    print(f"✅ All done! Total records: {len(merged_df)}")

if __name__ == "__main__":
    main()

# %% [markdown]
# <h2 align="center"><b>FEE CONCESSION REPORT</b></h2>

# %%



# ------------------ Configuration ------------------
login_url = "https://app.myskoolcom.tech/kotak_vizag/login"
data_url_2024_25 = "https://app.myskoolcom.tech/kotak_vizag/office_fee/fee_discounts_report_receipt_wise_print?&academic_years_id=1"
data_url_2025_26 = "https://app.myskoolcom.tech/kotak_vizag/office_fee/fee_discounts_report_receipt_wise_print?&academic_years_id=7"
data_url_2026_27 = "https://app.myskoolcom.tech/kotak_vizag/office_fee/fee_discounts_report_receipt_wise_print?&academic_years_id=8"

TABLE_NAME = "fee_concession_report"
fee_concession_report_path = os.path.join(OUTPUT_DIR, "fee_concession_report.csv")


# %%
# ------------------ Login Function ------------------
def login_to_website():
    session = requests.Session()
    login_response = session.post(login_url, data=credentials)

    if login_response.status_code != 200:
        print("❌ Login request failed! Server error.\n")
        return None

    soup = BeautifulSoup(login_response.text, "html.parser")
    if soup.find("div", class_="alert-danger"):
        print("❌ Login failed! Check credentials.\n")
        return None

    print("✅ Login successful!\n")
    return session

# %%
# ------------------ Fetch Table Data ------------------
def fetch_all_concession_tables(session, data_url):
    response = session.get(data_url)
    soup = BeautifulSoup(response.text, "html.parser")

    tables = soup.find_all("table", class_="table_view")
    if not tables:
        print("❌ No fee tables found! The page structure may have changed.")
        return None

    all_data = []
    for table in tables:
        df = table_to_dataframe(table)
        if df is not None:
            all_data.append(df)

    if not all_data:
        print("❌ No data extracted from tables.")
        return None

    return pd.concat(all_data, ignore_index=True)

# %%
# ------------------ HTML Table to DataFrame ------------------
def table_to_dataframe(table):
    headers = [th.get_text(strip=True) for th in table.find_all("th")]
    if len(headers) > 8:
        headers = headers[:8]

    rows = []
    for tr in table.find_all("tr")[1:]:
        cells = [td.get_text(strip=True) for td in tr.find_all("td")]
        if len(cells) >= 8:
            rows.append(cells[:8])

    return pd.DataFrame(rows, columns=headers) if rows else None

# %%
# ------------------ Clean DataFrame ------------------
def clean_data(df):
    df.columns = df.columns.str.strip().str.replace(" ", "_").str.lower()
    df = df.dropna(subset=["student_number"])
    df["student_number"] = df["student_number"].astype(str).str.strip()
    df["discount_given"] = pd.to_numeric(df["discount_given"], errors="coerce").fillna(0.00)
    df.drop(columns=['receipt_no', 'fee_name', 'fee_amount', 'total_due_amount'], errors="ignore", inplace=True)
    df["date"] = pd.to_datetime(df["date"].astype(str).str.strip(), errors="coerce").dt.date
    df = df.dropna(subset=["date"])

    df["id"] = range(1, len(df) + 1)

    # Ensure academic_year is kept if present
    cols = ['id', 'date', 'student_number', 'student_name', 'discount_given']
    if "academic_year" in df.columns:
        cols.append("academic_year")

    df = df[cols]
    df.reset_index(drop=True, inplace=True)

    df['academic_year_id'] = df['academic_year'].apply(
        lambda x: 1 if x == "2024-25" else 2 if x == "2025-26" else None
    )
    
    df.to_csv(fee_concession_report_path, index=False)
    print(f"✅ Cleaned data saved to {fee_concession_report_path}\n")

    df = df.drop(columns=['student_name', "academic_year"], errors="ignore")

    return df

# %%
def update_database(df: pd.DataFrame, table_name: str, postgres_credentials: dict):

    try:
        with engine.begin() as conn:
            print(f"🔄 Connecting to database {postgres_credentials['database']}...")

            # ✅ Create table if not exists
            conn.execute(text(f"""
                CREATE TABLE IF NOT EXISTS {table_name} (
                    id SERIAL PRIMARY KEY,
                    date DATE,
                    student_number VARCHAR(20),
                    discount_given NUMERIC(10, 2),
                    academic_year_id INTEGER
                );
            """))
            print(f"✅ Ensured '{table_name}' table exists.")

            # 🔄 Clear existing records
            print(f"⚠️ Deleting existing records from: {table_name}")
            conn.execute(text(f"DELETE FROM {table_name};"))
            print(f"✅ Table '{table_name}' cleared.\n")

        # 📥 Insert Data
        print(f"📥 Inserting data into {table_name} table...")
        df.to_sql(name=table_name, con=engine, if_exists="append", index=False, method="multi", chunksize=1000)
        print(f"✅ Data successfully inserted into '{table_name}' table.\n")

    except Exception as e:
        logging.error(f"❌ Error updating database: {e}", exc_info=True)
        print(f"❌ Error occurred while updating database: {e}")

    finally:
        engine.dispose()


# %%
def main():
    session = login_to_website()
    if session is None:
        return

    df_2024_25 = fetch_all_concession_tables(session, data_url_2024_25)
    df_2025_26 = fetch_all_concession_tables(session, data_url_2025_26)
    df_2026_27 = fetch_all_concession_tables(session, data_url_2026_27)

    if df_2024_25 is None or df_2025_26 is None or df_2026_27 is None:
        print("❌ Could not fetch data for one or more academic years.")
        return

    df_2024_25["academic_year"] = "2024-25"
    df_2025_26["academic_year"] = "2025-26"
    df_2026_27["academic_year"] = "2026-27"

    merged_df = pd.concat([df_2024_25, df_2025_26, df_2026_27], ignore_index=True)

    print("✅ Data extracted successfully! Cleaning data...\n")
    cleaned_df = clean_data(merged_df)

    output_file = os.path.join(
    BASE_DIR,
    "output_data",
    "fee_concession_report_combined.csv"
)
    cleaned_df.to_csv(output_file, index=False)
    print(cleaned_df.columns)
    print(f"✅ Data saved to '{output_file}'\n")

    update_database(cleaned_df, TABLE_NAME, POSTGRES_CREDENTIALS)
    print(f"✅ {len(cleaned_df)} records entered into the database")

    print(cleaned_df.to_string())


# %%
# ------------------ Run Script ------------------
if __name__ == "__main__":
    main()

# %% [markdown]
# <h2 align="center"><b>FEE TRANSCATION ATOM REPORT</b></h2>

# %%
# ------------------ CONFIGURATION ------------------
LOGIN_URL = "https://app.myskoolcom.tech/kotak_vizag/login"
DATA_URL = "https://app.myskoolcom.tech/kotak_vizag/office_fee_new/daywise_atom_report/"
CREDENTIALS = {
    "uname": os.getenv("APP_UNAME"),
    "psw": os.getenv("APP_PSW")
}
TABLE_NAME = "fee_transcation_atom_report"

OUTPUT_PATH = os.path.join(
    BASE_DIR,
    "output_data",
    "fee_transcation_atom_report.csv"
)

# %%
# ------------------ FUNCTIONS ------------------

def login_to_portal(session: requests.Session, login_url: str, credentials: dict) -> None:
    """Logs into the portal and validates session."""
    print("🔑 Logging in...")
    resp = session.post(login_url, data=credentials)
    if "Dashboard" not in resp.text and resp.status_code != 200:
        raise Exception("❌ Login failed. Check credentials or login URL.")
    print("✅ Logged in successfully!")

# %%
def fetch_report_html(session: requests.Session, data_url: str) -> str:
    """Submits the form and retrieves the report HTML."""
    print("📄 Accessing report page...")
    session.get(data_url)  # Load form first

    form_data = {
        "report_type": "transcation_wise",
        "from_date": "2025-10-30",
        "to_date": date.today().strftime("%Y-%m-%d"),
        "product": ""
    }

    print("📦 Fetching report data...")
    resp = session.post(data_url, data=form_data)
    if resp.status_code != 200:
        raise Exception("❌ Failed to fetch report data page.")
    return resp.text

# %%
def parse_html_to_dataframe(html: str) -> pd.DataFrame:
    """Extracts and cleans the HTML table into a DataFrame."""
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")

    if not table:
        raise Exception("❌ No table found in report HTML.")

    print("✅ Found data table. Parsing...")
    df = pd.read_html(StringIO(str(table)))[0]

    # Clean and normalize columns
    df.columns = df.columns.str.strip().str.replace(" ", "_").str.lower()
    df.rename(columns={'amount': 'term_amount', 'amount.1': 'recieved_amount'}, inplace=True)
    df.drop(columns=['adm_no', 'payment_id.1', 'student_no'], errors="ignore", inplace=True)
    # Replace '--' and empty strings with pandas NA
    df = df.replace(['--', ''], pd.NA)

    print("📊 Columns after cleaning:", df.columns.tolist())
    return df

# %%
def save_csv(df: pd.DataFrame, output_path: str) -> None:
    """Saves the DataFrame to a local CSV file."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"✅ CSV saved to {output_path}")

# %%
def upload_to_postgres(df: pd.DataFrame, table_name: str, postgres_credentials: dict) -> None:
    """Uploads DataFrame to PostgreSQL, replacing existing table content."""
    print("⬆️ Uploading data to PostgreSQL...")

    expected_cols = [
        'sno', 'admno', 'payment_id', 'account', 'status', 'term_amount',
        'created', 'settled', 'refund_on', 'receipt_no',
        'recieved_amount', 'date_added', 'difference'
    ]

    # ✅ Fix date formats before upload
    date_columns = ["created", "settled", "refund_on", "date_added"]

    for col in date_columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], dayfirst=True, errors='coerce')
            df[col] = df[col].dt.normalize()

    # ✅ Ensure expected columns exist and correct order
    for col in expected_cols:
        if col not in df.columns:
            df[col] = None
    df = df[expected_cols]

    try:
        with engine.begin() as conn:
            conn.execute(text(f"""
                CREATE TABLE IF NOT EXISTS {table_name} (
                    sno INTEGER PRIMARY KEY,
                    admno VARCHAR,
                    payment_id VARCHAR,
                    account VARCHAR,
                    status VARCHAR,
                    term_amount NUMERIC,
                    created TIMESTAMP NULL,
                    settled TIMESTAMP NULL,
                    refund_on TIMESTAMP NULL,
                    receipt_no VARCHAR,
                    recieved_amount NUMERIC,
                    date_added TIMESTAMP NULL,
                    difference VARCHAR
                );
            """))

            # ✅ Faster and safer than DELETE
            print(f"⚠️ Truncating '{table_name}'...")
            conn.execute(text(f"TRUNCATE TABLE {table_name};"))

            # ✅ Upload data
            df.to_sql(table_name, conn, if_exists="append", index=False)

        print(f"✅ Data successfully uploaded to PostgreSQL table '{table_name}'")

    except Exception as e:
        print(f"❌ Database upload failed: {e}")

    finally:
        engine.dispose()


# %%
# ------------------ MAIN ------------------

def main():
    print("🚀 Starting Fee Transaction Atom Report automation...")
    session = requests.Session()

    try:
        login_to_portal(session, LOGIN_URL, CREDENTIALS)
        html = fetch_report_html(session, DATA_URL)
        df = parse_html_to_dataframe(html)
        save_csv(df, OUTPUT_PATH)
        upload_to_postgres(df, TABLE_NAME, POSTGRES_CREDENTIALS)
        print("🎉 All steps completed successfully!")

    except Exception as e:
        print(f"❌ Error: {e}")

# %%
# ------------------ RUN SCRIPT ------------------
if __name__ == "__main__":
    main()

# %% [markdown]
# <h2 align="center"><b>ATOM WEBSITE TRANSCATION REPORT</b></h2>

# %%
import os
print("Current working dir:", os.getcwd())

# %%
import os
import sys
import time
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager


# ================= LOAD ENV =================
load_dotenv()

BASE_DIR = os.getenv("BASE_DIR")
USERNAME = os.getenv("ATOM_USERNAME")
PASSWORD = os.getenv("ATOM_PASSWORD")

if not BASE_DIR or not USERNAME or not PASSWORD:
    print("❌ Missing environment variables")
    sys.exit(1)


# ================= CONFIG =================
LOGIN_URL = "https://titan.atomtech.in/titan_merchant_console"
TXN_URL = "https://titan.atomtech.in/titan_merchant_console/view-transaction-temp"

FULL_FROM_DATE = datetime.strptime("30/10/2025", "%d/%m/%Y")
FULL_TO_DATE = datetime.today()

MAX_DAYS = 60  # 🔥 SAFE RANGE

DOWNLOAD_DIR = os.path.join(BASE_DIR, "source_data")
FINAL_PATH = os.path.join(DOWNLOAD_DIR, "atom_report.xlsx")

os.makedirs(DOWNLOAD_DIR, exist_ok=True)


# ================= DRIVER =================
def setup_driver():
    options = webdriver.ChromeOptions()

    prefs = {
        "download.default_directory": DOWNLOAD_DIR,
        "download.prompt_for_download": False,
        "safebrowsing.enabled": True,
    }

    options.add_experimental_option("prefs", prefs)

    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-features=DownloadBubble")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )

    driver.execute_cdp_cmd(
        "Page.setDownloadBehavior",
        {"behavior": "allow", "downloadPath": DOWNLOAD_DIR}
    )

    return driver


# ================= HELPERS =================
def split_ranges(start, end, days):
    ranges = []
    cur = start

    while cur <= end:
        r_end = min(cur + timedelta(days=days - 1), end)
        ranges.append((cur, r_end))
        cur = r_end + timedelta(days=1)

    return ranges


def wait_download(old_files, timeout=180):
    end = time.time() + timeout

    while time.time() < end:
        files = os.listdir(DOWNLOAD_DIR)

        for f in files:
            if f.endswith(".crdownload"):
                continue
            if f.endswith(".xlsx") and f not in old_files:
                path = os.path.join(DOWNLOAD_DIR, f)
                if os.path.getsize(path) > 0:
                    return f

        time.sleep(1)

    return None


def has_no_records(driver):
    msgs = driver.find_elements(By.XPATH, "//*[contains(text(),'No Record')]")
    if any(m.is_displayed() for m in msgs):
        return True

    rows = driver.find_elements(By.XPATH, "//table//tbody/tr")
    for r in rows:
        txt = r.text.strip()
        if txt and "No Record" not in txt:
            return False

    return True


def set_dates(driver, from_date, to_date):
    driver.execute_script("""
        function setDate(id, value) {
            let el = document.getElementById(id);
            el.value = value;
            el.dispatchEvent(new Event('input', { bubbles: true }));
            el.dispatchEvent(new Event('change', { bubbles: true }));
            el.dispatchEvent(new Event('blur', { bubbles: true }));
        }
        setDate('fromDate', arguments[0]);
        setDate('toDate', arguments[1]);
    """, from_date, to_date)


# ================= LOGIN =================
def login(driver, wait):
    print("🔐 Logging in...")

    driver.get(LOGIN_URL)

    wait.until(EC.presence_of_element_located((By.ID, "userName"))).send_keys(USERNAME)
    driver.find_element(By.ID, "password").send_keys(PASSWORD)

    driver.find_element(By.XPATH, "//button[contains(text(),'Login')]").click()

    wait.until(EC.presence_of_element_located((By.TAG_NAME, "nav")))

    print("✅ Login successful")


# ================= DOWNLOAD =================
def download_transactions(driver, wait):

    driver.get(TXN_URL)
    wait.until(EC.presence_of_element_located((By.ID, "fromDate")))

    ranges = split_ranges(FULL_FROM_DATE, FULL_TO_DATE, MAX_DAYS)
    all_dfs = []

    for start, end in ranges:
        try:
            from_date = start.strftime("%d/%m/%Y")
            to_date = end.strftime("%d/%m/%Y")

            print(f"⬇️ Fetching {from_date} → {to_date}")

            old_files = set(os.listdir(DOWNLOAD_DIR))

            # 🔥 Reset filters
            try:
                driver.find_element(By.XPATH, "//button[contains(text(),'Reset')]").click()
                time.sleep(2)
            except:
                pass

            # 🔥 Set dates (React fix)
            set_dates(driver, from_date, to_date)
            time.sleep(1)

            # 🔥 Double search click (UI bug)
            search_btn = wait.until(EC.element_to_be_clickable((By.ID, "search")))
            search_btn.click()
            time.sleep(2)
            search_btn.click()

            time.sleep(5)

            rows = driver.find_elements(By.XPATH, "//tbody/tr")
            print("Rows found:", len(rows))

            for i, r in enumerate(rows[:5]):
                print(i, repr(r.text))

            # if has_no_records(driver):
            #     print(f"⚠️ No records for {from_date} → {to_date}")
            #     continue

            print("Ignoring no-record check...")

            from selenium.webdriver.common.action_chains import ActionChains

            excel_btn = wait.until(
    EC.presence_of_element_located(
        (By.XPATH, "//button[contains(., 'XLSX')]")
    )
)

            print("Displayed:", excel_btn.is_displayed())
            print("Enabled:", excel_btn.is_enabled())

            print(driver.execute_script("""
            return {
                ready: document.readyState,
                onclick: arguments[0].getAttribute('onclick')
            }
            """, excel_btn))

            ActionChains(driver).move_to_element(excel_btn).pause(0.5).click().perform()

            driver.execute_script("arguments[0].click();", excel_btn)

            file = wait_download(old_files)

            print("Downloaded:", file)

            path = os.path.join(DOWNLOAD_DIR, file)

            print("Exists:", os.path.exists(path))
            print("Size:", os.path.getsize(path))

            print(driver.execute_script("""
return {
    exists: typeof downLoadData,
    ready: document.readyState
}
"""))

            if not file:
                print("❌ Download failed")
                continue

            path = os.path.join(DOWNLOAD_DIR, file)

            try:
                df = pd.read_excel(path)
                print(df.head())
                print("Rows:", len(df))
                all_dfs.append(df)
            except Exception as e:
                print("READ ERROR:", e)

            os.remove(path)

            print("✅ File processed")

        except Exception:
            import traceback
            traceback.print_exc()
            raise

    return all_dfs




# %%
# ================= MAIN =================
def main():

    if os.path.exists(FINAL_PATH):
        os.remove(FINAL_PATH)

    driver = setup_driver()
    wait = WebDriverWait(driver, 60)

    login(driver, wait)

    dfs = download_transactions(driver, wait)

    driver.quit()

    if not dfs:
        print("❌ No data")
        sys.exit(1)

    final_df = pd.concat(dfs, ignore_index=True)
    final_df.to_excel(FINAL_PATH, index=False)

    print("🎉 atom_report.xlsx created successfully")


# ================= RUN =================
if __name__ == "__main__":
    main()

# %%


# %%
# time.sleep(10)

# %% [markdown]
# **MANUAL WORK**

# %%
# import os
# import pandas as pd

# # 📁 Folder path
# DOWNLOAD_DIR = r"/Users/harikiran/Documents/GitHub/kotak-salesian-school-dbms/source_data"   # 🔁 change this
# OUTPUT_FILE = os.path.join(DOWNLOAD_DIR, "atom_report.xlsx")

# all_dfs = []

# # 🔍 Read only Transaction files
# for file in os.listdir(DOWNLOAD_DIR):
#     if file.startswith("TXN") and file.endswith(".xlsx") and not file.startswith("~"):
#         path = os.path.join(DOWNLOAD_DIR, file)
#         print(f"📄 Reading: {file}")

#         try:
#             df = pd.read_excel(path)

#             # optional: track source file
#             df["source_file"] = file

#             all_dfs.append(df)

#         except Exception as e:
#             print(f"⚠️ Error reading {file}: {e}")

# # ❌ No valid files
# if not all_dfs:
#     print("❌ No Transaction files found")
#     exit()

# # 🔗 Merge all files
# final_df = pd.concat(all_dfs, ignore_index=True)


# # 📅 Optional: sort by date column if exists
# DATE_COLUMNS = ["Date", "Txn Date", "Transaction Date"]

# for col in DATE_COLUMNS:
#     if col in final_df.columns:
#         print(f"📅 Sorting by: {col}")
#         final_df[col] = pd.to_datetime(final_df[col], errors='coerce')
#         final_df.sort_values(by=col, inplace=True)
#         break

# # 💾 Save final output
# final_df.to_excel(OUTPUT_FILE, index=False)

# print(f"🎉 Final merged file created: {OUTPUT_FILE}")

# %%
file_path = os.path.join(SOURCE_DIR, "atom_report.xlsx")

warnings.filterwarnings(
    "ignore",
    message="Workbook contains no default style",
    category=UserWarning,
    module="openpyxl"
)

df = pd.read_excel(file_path)
df

# %%
df.info()

# %%
dupes = df['Atom Txn ID'][df['Atom Txn ID'].duplicated(keep=False)]
print(dupes)


# %%
df = (
    df.sort_values(['Atom Txn ID', 'Amount'], ascending=[True, False])
      .drop_duplicates(subset=['Atom Txn ID'], keep='first')
)


# %%
dupes = df['Atom Txn ID'][df['Atom Txn ID'].duplicated(keep=False)]
print(dupes)

# %%
df['Description'].unique()

# %%
df['Txn Status'].unique()

# %%
df = df[
    (df['Description'].isin([
        'TRANSACTION IS SUCCESSFUL',
        'SUCCESS',
        'TRANSACTION IS SUCCESS'
    ])) 
    & 
    (df['Txn Status'].isin(['Force Success','OK']))
]


# %%
df['Description'].unique()

# %%
set_date = df[['Txn Date','Settlement Date','Settlement Date.1',]]
set_date.head()

# %%
# List of columns you want to remove
drop_cols = [
    'Auth No.', 'EMI Bank', 'Card Issuing Bank', 'EMI Tenure',
    'Udf4', 'Udf9', 'Card Number', 'EMI Status', 'EMI Reason', 'EMI Date',
    'Settlement Date.1', 'Address Line 1', 'Address Line 2', 'Country', 'State',
    'City', 'Zip Code', 'Refund Amount', 'Refund Initiated Date',
    'Refund Processed Date', 'Refund Closed Date', 'Refund Closing Remarks',
    'Card Type', 'Scheme', 'UDFEX6', 'UDFEX7', 'UDFEX8', 'UDFEX9', 'UDFEX10',
    'Atom MW MID', 'Atom TID', 'Switch MID', 'Switch TID',
    'NdpsProcCode', 'UMN', 'executionTxnId'
]

df = df.drop(columns=drop_cols, errors='ignore')

# %%
df.info()

# %%
df.rename(columns={'UDFEX5':'admission_no', 'Udf1' : 'student_name', 'Udf2':'email', 'Udf3':'phone', 'UDFEX4' : 'amount in rupees', "Customer Acc. No.": "customer_acc_no",
    "GST (18%)": "gst_18"}, inplace=True)

# %%
df.head(1)

# %%
df.columns

# %%
df.columns = df.columns.str.strip().str.replace(" ", "_").str.lower()
df.columns

# %%
cols_order = [
    'admission_no', 'student_name', 'phone', 'amount', 'net_amount_to_be_paid', 
    'txn_date', 'settlement_date', 'description', 'txn_status', 'product', 'amount_in_rupees',
    'customer_acc_no', 'merchant_name', 'merchant_id', 'client_code', 
    'atom_txn_id', 'merchant_txn_id', 'bank_ref_no', 'currency', 'txn_type', 
    'bank_name', 'recon_status', 'ifsc_code', 'merchant_type', 'discriminator', 
    'email', 'txn_charges', 'gst_18', 'sb_cess', 'krishi_kalyan_cess', 
    'total_chargeable', 'beneficiary_name', 'imps_status', 'settlement_type', 
    'udfex1', 'udfex2', 'udfex3', 'qr_transaction_type'
]

# ✅ Reorder columns safely
df = df[cols_order]

print("✅ DataFrame reordered successfully!")
df.head(1)


# %%
df.head()

# %%
atom_list_path = os.path.join(OUTPUT_DIR, "atom_report_cleaned.xlsx")

df.to_excel(atom_list_path, index=False)
print(f"🧹 Cleaned Excel saved to: {atom_list_path}")

# %%
df.info()

# %%
df.head()

# %%
df.to_csv(os.path.join(OUTPUT_DIR, "atom_report_cleaned.csv"), index=False)
print("✅ Cleaned CSV saved successfully!")

# %%
TABLE_NAME = "atom_transaction_report"

# --- Step 1: Create Table (if not exists) ---
with engine.begin() as conn:
    create_table_sql = f"""
    CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
        id SERIAL PRIMARY KEY,
        admission_no BIGINT,
        student_name TEXT,
        phone TEXT,
        amount NUMERIC(12,2),
        net_amount_to_be_paid NUMERIC(12,2),
        txn_date TIMESTAMP,
        settlement_date TIMESTAMP,
        description TEXT,
        txn_status TEXT,
        product TEXT,
        amount_in_rupees TEXT,
        customer_acc_no TEXT,
        merchant_name TEXT,
        merchant_id BIGINT,
        client_code BIGINT,
        atom_txn_id BIGINT,
        merchant_txn_id BIGINT,
        bank_ref_no BIGINT,
        currency TEXT,
        txn_type TEXT,
        bank_name TEXT,
        recon_status TEXT,
        ifsc_code TEXT,
        merchant_type TEXT,
        discriminator TEXT,
        email TEXT,
        txn_charges NUMERIC(10,2),
        gst_18 NUMERIC(10,2),
        sb_cess NUMERIC(10,2),
        krishi_kalyan_cess NUMERIC(10,2),
        total_chargeable NUMERIC(12,2),
        beneficiary_name TEXT,
        imps_status TEXT,
        settlement_type TEXT,
        udfex1 BIGINT,
        udfex2 TEXT,
        udfex3 TEXT,
        qr_transaction_type TEXT
    );
    """
    conn.execute(text(create_table_sql))
    print(f"✅ Table '{TABLE_NAME}' created or already exists.")

# --- Step 2: Delete existing records ---
with engine.begin() as conn:
    print(f"⚠️ Deleting existing records from '{TABLE_NAME}'...")
    conn.execute(text(f"DELETE FROM {TABLE_NAME};"))
    print(f"✅ All existing records deleted from '{TABLE_NAME}'.")

# --- Step 3: Insert new data ---
df.to_sql(TABLE_NAME, engine, if_exists="append", index=False, method="multi", chunksize=500)
print(f"✅ Inserted {len(df)} fresh records into '{TABLE_NAME}'.")

# --- Step 4: Verify row count ---
with engine.connect() as conn:
    result = conn.execute(text(f"SELECT COUNT(*) FROM {TABLE_NAME};"))
    print(f"📈 Total rows now in table: {result.scalar()}")

# %% [markdown]
# <h2 align="center"><b>ATOM vs DAYWISE</b></h2>

# %%
atom_df = pd.read_excel(atom_list_path)
atom_df.tail(3)

# %%
df = pd.read_csv(os.path.join(OUTPUT_DIR, "daywise_fees_collection.csv"))
print("Payment Types: ", df['payment_mode'].unique())
day_wise_df = df[df['payment_mode'] == 'Online Payment'].copy()
day_wise_df

# %%
print(atom_df.columns)
print(day_wise_df.columns)


# %%
atom_df["admission_no"] = atom_df["admission_no"].astype(str).str.strip()
day_wise_df["AdmissionNo"] = day_wise_df["AdmissionNo"].astype(str).str.strip()


# %%
missing_in_daywise = set(atom_df["admission_no"]) - set(day_wise_df["AdmissionNo"])
print("Missing count:", len(missing_in_daywise))


# %%
atom_missing_df = atom_df[atom_df["admission_no"].isin(missing_in_daywise)]
atom_missing_df


# %%
atom_missing_df.columns

# %%
atom_missing_df = atom_missing_df[['admission_no', 'student_name', 'phone', 'amount',
       'net_amount_to_be_paid', 'txn_date', 'settlement_date', 'description']]

atom_missing_df

# %%
TABLE_NAME = "atom_missing_records"

# --- Step 1: Create Table (if not exists) ---
with engine.begin() as conn:
    create_table_sql = f"""
    CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
        id SERIAL PRIMARY KEY,
        admission_no BIGINT,
        student_name TEXT,
        phone TEXT,
        amount NUMERIC(12,2),
        net_amount_to_be_paid NUMERIC(12,2),
        txn_date TIMESTAMP,
        settlement_date TIMESTAMP,
        description TEXT
    );
    """
    conn.execute(text(create_table_sql))
    print(f"✅ Table '{TABLE_NAME}' created or already exists.")

# --- Step 2: Delete existing records ---
with engine.begin() as conn:
    print(f"⚠️ Clearing old data from '{TABLE_NAME}'...")
    conn.execute(text(f"TRUNCATE TABLE {TABLE_NAME};"))
    print(f"🧹 Existing data cleared.")

# --- Step 3: Insert new data ---atom_missing_df.to_sql(
atom_missing_df.to_sql(
    TABLE_NAME,
    engine,
    if_exists="append",
    index=False,
    method="multi",
    chunksize=500
)

print(f"✅ Inserted {len(atom_missing_df)} fresh records into '{TABLE_NAME}'.")

with engine.connect() as conn:
    count = conn.execute(text(f"SELECT COUNT(*) FROM {TABLE_NAME};")).scalar()
    print(f"📈 Total rows now in table: {count}")



# %%
TABLE_NAME = "staff_child_table"

def upload_staff_table(df, TABLE_NAME, truncate=True):
    print("⬆️ Uploading Staff Data to PostgreSQL...")


    # --- Create table if not exists ---
    create_table_sql = f"""
    CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
        staff_id TEXT PRIMARY KEY,
        staff_name TEXT NOT NULL
    );
    """

    try:
        with engine.begin() as conn:
            # Create table
            conn.execute(text(create_table_sql))

            # Optional truncate
            if truncate:
                conn.execute(text(f"TRUNCATE TABLE {TABLE_NAME};"))
                print(f"✅ Table '{TABLE_NAME}' ensured and truncated.\n")

        # --- Insert cleaned data ---
        df.to_sql(
            name=TABLE_NAME,
            con=engine,
            if_exists='append',
            index=False,
            method='multi',
            chunksize=1000
        )

        print(f"✅ {len(df)} staff records inserted into '{TABLE_NAME}' successfully.\n")

    except Exception as e:
        print(f"⚠️ Error inserting staff data: {e}")

    finally:
        engine.dispose()




# %%
import pandas as pd
staff_child_path = os.path.join(OUTPUT_DIR, "staff_child_table.csv")
staff_child_df = pd.read_csv(staff_child_path)


# %%
upload_staff_table(staff_child_df,TABLE_NAME)

# %%
def notify_success(title, message):
    from plyer import notification

    notification.notify(
        title=title,
        message=message,
        app_name="Python",
        timeout=5
    )


# %%
try:
    # ---- all your code executed successfully ----

    notify_success(
        "Execution Complete",
        "All Python cells ran successfully."
    )

except Exception as e:
    print("Execution failed:", e)


# %%
