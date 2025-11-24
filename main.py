# Converted from notebook: KOTAK_DB.ipynb
# === Basic structure ===
import os
import sys
import logging
from datetime import datetime


logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')



def main():

    # --- Cell 1 ---

    import os
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
    from datetime import date
    import requests
    from io import StringIO


    # --- Cell 2 ---

    # Load environment variables from .env file
    load_dotenv()

    # * PostgreSQL Credentials (from .env)
    POSTGRES_CREDENTIALS = {
        "username": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
        "host": os.getenv("DB_HOST"),
        "port": 5432,
        "database": os.getenv("DB_NAME"),
    }

    password = POSTGRES_CREDENTIALS["password"]

    conn_url = (
            f"postgresql+psycopg2://{POSTGRES_CREDENTIALS['username']}:{password}"
            f"@{POSTGRES_CREDENTIALS['host']}:{POSTGRES_CREDENTIALS['port']}/"
            f"{POSTGRES_CREDENTIALS['database']}"
        )

    engine = create_engine(conn_url)

    # * Backup Config (from .env)
    BACKUP_DIR = os.getenv("BACKUP_DIR")
    DB_DUMP_PATH = os.getenv("PG_DUMP_PATH")

    print("Using BACKUP_DIR:", BACKUP_DIR)
    print("Using DB_DUMP_PATH:", DB_DUMP_PATH)


    # * Ensure the backup directory exists
    os.makedirs(BACKUP_DIR, exist_ok=True)

    # * Generate a timestamp for the backup file
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_file = os.path.join(BACKUP_DIR, f"backup_{POSTGRES_CREDENTIALS['database']}_{timestamp}.sql")

    # * Run DB_dump
    try:
        result = subprocess.run(
            [
                DB_DUMP_PATH,  # Use full path if not in PATH
                "-U", POSTGRES_CREDENTIALS["username"],
                "-h", POSTGRES_CREDENTIALS["host"],
                "-p", POSTGRES_CREDENTIALS["port"],
                "-F", "c",
                "-b",
                "-v",
                "-f", backup_file,
                POSTGRES_CREDENTIALS["database"],
            ],
            env={**os.environ, "PGPASSWORD": POSTGRES_CREDENTIALS["password"]},  # Pass password securely
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=True
        )

        # * Check for errors
        if result.returncode == 0:
            print(f"✅ Backup successful: {backup_file}")
        else:
            print(f"❌ Backup failed!\nError: {result.stderr}")

    except FileNotFoundError:
        print(f"⚠️ DB_dump not found at {DB_DUMP_PATH}. Check PostgreSQL installation or system PATH.")

    except Exception as e:
        print(f"⚠️ An unexpected error occurred: {e}")


    # --- Cell 3 ---

    # * Google Sheets Config (from .env)
    GOOGLE_JSON_STUDENT_PATHS = {
        "2024-25": os.getenv("GOOGLE_JSON_STUDENT_PATH_2024_25"),
        "2025-26": os.getenv("GOOGLE_JSON_STUDENT_PATH_2025_26"),
    }

    GOOGLE_SHEET_TITLES = {
        "2024-25": os.getenv("GOOGLE_SHEET_TITLE_2024_25"),
        "2025-26": os.getenv("GOOGLE_SHEET_TITLE_2025_26"),
    }

    UNIQUE_KEY = os.getenv("UNIQUE_KEY")


    # * Table names
    TABLE_NAME1 = "students"
    TABLE_NAME2 = "student_list"


    # --- Cell 4 ---

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


    # --- Cell 5 ---

    TC_APPLIED_SHEET_NAME = "TC LIST"

    def merge_and_tag():

        # Fetch and clean data
        df_2024 = clean_column_names(fetch_data(
            GOOGLE_SHEET_TITLES["2024-25"], "Overall", GOOGLE_JSON_STUDENT_PATHS["2024-25"]
        ))

        df_2025 = clean_column_names(fetch_data(
            GOOGLE_SHEET_TITLES["2025-26"], "Overall", GOOGLE_JSON_STUDENT_PATHS["2025-26"]
        ))

        # ✅ TC applied sheet
        df_tc_applied = clean_column_names(fetch_data(
            GOOGLE_SHEET_TITLES["2024-25"], TC_APPLIED_SHEET_NAME, GOOGLE_JSON_STUDENT_PATHS["2024-25"]
        ))


        # Tag academic year
        df_2024["academic_year"] = "2024-25"
        df_2025["academic_year"] = "2025-26"

        # Ensure no NaN in unique key column
        df_2024 = df_2024.dropna(subset=[UNIQUE_KEY])
        df_2025 = df_2025.dropna(subset=[UNIQUE_KEY])

        # Get sets of unique keys
        codes_2024 = set(df_2024[UNIQUE_KEY])
        codes_2025 = set(df_2025[UNIQUE_KEY])
        tc_applied_ids = set(df_tc_applied[UNIQUE_KEY])

        # Determine who left and who is new
        left = codes_2024 - codes_2025
        new = codes_2025 - codes_2024

        # Find graduates = left students in max grade
        max_grade = df_2024["GRADES"].max()
        graduates = set(
            df_2024[(df_2024["GRADES"] == max_grade) & (df_2024[UNIQUE_KEY].isin(left))][UNIQUE_KEY]
        )

        # 🔹 Assign status_id for 2024
        def get_status_2024(x):
            if x in graduates:
                return 4  # Graduated
            elif x in tc_applied_ids:
                return 5  # TC Applied
            elif x in left:
                return 2  # Not coming
            else:
                return 1  # Continuing

        df_2024["status_id"] = df_2024[UNIQUE_KEY].apply(get_status_2024)

        # 🔹 Assign status_id for 2025
        df_2025["status_id"] = df_2025[UNIQUE_KEY].apply(
            lambda x: 3 if x in new else 1
        )

        # Merge and return
        return pd.concat([df_2024, df_2025], ignore_index=True)


    # --- Cell 6 ---

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

        df["academic_year_id"] = df["academic_year"].apply(lambda x: 1 if x== "2024-25" else 2)

        # 🧾 Save CSV for auditing
        df.to_csv(r"D:\GITHUB\kotak-school-dbms\output_data\students_data.csv", index=False)

        student_list_df = df_sorted.drop_duplicates(subset="adm_no", keep="first")[
            [
                "adm_no", "name", "gender", "mother_name", "father_name",
                "pen_number", "dob", "phone_no", "religion", "caste",
                "sub_caste", "second_lang", "remarks", "student_aadhar", "father_aadhar", "mother_aadhar","apaar_id"
            ]
        ]

        student_list_df.to_csv(r"D:\GITHUB\kotak-school-dbms\output_data\student_list.csv", index=False)


        students_df = df[
            [
                "adm_no", "class_nos",
                "grade_id", "academic_year_id", "status_id","branch_id"
            ]
        ]


        print("✅ Cleaned and split data saved.")

        return student_list_df, students_df


    # --- Cell 7 ---

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

            df.to_sql(name=table_name, con=engine, if_exists='replace', index=False, method='multi', chunksize=500)

            with engine.connect() as conn:
                result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name};"))
                count = result.scalar()
                print(f"✅ Insert complete. 📊 Table '{table_name}' now contains {count} records.\n")

        except Exception as e:
            print(f"❌ Error updating table '{table_name}': {e}")


    # --- Cell 8 ---

    if __name__ == "__main__":
        print("🚀 Starting full student import pipeline...\n")

        merged_df = merge_and_tag()
        student_list_df, students_df = clean_data(merged_df)

        # Update master (student_list) and academic (students) tables
        update_database(students_df, "students")
        update_database(student_list_df, "student_list")

        print("🎉 All done! Both 'student_list' and 'students' tables updated successfully.")


    # --- Cell 9 ---

    # * Google Sheets Config (from .env)
    GOOGLE_JSON_FEE_DATA_PATHS = {
        "2024-25": os.getenv("GOOGLE_JSON_FEE_DATA_PATH_2024_25"),
        "2025-26": os.getenv("GOOGLE_JSON_FEE_DATA_PATH_2025_26"),
    }

    GOOGLE_JSON_FEE_PATHS = {
        "2024-25": os.getenv("GOOGLE_JSON_FEE_PATH_2024_25"),
        "2025-26": os.getenv("GOOGLE_JSON_FEE_PATH_2025_26"),
    }

    UNIQUE_KEY = os.getenv("UNIQUE_KEY")


    TABLE_NAME = "fees_table"


    # --- Cell 10 ---

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


    # --- Cell 11 ---

    ## **Merge and Tag Fees Data**
    def merge_and_tag():
        df_2024 = clean_column_names(fetch_data(
            GOOGLE_JSON_FEE_PATHS["2024-25"], "Overall Sheet", GOOGLE_JSON_FEE_DATA_PATHS["2024-25"]
        ))

        df_2025 = clean_column_names(fetch_data(
            GOOGLE_JSON_FEE_PATHS["2025-26"], "Overall Sheet", GOOGLE_JSON_FEE_DATA_PATHS["2025-26"]
        ))

        df_2024["academic_year"] = "2024-25"
        df_2025["academic_year"] = "2025-26"

        return pd.concat([df_2024, df_2025], ignore_index=True)


    # --- Cell 12 ---

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
        df = df.sort_values(by=["sno"])

        # 💰 Calculate total fees
        df["total_fees"] = df["total_fee_paid"] + df["discount_concession"] + df["total_fee_due"] + df["exempted"]

        # 🆔 Academic year mapping
        df['academic_year_id'] = df['academic_year'].apply(lambda x: 1 if x == "2024-25" else 2)
        df = df.sort_values(by=["academic_year_id", "classno", "student_name"], ascending=[True, True, True])

        # 📂 Save main fees report
        df.to_csv(r"D:\GITHUB\kotak-school-dbms\output_data\fees_report.csv", index=False)

        # ✅ Ensure payment_status column exists
        if "payment_status" not in df.columns:
            df["payment_status"] = "Unknown"

        # 📂 Create payment status table
        payment_status_df = df[["payment_status"]].sort_values(by="payment_status").drop_duplicates().reset_index(drop=True).copy()
        payment_status_df["payment_status_id"] = range(1, len(payment_status_df) + 1)
        payment_status_df = payment_status_df[["payment_status_id", "payment_status"]]
        payment_status_df.to_csv(r"D:\GITHUB\kotak-school-dbms\output_data\payment_status_table.csv", index=False)
        print("✅ Fees Report & Payment Status Table created successfully.\n")


        # 📂 Create staff child table
        df["staff"] = np.where(df['staff_name'].notnull() & df['staff_name'].str.strip().ne(''),1,0)    

        # ✅ Extract only staff records for the child table
        staff_child_df = df[df["staff"] == 1][["staff_name"]].drop_duplicates().reset_index(drop=True)

        # Assign staff IDs sequentially
        staff_child_df["staff_id"] = range(1, len(staff_child_df) + 1)

        # Save staff child table
        staff_child_df.to_csv(r"D:\GITHUB\kotak-school-dbms\output_data\staff_child_table.csv", index=False)
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


    # --- Cell 13 ---

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


    # --- Cell 14 ---

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
                if_exists='replace',
                index=False,
                method='multi',
                chunksize=1000
            )

            print(f"✅ {len(df)} records successfully inserted into '{TABLE_NAME}'.\n")

        except SQLAlchemyError as e:
            print(f"❌ An error occurred during database update: {e}")


    # --- Cell 15 ---

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


    # --- Cell 16 ---

    staff_child_df = pd.read_csv(r"D:\GITHUB\kotak-school-dbms\output_data\staff_child_table.csv")
    staff_child_df


    # --- Cell 17 ---

     # Load environment variables from .env

    print("✅ Libraries imported successfully")

    # --- LOGIN & TARGET URLs ---
    login_url = "https://app.myskoolcom.tech/kotak_vizag/login"
    urls_to_fetch = [
        "https://app.myskoolcom.tech/kotak_vizag/office_fee/fee_reports_day_wise_receipt_wise_print?academic_years_id=1",
        "https://app.myskoolcom.tech/kotak_vizag/office_fee/fee_reports_day_wise_receipt_wise_print?academic_years_id=7",
    ]

    TABLE_NAME = "daywise_fees_collection"

    credentials = {
        "uname": os.getenv("APP_UNAME"),
        "psw": os.getenv("APP_PSW")
    }

    OUTPUT_DIR = r"D:\GITHUB\kotak-school-dbms\output_data"
    os.makedirs(OUTPUT_DIR, exist_ok=True)


    # --- Cell 18 ---

    # --- FUNCTION: Determine Academic Year ---
    def get_academic_year_from_url(url):
        if "academic_years_id=1" in url:
            return "2024-25"
        elif "academic_years_id=7" in url:
            return "2025-26"
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


    # --- Cell 19 ---

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


    # --- Cell 20 ---

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
        df["academic_year_id"] = 1 if academic_year == "2024-25" else 2
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


    # --- Cell 21 ---

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
                if_exists='replace',
                index=False,
                method='multi',
                chunksize=1000
            )
            print(f"✅ {len(df)} records inserted into '{TABLE_NAME}' successfully.\n")

        except Exception as e:
            print(f"⚠️ Error inserting data: {e}")


    # --- Cell 22 ---

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


    # --- Cell 23 ---

    # 📌 Logging
    logging.basicConfig(filename="fee_collection_merge.log", level=logging.ERROR)

    # 🔐 Credentials & URLs
    login_url = "https://app.myskoolcom.tech/kotak_vizag/login"

    urls = {
        "2024_25": "https://app.myskoolcom.tech/kotak_vizag/office_fee/fee_consolidate_report_print?&from=2025-04-01&academic_years_id=1&status=1&imageField=Search",
        "2025_26": "https://app.myskoolcom.tech/kotak_vizag/office_fee/fee_consolidate_report_print?&from=2024-04-01&academic_years_id=7&status=1&imageField=Search"
    }

    TABLE_NAME = "fees_collection"


    # --- Cell 24 ---


    # 🔑 Login
    def login_to_website():
        session = requests.Session()
        response = session.post(login_url, data=credentials)
        if "Invalid" in response.text:
            print("❌ Login failed!")
            return None
        print("✅ Login successful!")
        return session


    # --- Cell 25 ---

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


    # --- Cell 26 ---

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

        df["academic_year_id"] = 1 if academic_year =="2024_25" else 2

        # df = df[~((df["AdmissionNo"].str.extract(r"(\d+)").astype(int) > 17164) & (df["academic_year_id"] == 1))].copy()

        df.to_csv(f"D:\\GITHUB\\kotak-school-dbms\\output_data\\fees_collection.csv", index=False)
        df = df.drop(columns=["Name"])
        return df


    # --- Cell 27 ---

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


    # --- Cell 28 ---

    # 🛢️ Insert into PostgreSQL
    def update_database(df, table_name):
        try:
            with engine.begin() as conn:
                print(f"⚠️ Deleting old records from '{table_name}'...")
                conn.execute(text(f"DELETE FROM {table_name};"))
                print(f"✅ Table '{table_name}' cleared.")
            df.columns = df.columns.str.lower()
            print(f"📥 Inserting {len(df)} rows...")
            df.to_sql(name=table_name, con=engine, if_exists='replace', index=False, method='multi', chunksize=1000)
            print(f"✅ Inserted into '{table_name}' successfully.")
        except Exception as e:
            print(f"❌ Error inserting: {e}")
            logging.error(f"Database insert error: {e}")
        finally:
            engine.dispose()


    # --- Cell 29 ---

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
        merged_df.to_csv("merged_fee_collection.csv", index=False)
        print("📁 Saved to merged_fee_collection.csv")

        # Ensure table exists
        ensure_fees_collection_table(engine, TABLE_NAME)
        print("✅ Fees collection table ensured.")
        # Push to DB
        update_database(merged_df, TABLE_NAME)
        print(f"✅ All done! Total records: {len(merged_df)}")

    if __name__ == "__main__":
        main()


    # --- Cell 30 ---




    # ------------------ Configuration ------------------
    login_url = "https://app.myskoolcom.tech/kotak_vizag/login"
    data_url_2024_25 = "https://app.myskoolcom.tech/kotak_vizag/office_fee/fee_discounts_report_receipt_wise_print?&academic_years_id=1"
    data_url_2025_26 = "https://app.myskoolcom.tech/kotak_vizag/office_fee/fee_discounts_report_receipt_wise_print?&academic_years_id=7"

    TABLE_NAME = "fee_concession_report"
    OUTPUT_PATH = r"D:\GITHUB\kotak-school-dbms\output_data\fee_concession_report.csv"


    # --- Cell 31 ---

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


    # --- Cell 32 ---

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


    # --- Cell 33 ---

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


    # --- Cell 34 ---

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

        df.to_csv(OUTPUT_PATH, index=False)
        print(f"✅ Cleaned data saved to {OUTPUT_PATH}\n")

        df = df.drop(columns=['student_name', "academic_year"], errors="ignore")

        return df


    # --- Cell 35 ---

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


    # --- Cell 36 ---

    def main():
        session = login_to_website()
        if session is None:
            return

        df_2024_25 = fetch_all_concession_tables(session, data_url_2024_25)
        df_2025_26 = fetch_all_concession_tables(session, data_url_2025_26)

        if df_2024_25 is None or df_2025_26 is None:
            print("❌ Could not fetch data for one or both academic years.")
            return

        df_2024_25["academic_year"] = "2024-25"
        df_2025_26["academic_year"] = "2025-26"

        merged_df = pd.concat([df_2024_25, df_2025_26], ignore_index=True)

        print("✅ Data extracted successfully! Cleaning data...\n")
        cleaned_df = clean_data(merged_df)

        output_file = r"D:\\GITHUB\\kotak-school-dbms\\output_data\\fee_concession_report_combined.csv"
        cleaned_df.to_csv(output_file, index=False)
        print(cleaned_df.columns)
        print(f"✅ Data saved to '{output_file}'\n")

        update_database(cleaned_df, TABLE_NAME, POSTGRES_CREDENTIALS)
        print(f"✅ {len(cleaned_df)} records entered into the database")

        print(cleaned_df.to_string())


    # --- Cell 37 ---

    # ------------------ Run Script ------------------
    if __name__ == "__main__":
        main()


    # --- Cell 38 ---




    # --- Cell 39 ---

    # ------------------ Configuration ------------------
    login_url = "https://app.myskoolcom.tech/kotak_vizag/login"
    data_url_2024_25 = "https://app.myskoolcom.tech/kotak_vizag/office_fee/fee_discounts_report_receipt_wise_print?&academic_years_id=1"
    data_url_2025_26 = "https://app.myskoolcom.tech/kotak_vizag/office_fee/fee_discounts_report_receipt_wise_print?&academic_years_id=7"

    TABLE_NAME = "fee_concession_report"
    OUTPUT_PATH = r"D:\GITHUB\kotak-school-dbms\output_data\fee_concession_report.csv"


    # --- Cell 40 ---

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


    # --- Cell 41 ---

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


    # --- Cell 42 ---

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


    # --- Cell 43 ---

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

        df.to_csv(OUTPUT_PATH, index=False)
        print(f"✅ Cleaned data saved to {OUTPUT_PATH}\n")

        df = df.drop(columns=['student_name', "academic_year"], errors="ignore")

        return df


    # --- Cell 44 ---

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


    # --- Cell 45 ---

    def main():
        session = login_to_website()
        if session is None:
            return

        df_2024_25 = fetch_all_concession_tables(session, data_url_2024_25)
        df_2025_26 = fetch_all_concession_tables(session, data_url_2025_26)

        if df_2024_25 is None or df_2025_26 is None:
            print("❌ Could not fetch data for one or both academic years.")
            return

        df_2024_25["academic_year"] = "2024-25"
        df_2025_26["academic_year"] = "2025-26"

        merged_df = pd.concat([df_2024_25, df_2025_26], ignore_index=True)

        print("✅ Data extracted successfully! Cleaning data...\n")
        cleaned_df = clean_data(merged_df)

        output_file = r"D:\\GITHUB\\kotak-school-dbms\\output_data\\fee_concession_report_combined.csv"
        cleaned_df.to_csv(output_file, index=False)
        print(cleaned_df.columns)
        print(f"✅ Data saved to '{output_file}'\n")

        update_database(cleaned_df, TABLE_NAME, POSTGRES_CREDENTIALS)
        print(f"✅ {len(cleaned_df)} records entered into the database")

        print(cleaned_df.to_string())


    # --- Cell 46 ---

    # ------------------ Run Script ------------------
    if __name__ == "__main__":
        main()


    # --- Cell 47 ---

    # ------------------ CONFIGURATION ------------------
    LOGIN_URL = "https://app.myskoolcom.tech/kotak_vizag/login"
    DATA_URL = "https://app.myskoolcom.tech/kotak_vizag/office_fee_new/daywise_atom_report/"
    CREDENTIALS = {"uname": "harikiran", "psw": "812551"}
    TABLE_NAME = "fee_transcation_atom_report"
    OUTPUT_PATH = r"D:\GITHUB\kotak-school-dbms\output_data\fee_transcation_atom_report.csv"


    # --- Cell 48 ---

    # ------------------ FUNCTIONS ------------------

    def login_to_portal(session: requests.Session, login_url: str, credentials: dict) -> None:
        """Logs into the portal and validates session."""
        print("🔑 Logging in...")
        resp = session.post(login_url, data=credentials)
        if "Dashboard" not in resp.text and resp.status_code != 200:
            raise Exception("❌ Login failed. Check credentials or login URL.")
        print("✅ Logged in successfully!")


    # --- Cell 49 ---

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


    # --- Cell 50 ---

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

        print("📊 Columns after cleaning:", df.columns.tolist())
        return df


    # --- Cell 51 ---

    def save_csv(df: pd.DataFrame, output_path: str) -> None:
        """Saves the DataFrame to a local CSV file."""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        df.to_csv(output_path, index=False)
        print(f"✅ CSV saved to {output_path}")


    # --- Cell 52 ---

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


    # --- Cell 53 ---

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


    # --- Cell 54 ---

    # ------------------ RUN SCRIPT ------------------
    if __name__ == "__main__":
        main()


    # --- Cell 55 ---

    file_path = r"D:\GITHUB\kotak-school-dbms\source_data\atom_report.xlsx"

    warnings.filterwarnings(
        "ignore",
        message="Workbook contains no default style",
        category=UserWarning,
        module="openpyxl"
    )

    df = pd.read_excel(file_path)

    df.head(3)


    # --- Cell 56 ---

    df.info()


    # --- Cell 57 ---

    dupes = df['Atom Txn ID'][df['Atom Txn ID'].duplicated(keep=False)]
    print(dupes)


    # --- Cell 58 ---

    df = (
        df.sort_values(['Atom Txn ID', 'Amount'], ascending=[True, False])
          .drop_duplicates(subset=['Atom Txn ID'], keep='first')
    )


    # --- Cell 59 ---

    dupes = df['Atom Txn ID'][df['Atom Txn ID'].duplicated(keep=False)]
    print(dupes)


    # --- Cell 60 ---

    df['Description'].unique()


    # --- Cell 61 ---

    df = df[df['Description'].isin(['TRANSACTION IS SUCCESSFUL', 'SUCCESS'])]


    # --- Cell 62 ---

    df['Description'].unique()


    # --- Cell 63 ---

    set_date = df[['Txn Date','Settlement Date','Settlement Date.1',]]
    set_date.head()


    # --- Cell 64 ---

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


    # --- Cell 65 ---

    df.info()


    # --- Cell 66 ---

    df.rename(columns={'UDFEX5':'admission_no', 'Udf1' : 'student_name', 'Udf2':'email', 'Udf3':'phone', 'UDFEX4' : 'amount in rupees', "Customer Acc. No.": "customer_acc_no",
        "GST (18%)": "gst_18"}, inplace=True)


    # --- Cell 67 ---

    df.head(1)


    # --- Cell 68 ---

    df.columns


    # --- Cell 69 ---

    df.columns = df.columns.str.strip().str.replace(" ", "_").str.lower()
    df.columns


    # --- Cell 70 ---

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


    # --- Cell 71 ---

    df.head()


    # --- Cell 72 ---

    output_path = r"D:\GITHUB\kotak-school-dbms\output_data\atom_report_cleaned.xlsx"
    df.to_excel(output_path, index=False)
    print(f"🧹 Cleaned Excel saved to: {output_path}")


    # --- Cell 73 ---

    df.info()


    # --- Cell 74 ---

    TABLE_NAME = "atom_transaction_report"

    # --- Step 1: Create Table (if not exists) ---
    with engine.begin() as conn:
        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
            id SERIAL PRIMARY KEY,
            admission_no BIGINT,
            student_name TEXT,
            phone BIGINT,
            amount NUMERIC(12,2),
            net_amount_to_be_paid NUMERIC(12,2),
            txn_date TIMESTAMP,
            settlement_date TIMESTAMP,
            description TEXT,
            txn_status TEXT,
            product TEXT,
            amount_in_rupees TEXT,
            customer_acc_no BIGINT,
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


    # --- Cell 75 ---

    atom_df = pd.read_excel(output_path)
    atom_df.head(3)


    # --- Cell 76 ---

    df = pd.read_csv(r"D:\GITHUB\kotak-school-dbms\output_data\daywise_fees_collection.csv")
    day_wise_df = df[df['payment_mode'] == 'Online Payment'].copy()
    day_wise_df


    # --- Cell 77 ---

    print(atom_df.columns)
    print(day_wise_df.columns)


    # --- Cell 78 ---

    atom_df["admission_no"] = atom_df["admission_no"].astype(str).str.strip()
    day_wise_df["AdmissionNo"] = day_wise_df["AdmissionNo"].astype(str).str.strip()


    # --- Cell 79 ---

    missing_in_daywise = set(atom_df["admission_no"]) - set(day_wise_df["AdmissionNo"])
    print("Missing count:", len(missing_in_daywise))


    # --- Cell 80 ---

    atom_missing_df = atom_df[atom_df["admission_no"].isin(missing_in_daywise)]
    atom_missing_df


    # --- Cell 81 ---

    atom_missing_df.columns


    # --- Cell 82 ---

    atom_missing_df = atom_missing_df[['admission_no', 'student_name', 'phone', 'amount',
           'net_amount_to_be_paid', 'txn_date', 'settlement_date', 'description']]

    atom_missing_df


    # --- Cell 83 ---

    TABLE_NAME = "atom_missing_records"

    # --- Step 1: Create Table (if not exists) ---
    with engine.begin() as conn:
        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
            id SERIAL PRIMARY KEY,
            admission_no BIGINT,
            student_name TEXT,
            phone BIGINT,
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


    # --- Cell 84 ---

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


    # --- Cell 85 ---

    import pandas as pd
    staff_child_df = pd.read_csv(r"D:\GITHUB\kotak-school-dbms\output_data\staff_child_table.csv")


    # --- Cell 86 ---

    upload_staff_table(staff_child_df,TABLE_NAME)


    # --- Cell 87 ---

    # 
    # import time
    # 
    # from datetime , timedelta
    # from selenium import webdriver
    # from selenium.webdriver.common.by import By
    # from selenium.webdriver.common.keys import Keys
    # from selenium.webdriver.chrome.service import Service
    # from selenium.webdriver.support.ui import WebDriverWait
    # from selenium.webdriver.support import expected_conditions as EC
    # from webdriver_manager.chrome import ChromeDriverManager


    # --- Cell 88 ---

    # # ✅ Config
    # login_url = "https://app.myskoolcom.tech/kotak_vizag/login"
    # attendance_url = "https://app.myskoolcom.tech/kotak_vizag/admin/attedance_grid"

    # credentials = {
    #     "uname": "harikiran",
    #     "psw": "812551"
    # }

    # download_folder = r"D:\GITHUB\kotak-school-dbms\source_data\Attendance Reports"
    # merged_output_path = os.path.join(download_folder, "MergedAttendance_2025_26.csv")

    # academic_ranges = {
    #     "2025-26": ("2025-06-16", datetime.today().strftime("%Y-%m-%d"))
    #     # "2025-26": ("2025-06-16", datetime.today().strftime("%Y-%m-%d"))
    # }


    # --- Cell 89 ---

    # # ✅ Setup Chrome Driver
    # chrome_options = webdriver.ChromeOptions()
    # prefs = {"download.default_directory": download_folder}
    # chrome_options.add_experimental_option("prefs", prefs)
    # driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    # wait = WebDriverWait(driver, 10)

    # # ✅ Functions
    # def login():
    #     driver.get(login_url)
    #     wait.until(EC.presence_of_element_located((By.NAME, "uname"))).send_keys(credentials["uname"])
    #     driver.find_element(By.NAME, "psw").send_keys(credentials["psw"])
    #     driver.find_element(By.NAME, "psw").send_keys(Keys.RETURN)
    #     print("✅ Logged in successfully!")
    #     time.sleep(5)

    # def set_date_range(start, end):
    #     driver.get(attendance_url)
    #     time.sleep(2)
    #     from_date_input = wait.until(EC.presence_of_element_located((By.ID, "from_attendance_date")))
    #     driver.execute_script("arguments[0].removeAttribute('readonly')", from_date_input)
    #     from_date_input.clear()
    #     from_date_input.send_keys(start)

    #     to_date_input = wait.until(EC.presence_of_element_located((By.ID, "to_attendance_date")))
    #     driver.execute_script("arguments[0].removeAttribute('readonly')", to_date_input)
    #     to_date_input.clear()
    #     to_date_input.send_keys(end)

    #     print(f"✅ Date range set: {start} to {end}")

    # def download_csv(filename):
    #     try:
    #         if os.path.exists(filename):
    #             os.remove(filename)
    #         download_button = wait.until(EC.element_to_be_clickable((By.ID, "smaplecsv")))
    #         download_button.click()
    #         time.sleep(8)
    #         downloaded = sorted(
    #             [f for f in os.listdir(download_folder) if f.endswith(".csv")],
    #             key=lambda x: os.path.getctime(os.path.join(download_folder, x)),
    #             reverse=True
    #         )[0]
    #         os.rename(os.path.join(download_folder, downloaded), filename)
    #         print(f"✅ Downloaded and renamed to: {filename}")
    #     except Exception as e:
    #         print(f"❌ Error downloading file: {e}")

    # def date_batches(start, end, months=1):
    #     start_date = datetime.strptime(start, "%Y-%m-%d")
    #     end_date = datetime.strptime(end, "%Y-%m-%d")
    #     while start_date < end_date:
    #         batch_end = min(start_date + timedelta(days=30 * months), end_date)
    #         yield (start_date.strftime("%Y-%m-%d"), batch_end.strftime("%Y-%m-%d"))
    #         start_date = batch_end + timedelta(days=1)

    # def merge_csvs(folder, output_file, year_filter="2025-26"):
    #     all_csvs = [
    #         os.path.join(folder, f)
    #         for f in os.listdir(folder)
    #         if f.endswith(".csv") and year_filter in f
    #     ]

    #     merged_df = pd.DataFrame()

    #     for f in all_csvs:
    #         try:
    #             df = pd.read_csv(f, low_memory=False)
    #             if "Students Number" in df.columns:
    #                 # Merge logic: remove duplicates by date + student number
    #                 df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    #                 df = df.dropna(subset=["Date", "Students Number"])

    #                 # Merge with deduplication
    #                 if not merged_df.empty:
    #                     merged_df = pd.concat([merged_df, df], ignore_index=True)
    #                     merged_df.drop_duplicates(subset=["Date", "Students Number"], keep="last", inplace=True)
    #                 else:
    #                     merged_df = df
    #                 print(f"🔄 Merged file (with Students Number): {os.path.basename(f)}")
    #             else:
    #                 # Append directly if "Students Number" not found
    #                 merged_df = pd.concat([merged_df, df], ignore_index=True)
    #                 print(f"➕ Appended file (no Students Number): {os.path.basename(f)}")
    #         except Exception as e:
    #             print(f"❌ Error reading file {f}: {e}")

    #     merged_df.to_csv(output_file, index=False)
    #     print(f"✅ Final merged file saved: {output_file}")

    #     # ✅ MAIN Execution
    # login()

    # # ✅ MAIN Execution
    # login()

    # for year, (start, end) in academic_ranges.items():
    #     print(f"\n📅 Downloading attendance for {year}")
    #     for i, (s, e) in enumerate(date_batches(start, end)):
    #         s_fmt = datetime.strptime(s, "%Y-%m-%d")
    #         e_fmt = datetime.strptime(e, "%Y-%m-%d")
    #         filename = f"Attendance_{year}_{s_fmt.strftime('%b')}_{e_fmt.strftime('%b')}.csv"
    #         filepath = os.path.join(download_folder, filename)
    #         set_date_range(s_fmt.strftime("%Y-%m-%d"), e_fmt.strftime("%Y-%m-%d"))
    #         download_csv(filepath)

    # # ❌ No merging now – only individual files will be downloaded and renamed
    # # merge_csvs(download_folder, merged_output_path, year_filter="2025-26")

    # driver.quit()
    # print("✅ All attendance downloads complete – individual files saved!")


    # --- Cell 90 ---

    # 
    # from sqlalchemy import create_engine
    # 
    # 
    # import urllib
    # import traceback
    # from datetime 


    # # * Configure logging
    # logging.basicConfig(filename=r"D:\GITHUB\kotak-school-dbms\output_data\attendance_report.log", level=logging.ERROR, 
    #                     format="%(asctime)s - %(levelname)s - %(message)s")


    # --- Cell 91 ---

    # 

    # def load_and_clean_data(file1, file2, file3=None, file4=None, file5=None):
    #     # Load DataFrames (read as str to avoid DtypeWarning)
    #     dfs = [pd.read_csv(f, dtype=str) for f in [file1, file2, file3, file4, file5] if f is not None]

    #     # Clean column names
    #     for i in range(len(dfs)):
    #         dfs[i].columns = dfs[i].columns.str.strip().str.replace('"', '', regex=False)

    #         # Strip spaces from all string columns
    #         dfs[i] = dfs[i].apply(lambda x: x.str.strip() if x.dtype == "object" else x)

    #         # 🛠 Date cleaning (if column exists)
    #         if 'Date' in dfs[i].columns:
    #             dfs[i]['Date'] = pd.to_datetime(dfs[i]['Date'], dayfirst=True, errors='coerce')

    #             # Warn about invalid dates
    #             bad_dates = dfs[i][dfs[i]['Date'].isna()]
    #             if not bad_dates.empty:
    #                 print(f"⚠️ Invalid dates found in file {i+1}:")
    #                 print(bad_dates[['Date']].head(10))  # Show first 10

    #     # Merge logic
    #     base_df = dfs[0]
    #     for df in dfs[1:]:
    #         conflict_cols = [col for col in df.columns if col in base_df.columns and col != 'Students Number']
    #         df = df.drop(columns=conflict_cols, errors='ignore')
    #         base_df = base_df.merge(df, on="Students Number", how="outer")

    #     df = base_df

    #     # Merge fields like Name, Class if duplicated
    #     for field in ['Name', 'Class']:
    #         col_x, col_y = f"{field}_x", f"{field}_y"
    #         if col_x in df.columns and col_y in df.columns:
    #             df[field] = df[col_x].combine_first(df[col_y])
    #             df.drop([col_x, col_y], axis=1, inplace=True)
    #         elif col_x in df.columns:
    #             df[field] = df.pop(col_x)
    #         elif col_y in df.columns:
    #             df[field] = df.pop(col_y)

    #     # Drop remaining _x/_y columns
    #     df = df.drop(columns=[col for col in df.columns if col.endswith('_x') or col.endswith('_y')], errors='ignore')

    #     # Rename key identifier
    #     df = df.rename(columns={"Students Number": "AdmissionNo"})

    #     # Drop unnecessary columns
    #     drop_cols = ['Present Days', 'Absent Days', 'Toral Working Days']
    #     df = df.drop(columns=[col for col in drop_cols if col in df.columns], errors='ignore')

    #     # Reorder columns
    #     key_cols = ['AdmissionNo', 'Name', 'Class']
    #     other_cols = [col for col in df.columns if col not in key_cols]
    #     df = df[key_cols + other_cols]

    #     return df


    # --- Cell 92 ---


    # def process_attendance_data(df):
    #     # * Step 1: Clean AdmissionNo (remove 786 and purely alphabetical ones)
    #     df = df[~(df["AdmissionNo"].astype(str) == "786") & ~df["AdmissionNo"].astype(str).str.match(r"^[a-zA-Z]+$")].copy()

    #     # * Step 2: Clean Class name (remove ICSE wrapper)
    #     df["Class"] = df["Class"].astype(str).str.replace(r"ICSE \((.*?)\)", r"\1", regex=True)

    #     # * Step 3: Load class info with academic year
    #     student_df = pd.read_csv(r"D:\GITHUB\kotak-school-dbms\output_data\fees_report.csv")[["adm_no", "academic_year_id", "class"]]
    #     print("✅ Students Before Merging\n", len(df["AdmissionNo"].unique()))
    #     df = df[df["AdmissionNo"].isin(student_df["adm_no"])]
    #     print("✅ Students After Merging\n", len(df["AdmissionNo"].unique()))

    #     # * Step 4: Unpivot attendance columns to Date-wise rows
    #     df_unpivot = pd.melt(df, id_vars=["AdmissionNo", "Name", "Class"], var_name="Date", value_name="AttendanceStatus")
    #     df_unpivot["Date"] = pd.to_datetime(df_unpivot["Date"], format='%d.%m.%Y', errors='coerce')

    #     # * Step 5: Remove invalid past records for new students
    #     numeric_mask = df_unpivot["AdmissionNo"].str.isnumeric()
    #     df_unpivot.loc[numeric_mask, "adm_no_int"] = df_unpivot.loc[numeric_mask, "AdmissionNo"].astype(int)
    #     df_unpivot = df_unpivot[
    #         ~((df_unpivot["Date"] < datetime(2024, 4, 1)) & (df_unpivot["adm_no_int"] > 17165))
    #     ]
    #     df_unpivot.drop(columns=["adm_no_int"], inplace=True)

    #     df_unpivot["id"] = range(1, len(df_unpivot) + 1)

    #     if df_unpivot["Date"].isna().sum() > 0:
    #         print("⚠️ Warning: Some Date values were invalid and converted to NaT.")

    #     df_unpivot = df_unpivot.sort_values("Date", ascending=False).reset_index(drop=True)

    #     # * Step 6: Mark "Not Joined"
    #     first_attendance_dates = df_unpivot[df_unpivot['AttendanceStatus'].notna()].groupby('AdmissionNo')['Date'].min()
    #     df_unpivot['AttendanceStatus'] = df_unpivot.apply(
    #         lambda row: "Not Joined" if row['Date'] < first_attendance_dates.get(row['AdmissionNo'], row['Date']) else row['AttendanceStatus'],
    #         axis=1
    #     )

    #     # * Step 7: Prioritize and deduplicate attendance
    #     priority_map = {'P': 2, 'A': 1, 'H': 3, 'Not Joined': 4, 'TC': 5}
    #     df_unpivot['Priority'] = df_unpivot["AttendanceStatus"].map(priority_map)
    #     df_unpivot = df_unpivot.sort_values(by=['AdmissionNo', 'Date', 'Priority']) \
    #                            .drop_duplicates(subset=['AdmissionNo', 'Date'], keep='first') \
    #                            .drop(columns=['Priority'])

    #     # * Step 8: Clean Class + Standardize AttendanceStatus
    #     df_unpivot['Class'] = df_unpivot['Class'].str.replace("Pre KG - ", "Pre KG")
    #     df_unpivot["AttendanceStatus"] = df_unpivot["AttendanceStatus"].replace({
    #         'P': "Present", 'A': "Absent", 'H': "Holiday"
    #     })
    #     df_unpivot.sort_values(by=['Date'], ascending=False, inplace=True)

    #     # * Step 9: Assign academic year from Date
    #     df_unpivot['academic_year_id'] = df_unpivot['Date'].apply(
    #         lambda d: 1 if pd.Timestamp("2024-07-17") <= d <= pd.Timestamp("2025-03-31")
    #         else 2 if pd.Timestamp("2025-06-16") <= d <= pd.Timestamp(datetime.today().date())
    #         else ""
    #     )

    #     # * Step 10: Assign ClassNo by academic year
    #     student_df["adm_no"] = student_df["adm_no"].astype(str)
    #     lookup_2024 = student_df[student_df["academic_year_id"] == 1]
    #     lookup_2025 = student_df[student_df["academic_year_id"] == 2]

    #     lookup_map_2024 = {row["adm_no"]: row["class"] for _, row in lookup_2024.iterrows()}
    #     lookup_map_2025 = {row["adm_no"]: row["class"] for _, row in lookup_2025.iterrows()}

    #     class_mapping = {
    #         "Pre KG": 1, "LKG - A": 2, "LKG - B": 3, "UKG - A": 4, "UKG - B": 5, "UKG - C": 6,
    #         "I - A": 7, "I - B": 8, "I - C": 9, "I - D": 10,
    #         "II - A": 11, "II - B": 12, "II - C": 13, "II - D": 14,
    #         "III - A": 15, "III - B": 16, "III - C": 17, "III - D": 18,
    #         "IV - A": 19, "IV - B": 20, "IV - C": 21, "IV - D": 22,
    #         "V - A": 23, "V - B": 24, "V - C": 25, "V - D": 26,
    #         "VI - A": 27, "VI - B": 28, "VI - C": 29, "VI - D": 30,
    #         "VII - A": 31, "VII - B": 32, "VII - C": 33, "VII - D": 34,
    #         "VIII - A": 35, "VIII - B": 36, "VIII - C": 37, "VIII - D": 38,
    #         "IX - A": 39, "IX - B": 40, "IX - C": 41,
    #         "X - A": 42, "X - B": 43, "X - C": 44
    #     }

    #     def get_class_no_2024(adm_no):
    #         class_name = lookup_map_2024.get(str(adm_no), "")
    #         return class_mapping.get(class_name, np.nan)

    #     def get_class_no_2025(adm_no):
    #         class_name = lookup_map_2025.get(str(adm_no), "")
    #         return class_mapping.get(class_name, np.nan)

    #     df_2024 = df_unpivot[df_unpivot["academic_year_id"] == 1].copy()
    #     df_2025 = df_unpivot[df_unpivot["academic_year_id"] == 2].copy()

    #     valid_adm_nos_2025 = set(lookup_map_2025.keys())
    #     df_2025 = df_2025[df_2025["AdmissionNo"].astype(str).isin(valid_adm_nos_2025)].copy()

    #     df_2024["ClassNo"] = df_2024["AdmissionNo"].apply(get_class_no_2024)
    #     df_2025["ClassNo"] = df_2025["AdmissionNo"].apply(get_class_no_2025)

    #     df_unpivot = pd.concat([df_2024, df_2025], ignore_index=True)
    #     df_unpivot["ClassNo"] = df_unpivot["ClassNo"].fillna(0).astype(int)

    #     # * Step 11: Grade level (classId)
    #     grade_mapping = [
    #         ("Pre KG", 1), ("LKG", 2), ("UKG", 3),
    #         ("I", 4), ("II", 5), ("III", 6), ("IV", 7), ("V", 8),
    #         ("VI", 9), ("VII", 10), ("VIII", 11), ("IX", 12), ("X", 13)
    #     ]
    #     conditions = [df_unpivot['Class'].str.contains(fr"\b{k}\b", na=False, regex=True) for k, _ in grade_mapping]
    #     choices = [v for _, v in grade_mapping]
    #     df_unpivot['classId'] = np.select(conditions, choices, default=0).astype(int)

    #     # * Step 12: AttendanceStatusId
    #     AttendanceStatus_mapping = [("Absent", 1), ("Present", 2), ("Not Joined", 3), ("Holiday", 4)]
    #     conditions = [df_unpivot['AttendanceStatus'].str.contains(k, na=False) for k, _ in AttendanceStatus_mapping]
    #     choices = [v for _, v in AttendanceStatus_mapping]
    #     df_unpivot['AttendanceStatusId'] = np.select(conditions, choices, default=0).astype(int)

    #     # * Step 13: BranchId
    #     branch_mapping = [
    #         ('Pre KG', 1), ('LKG', 1), ('UKG', 1),
    #         ('I', 2), ('II', 2), ('III', 2), ('IV', 2), ('V', 2),
    #         ('VI', 3), ('VII', 3), ('VIII', 3), ('IX', 3), ('X', 3)
    #     ]
    #     conditions = [df_unpivot['Class'].str.contains(fr"\b{k}\b", na=False, regex=True) for k, _ in branch_mapping]
    #     choices = [v for _, v in branch_mapping]
    #     df_unpivot['branchId'] = np.select(conditions, choices, default=0).astype(int)

    #     # ✅ Final output
    #     df_unpivot = df_unpivot[[
    #         "id", "Date", "AdmissionNo", "ClassNo", "classId", "branchId", "AttendanceStatusId", "academic_year_id"
    #     ]]
    #     df_unpivot.columns = [c.lower() for c in df_unpivot.columns]

    #     print(f"✅ Processed data with {len(df_unpivot)} rows.")
    #     print(f"✅ Columns are:\n {df_unpivot.columns}")
    #     return df_unpivot


    # --- Cell 93 ---

    # from sqlalchemy import text

    # def ensure_table_exists():
    #     create_table_sql = f"""
    #     CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
    #         id SERIAL PRIMARY KEY,
    #         date DATE,
    #         admissionno TEXT,
    #         classno INTEGER,
    #         classid INTEGER,
    #         branchid INTEGER,
    #         attendancestatusid INTEGER,
    #         academic_year_id INTEGER
    #     );
    #     """
    #     try:
    #         with engine.begin() as connection:  # ✅ ensures DDL is committed
    #             connection.execute(text(create_table_sql))
    #         print(f"✅ Table '{TABLE_NAME}' ensured.")
    #     except Exception as e:
    #         print(f"❌ Failed to create or check table '{TABLE_NAME}': {e}")


    # --- Cell 94 ---

    # # Create database engine
    # password = urllib.parse.quote(POSTGRES_CREDENTIALS["password"])
    # engine = create_engine(
    #     f"postgresql+psycopg2://{POSTGRES_CREDENTIALS['username']}:{password}"
    #     f"@{POSTGRES_CREDENTIALS['host']}:{POSTGRES_CREDENTIALS['port']}/{POSTGRES_CREDENTIALS['database']}"
    # )

    # def update_database(df):
    #     """Use PostgreSQL COPY for ultra-fast data insertion."""
    #     csv_path = (r"D:\GITHUB\kotak-school-dbms\output_data\attendance_report.csv")

    #     # ✅ Ensure column names are lowercase to match table definition
    #     df.columns = [c.lower() for c in df.columns]

    #     # ✅ Save DataFrame to CSV
    #     df.to_csv(csv_path, index=False, header=False)

    #     try:
    #         conn = engine.raw_connection()
    #         cursor = conn.cursor()

    #         print(f"🔄 Truncating table: {TABLE_NAME}")
    #         cursor.execute(f"TRUNCATE TABLE {TABLE_NAME};")
    #         conn.commit()

    #         with open(csv_path, "r") as f:
    #             cursor.copy_from(f, TABLE_NAME, sep=",")  # ✅ lowercase and unquoted

    #         conn.commit()
    #         cursor.close()
    #         conn.close()

    #         print(f"✅ Data copied to '{TABLE_NAME}' using COPY command!")

    #     except Exception as e:
    #         print(f"❌ COPY failed: {e}")
    #         logging.error(traceback.format_exc())


    # --- Cell 95 ---

    # def main():
    #     # 📌 Already-clean 2024-25 data
    #     file_2024_25 = r"D:\GITHUB\kotak-school-dbms\output_data\attendance_report_2024_25.csv"

    #     # 📌 Raw 2025-26 files
    #     file4 = r"D:\GITHUB\kotak-school-dbms\source_data\Attendance Reports\Attendance_2025-26_Jun_Jul.csv"
    #     file5 = r"D:\GITHUB\kotak-school-dbms\source_data\Attendance Reports\Attendance_2025-26_Jul_Aug.csv"

    #     output_file = r"D:\GITHUB\kotak-school-dbms\output_data\attendance_report.csv"

    #     try:
    #         print("📂 Loading already-clean 2024-25 data...\n")
    #         df_2024 = pd.read_csv(file_2024_25)
    #         print(f"✅ 2024-25 data loaded with {df_2024.shape[0]} rows.")

    #         print("\n🛠 Cleaning and loading 2025-26 raw files...\n")
    #         df_2025 = load_and_clean_data(file4, file5)  # No need to pass None for unused files
    #         print(f"✅ 2025-26 data cleaned with {df_2025.shape[0]} rows.")

    #         # 📌 Combine datasets
    #         df = pd.concat([df_2024, df_2025], ignore_index=True)
    #         print(f"\n🔄 Combined dataset has {df.shape[0]} rows.\n")

    #         # 📌 Process attendance data
    #         print("⚙️ Processing attendance data...\n")
    #         df_unpivot = process_attendance_data(df)
    #         df_unpivot.to_csv(output_file, index=False)

    #         print(f"✅ Processed data saved with {df_unpivot.shape[0]} rows.\n")
    #         print("✅ Columns are:\n", df_unpivot.columns)
    #         if not df_unpivot.empty:
    #             print("📅 Max date in dataset:", df_unpivot["date"].max())
    #         print(df_unpivot.head())

    #         # 📌 Update database
    #         print("\n💾 Updating database...\n")
    #         ensure_table_exists()
    #         update_database(df_unpivot)

    #         print("\n🎯 Attendance report processing completed successfully!")
    #         print(f"📊 Final row count: {df_unpivot.shape[0]}\n")

    #     except Exception as e:
    #         print(f"❌ An unexpected error occurred: {e}\n")
    #         logging.error(f"❌ Unexpected error: {e}\n")


    # # Run script
    # main()


    # --- Cell 96 ---

    # 
    # 

    # POSTGRES_CREDENTIALS = {
    #     "username": "postgres",
    #     "password": "Hari@123",
    #     "host": "localhost",
    #     "port": "5432",
    #     "database": "ksdb",
    # }
    # TABLE_NAME = "class_table"


    # --- Cell 97 ---

    # df = pd.read_csv(r"D:\GITHUB\kotak-school-dbms\output_data\class_section_grade_table.csv")
    # # df["ClassNo"] = df["ClassNo"].astype(int)
    # df.head()


    # --- Cell 98 ---

    # df.columns


    # --- Cell 99 ---

    # import time
    # import traceback
    # 
    # 
    # import urllib
    # import io
    # 
    # from sqlalchemy.exc import OperationalError

    # # Retry settings
    # MAX_RETRIES = 3
    # RETRY_DELAY = 5  # Seconds

    # def bulk_insert_postgres(df, conn, table_name):
    #     """Fast bulk insert using PostgreSQL COPY command."""
    #     with conn.connection.cursor() as cur:
    #         output = io.StringIO()
    #         df.to_csv(output, sep="\t", index=False, header=False)
    #         output.seek(0)
    #         cur.copy_from(output, table_name, sep="\t", null="NULL")
    #         conn.connection.commit()

    # def update_database(df):
    #     """Insert attendance data into PostgreSQL database with retry logic."""
    #     password = urllib.parse.quote(POSTGRES_CREDENTIALS["password"])
    #     engine = create_engine(f"postgresql+psycopg2://{POSTGRES_CREDENTIALS['username']}:{password}"
    #                            f"@{POSTGRES_CREDENTIALS['host']}:{POSTGRES_CREDENTIALS['port']}/{POSTGRES_CREDENTIALS['database']}")

    #     for attempt in range(1, MAX_RETRIES + 1):
    #         try:
    #             print(f"🔄 Attempt {attempt}: Connecting to database {POSTGRES_CREDENTIALS['database']} at {POSTGRES_CREDENTIALS['host']}...")
    #             with engine.begin() as conn:
    #                 print(f"✅ Connection established.")

    #                 # Create Table if it does not exist
    #                 print(f"Checking if table '{TABLE_NAME}' exists...")

    #                 # Truncate the table before inserting data
    #                 print(f"Truncating existing table: {TABLE_NAME}")
    #                 conn.execute(text(f"TRUNCATE TABLE {TABLE_NAME} CASCADE;"))

    #                 print(f"Deleting data from {TABLE_NAME} table...")
    #                 conn.execute(text(f"DELETE FROM {TABLE_NAME};"))


    #                 # Fast Bulk Insert
    #                 print(f"Inserting data into {TABLE_NAME} table...")
    #                 bulk_insert_postgres(df, conn, TABLE_NAME)

    #                 print(f"✅ Data successfully inserted into '{TABLE_NAME}' table.")
    #                 return  # Exit function if successful

    #         except OperationalError as e:
    #             print(f"❌ OperationalError: {e}")
    #             logging.error(f"❌ OperationalError: {e}")
    #             logging.error("Error Traceback:\n" + traceback.format_exc())

    #             if attempt < MAX_RETRIES:
    #                 print(f"🔄 Retrying in {RETRY_DELAY} seconds...")
    #                 time.sleep(RETRY_DELAY)
    #             else:
    #                 print("❌ Max retries reached. Could not update the database.")
    #                 logging.error("❌ Max retries reached. Could not update the database.")
    #                 return


    # --- Cell 100 ---

    # update_database(df)


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logging.exception('Script failed')
        raise
