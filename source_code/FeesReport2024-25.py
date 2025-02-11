#!/usr/bin/env python
# coding: utf-8

# <h1 align="center"><b>KOTAK SALESIAN SCHOOL</b></h1>
# 

# <h2 align="center"><b>STUDENTS INFO 2024-25</b></h2>

# ### **Backup Files Before running New**

# In[1]:


import os
import datetime

# MySQL Credentials
DB_USER = "root"
DB_PASSWORD = "Hari@123"
DB_NAME = "schooldb"
BACKUP_DIR = "D:/mysql_backups"  # Directory to save backups in

# Ensure the backup directory exists
if not os.path.exists(BACKUP_DIR):
    os.makedirs(BACKUP_DIR)

# Generate a timestamp for the backup file
timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
backup_file = f"{BACKUP_DIR}/backup_{DB_NAME}_{timestamp}.sql"

# Run MySQL Dump Command
dump_command = f"mysqldump -u {DB_USER} -p{DB_PASSWORD} {DB_NAME} > {backup_file}"
os.system(dump_command)

print(f"Backup saved to {backup_file}")


# ### **Import Libraries & Define Credentials**

# In[2]:


import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from sqlalchemy import create_engine, text
import urllib.parse

GOOGLE_JSON_PATH = r"D:\GITHUB\kotak-school-dbms\google_api_keys\woven-solution-446513-f2-6700b7a9f290.json"
GOOGLE_SHEET_NAME = "Fee Reports 2024-25"
MYSQL_CREDENTIALS = {
    "username": "root",
    "password": "Hari@123",
    "host": "localhost",
    "port": "3306",
    "database": "schooldb",
}
TABLE_NAME = "students_2024_25"


# ### **Extract Data from Google Sheet**

# In[3]:


def fetch_data(sheet_name="Sheet1"):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_JSON_PATH, scope)
    client = gspread.authorize(creds)

    try:
        # Open the Google Spreadsheet
        spreadsheet = client.open("STUDENTS DETAILS 2024-25")
        
        # Open the specific sheet (default is Sheet1)
        sheet = spreadsheet.worksheet("Overall")
    except gspread.SpreadsheetNotFound:
        raise Exception("❌ Spreadsheet not found! Ensure the name is correct and the service account has access.")
    except gspread.WorksheetNotFound:
        raise Exception(f"❌ Worksheet '{sheet_name}' not found! Ensure the name matches exactly.")
    
    # Fetch data
    data = sheet.get_all_records(head=3)
    return pd.DataFrame(data)


# In[4]:


# Fetch data
student_info = fetch_data()

student_info.head()


# ### **Clean Extracted Data**

# In[5]:


import pandas as pd

def clean_data(df):
    # Make a copy to avoid SettingWithCopyWarning
    df = df.copy()

    # Rename columns
    df.columns = [
        'SNo', 'AdmissionNo', 'STUDENT_NAME', 'Class', 'Gender', 'MotherName', 
        'FatherName', 'PenNo', 'DOB', 'Mobile', 'Religion', 'Caste', 
        'SubCaste', 'IIndLang', 'Remarks', 'ClassNo', 'JoinedYear', "APAAR Status"
    ]

    # Keep only valid date formats (DD-MM-YYYY)
    #df = df[df["DOB"].str.match(r'^\d{1,2}-\d{1,2}-\d{4}$', na=False)]

    # Convert DOB to MySQL format (YYYY-MM-DD)
    df["DOB"] = pd.to_datetime(df["DOB"], format="%d-%m-%Y", errors='coerce').dt.strftime("%Y-%m-%d")

    # Sort by ClassNo first, then SNo for logical ordering
    df = df.sort_values(by=["ClassNo", "SNo"], ascending=[True, True])

    # Drop 'APAAR Status' column if it exists
    if "APAAR Status" in df.columns:
        df = df.drop(columns=["APAAR Status"])

    # Reset SNo after sorting
    df["SNo"] = range(1, len(df) + 1)

    # Convert 'JoinedYear' safely to integer (handling empty values)
    df["JoinedYear"] = pd.to_numeric(df["JoinedYear"], errors="coerce").astype("Int64")
    
    df.to_csv(r"D:\GITHUB\kotak-school-dbms\output_data\students_table_2024_25.csv", index=False)

    return df


# ### **Update MySQL Database**

# In[6]:


def update_database(df):
    password = urllib.parse.quote(MYSQL_CREDENTIALS["password"])
    engine = create_engine(f"mysql+pymysql://{MYSQL_CREDENTIALS['username']}:{password}"
                           f"@{MYSQL_CREDENTIALS['host']}:{MYSQL_CREDENTIALS['port']}/{MYSQL_CREDENTIALS['database']}")

    try:
        with engine.connect() as conn:
            # Step 3: Truncate the table
            conn.execute(text(f"TRUNCATE TABLE {TABLE_NAME};"))
            print(f"✅ All records from the '{TABLE_NAME}' table have been deleted.\n")

            # Step 4: Add unique constraint
            conn.execute(text(f"ALTER TABLE {TABLE_NAME} ADD UNIQUE (AdmissionNo);\n"))
            print(f"✅ Unique constraint added to ADM_NO in the '{TABLE_NAME}' table.\n")

            # Step 5: Insert data into the table
            df.to_sql(name=TABLE_NAME, con=engine, if_exists='append', index=False)
            print(f"✅ Data successfully inserted into the '{TABLE_NAME}' table.\n")

            # Step 6: Sort the table by ClassNo and SNo (in MySQL)
            conn.execute(text(f"ALTER TABLE {TABLE_NAME} ORDER BY ClassNo ASC, SNo ASC;"))
            print(f"✅ Data in the '{TABLE_NAME}' table sorted by ClassNo and SNo.\n")

    except Exception as e:
        print(f"An error occurred: {e}")



# ### **Run the Main Function**

# In[7]:


if __name__ == "__main__":
    
    # Fetch data
    student_info = fetch_data()
    print("✅ Data fetched successfully.\n")

    # Clean data
    student_info = clean_data(student_info)
    print("✅ Data cleaned successfully.\n")
    print("✅ Columns are:\n",student_info.columns)

    # Update database
    update_database(student_info)
    print("✅ Process completed successfully.\n")

    # Print the full DataFrame
    #print(student_info.to_string())  # Print the entire DataFrame in a readable format


# <h2 align="center"><b>FEE REPORT 2024-25</b></h2>

# #### **Google Console Service Account: myschooldb@woven-solution-446513-f2.iam.gserviceaccount.com**

# ### **Import Necessary Libraries & Define Global Variables**

# In[8]:


import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from sqlalchemy import create_engine, text
import urllib.parse

GOOGLE_JSON_PATH = r"D:\GITHUB\kotak-school-dbms\google_api_keys\woven-solution-446513-f2-5ffd100e19c7.json"
GOOGLE_SHEET_NAME = "Fee Reports 2024-25"
MYSQL_CREDENTIALS = {
    "username": "root",
    "password": "Hari@123",
    "host": "localhost",
    "port": "3306",
    "database": "schooldb",
}
TABLE_NAME = "fees_table_2024_25"


# ### **Function for Fetching Data**

# In[9]:


def fetch_data(sheet_name="Sheet1"):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_JSON_PATH, scope)
    client = gspread.authorize(creds)

    try:
        # Open the Google Spreadsheet
        spreadsheet = client.open("Fee Reports 2024-25")
        
        # Open the specific sheet (default is Sheet1)
        sheet = spreadsheet.worksheet("Overall Sheet")
    except gspread.SpreadsheetNotFound:
        raise Exception("❌ Spreadsheet not found! Ensure the name is correct and the service account has access.")
    except gspread.WorksheetNotFound:
        raise Exception(f"❌ Worksheet '{sheet_name}' not found! Ensure the name matches exactly.")
    
    # Fetch data
    data = sheet.get_all_records(head=3)
    return pd.DataFrame(data)


# ### **Function for Cleaning Data**

# In[10]:


def clean_data(df):
    df = df[:-1][:-6]
    df.columns = ['SNo', 'STUDENT_NAME', 'ADM_NO', 'FB_NO', 'CLASS',
                  'Term1', 'Term2', 'Term3', 'Term4', 'TotalFeePaid',
                  'Discount_Concession', 'TotalFeeDue', 'PermissionUpto',
                  'Fine', 'PaymentStatus', 'ClassNo',"AcNo"]

    columns_to_convert = ["Term1", "Term2", "Term3", "Term4", "TotalFeePaid",
                          "Discount_Concession", "TotalFeeDue", "Fine"]
    df[columns_to_convert] = df[columns_to_convert].apply(pd.to_numeric, errors='coerce').fillna(0)

    df = df.drop(columns=["AcNo"])

    df["SNo"] = range(1, len(df) + 1)

    df = df.sort_values(by=["SNo"])

    df["TotalFees"] = df["TotalFeePaid"] + df["Discount_Concession"] + df["TotalFeeDue"]
    
    df.to_csv(r"D:\GITHUB\kotak-school-dbms\output_data\fees_report_2024_25.csv", index=False)
    
    df.drop(columns=["PermissionUpto"], inplace=True)
    

    return df


# ### **Function for Updating the Database**

# In[11]:


def update_database(df):
    password = urllib.parse.quote(MYSQL_CREDENTIALS["password"])
    engine = create_engine(f"mysql+pymysql://{MYSQL_CREDENTIALS['username']}:{password}"
                           f"@{MYSQL_CREDENTIALS['host']}:{MYSQL_CREDENTIALS['port']}/{MYSQL_CREDENTIALS['database']}")

    try:
        with engine.connect() as conn:
            conn.execute(text(f"TRUNCATE TABLE {TABLE_NAME};"))
            print(f"✅ All records from the '{TABLE_NAME}' table have been deleted.\n")

            conn.execute(text(f"ALTER TABLE {TABLE_NAME} ADD UNIQUE (ADM_NO);\n"))
            print(f"✅ Unique constraint added to ADM_NO in the '{TABLE_NAME}' table.\n")

            df.to_sql(name=TABLE_NAME, con=engine, if_exists='append', index=False)
            print(f"✅ Data successfully inserted into the '{TABLE_NAME}' table.")

    except Exception as e:
        print(f"❌ An error occurred: {e}")


# ### **Main Execution Block**

# In[12]:


if __name__ == "__main__":
    # Fetch data
    fees_df = fetch_data()
    print("✅ Data fetched successfully.\n")
    print(fees_df.to_string())

    # Clean data
    fees_df = clean_data(fees_df)
    print("✅ Data cleaned and transformed successfully.\n")
    print("✅ Columns are:\n", fees_df.columns)


    # Update database
    update_database(fees_df)


# In[13]:


fees_df


# <h2 align="center"><b>DAY WISE REPORTS 2024-25</b></h2>

# ### **Import Required Libraries**

# In[14]:


import requests
from bs4 import BeautifulSoup
import pandas as pd
import urllib.parse
from sqlalchemy import create_engine, text


# ### **Define Login Credentials and MySQL Credentials**

# In[15]:


# 🔹 Login Credentials
login_url = "https://app.myskoolcom.tech/kotak_vizag/login"
data_url = "https://app.myskoolcom.tech/kotak_vizag/office_fee/fee_reports_day_wise_receipt_wise_print"

credentials = {
    "uname": "harikiran",
    "psw": "812551"
}

MYSQL_CREDENTIALS = {
    "username": "root",
    "password": "Hari@123",
    "host": "localhost",
    "port": "3306",
    "database": "schooldb",
}

TABLE_NAME = "daywise_fees_collection_2024_25"


# ### **Define Functions for Each Step**

# In[16]:


def login_to_website():
    session = requests.Session()
    login_response = session.post(login_url, data=credentials)
    if "Invalid" in login_response.text:
        print("❌ Login failed! Check credentials.\n")
        return None
    else:
        print("✅ Login successful!\n")
        return session


# ### **Function to Fetch Fee Report Page**

# In[17]:


def fetch_fee_report_page(session):
    response = session.get(data_url)
    soup = BeautifulSoup(response.text, "html.parser")
    table = soup.find("table")
    return table


# ### **Function to Extract Data from Table**

# In[18]:


def extract_data_from_table(table):
    rows = []
    for tr in table.find_all("tr"):
        cols = [td.text.strip() for td in tr.find_all("td")]
        if cols:
            rows.append(cols)
    
    header_row = [
        "SNo", "RecieptNo", "Class", "AdmissionNo", "StudentName", 
        "Date", "-", "Abacus / Vediic Maths", "TERM FEE", 
        "ReceivedAmount", "Remarks"
    ]
    
    df = pd.DataFrame(rows, columns=header_row)
    return df


# ### **Function to Clean Data**

# In[19]:


def clean_data(df):
    # Convert 'Date' column to proper datetime format
    df['Date'] = pd.to_datetime(df['Date'], format='%d-%m-%Y', errors='coerce')

    # Ensure 'AdmissionNo' is treated as a string (no conversion to numeric)
    df['AdmissionNo'] = df['AdmissionNo'].astype(str)

    # Find the index where "TERM" first appears in the "SNo" column
    term_index = df[df["SNo"].str.contains("TERM", na=False)].index

    if not term_index.empty:
        # Drop all rows from the first occurrence of "TERM" onward
        df = df.iloc[:term_index[0]]

        # Drop unnecessary columns
        df = df.drop(columns=["-", "Abacus / Vediic Maths", "TERM FEE"])


    return df


# ### **Function to Update Database**

# In[20]:


def update_database(df):
    password = urllib.parse.quote(MYSQL_CREDENTIALS["password"])
    engine = create_engine(f"mysql+pymysql://{MYSQL_CREDENTIALS['username']}:{password}"
                           f"@{MYSQL_CREDENTIALS['host']}:{MYSQL_CREDENTIALS['port']}/{MYSQL_CREDENTIALS['database']}")

    try:
        with engine.connect() as conn:
            # # 🔹 Alter table to add Remarks column
            # conn.execute(text(f"ALTER TABLE {TABLE_NAME} ADD COLUMN Remarks VARCHAR(255);"))
            # print(f"Step3: Column 'Remarks' added to the '{TABLE_NAME}' table.\n")
            
            # # 🔹 Alter column type for AdmissionNo to VARCHAR
            # conn.execute(text(f"ALTER TABLE {TABLE_NAME} MODIFY COLUMN `AdmissionNo` VARCHAR(20);"))
            # print(f"Step3: Column 'AdmissionNo' type modified to VARCHAR(20).\n")

            # 🔹 Truncate the table before inserting new data
            conn.execute(text(f"TRUNCATE TABLE {TABLE_NAME};"))
            print(f"✅ All records from the '{TABLE_NAME}' table have been deleted.\n")

            # 🔹 Insert the data into the table
            df.to_sql(name=TABLE_NAME, con=engine, if_exists='append', index=False)
            print(f"✅ Data successfully inserted into the '{TABLE_NAME}' table.\n")

    except Exception as e:
        print(f"An error occurred: {e}")


# ### **Main Execution Flow**

# In[21]:


def main():
    # Log in to the website
    session = login_to_website()
    if session is None:
        return

    # Fetch the fee report page
    table = fetch_fee_report_page(session)

    if table:
        print("✅ Table found! Extracting data...\n")

        # Extract data from the table
        df = extract_data_from_table(table)

        # Clean the data
        df = clean_data(df)

        # Save to CSV (optional)
        df.to_csv(r"D:\GITHUB\kotak-school-dbms\output_data\daywise_fee_collection_report_2024_25.csv", index=False)
        print("✅ Data saved to fee_collection_report.csv\n")

        # Insert data into MySQL database
        update_database(df)
        print("✅ Columns are:\n", df.columns)

        # Print sample data
        print(f"✅ {len(df)} Records Entered into database")

    else:
        print("❌ Table not found! The page structure might have changed.")


# ### **Run the Main Function**

# In[22]:


# Run the main function
main()


# <h2 align="center"><b>ATTENDANCE REPORT 2024-25</b></h2>

# ### **📌 Step 1: Import Libraries**

# In[23]:


import pandas as pd
import urllib.parse
from sqlalchemy import create_engine, text
import logging

# Configure logging
logging.basicConfig(filename=r"D:\GITHUB\kotak-school-dbms\output_data\attendance_report_2024_25.log", level=logging.ERROR, 
                    format="%(asctime)s - %(levelname)s - %(message)s")


# ### **📌 Step 2: Define MySQL Credentials & Table Name**

# In[24]:


# MySQL Credentials
MYSQL_CREDENTIALS = {
    "username": "root",
    "password": "Hari@123",
    "host": "localhost",
    "port": "3306",
    "database": "schooldb",
}
TABLE_NAME = "attendance_report_2024_25"


# ### **📌 Step 3: Load and Clean Data**

# In[25]:


### **📌 Step 3: Load and Clean Data (Updated)**
def load_and_clean_data(file1, file2, file3):


    # Load Data
    df1 = pd.read_csv(file1)
    df2 = pd.read_csv(file2)
    df3 = pd.read_csv(file3)

    # Standardize column names
    for df in [df1, df2, df3]:
        df.columns = df.columns.str.strip().str.replace('"', '', regex=False)

    # Merge DataFrames on 'Students Number' using outer join
    df = df1.merge(df2, on='Students Number', how='outer').merge(df3, on='Students Number', how='outer')

    # Identify and handle duplicate columns
    common_fields = ['Name', 'Class']
    for field in common_fields:
        df[field] = df.pop(f"{field}_x").combine_first(df.pop(f"{field}_y"))

    # Drop remaining duplicate columns
    drop_columns = [col for col in df.columns if '_x' in col or '_y' in col]
    df = df.drop(columns=drop_columns, errors='ignore')

    # Rename 'Students Number' to 'AdmissionNo'
    df = df.rename(columns={"Students Number": "AdmissionNo"})

    # Reorder Columns
    column_order = ['AdmissionNo', 'Name', 'Class'] + [col for col in df.columns if col not in ['AdmissionNo', 'Name', 'Class']]
    df = df[column_order]

    # Drop Unnecessary Columns
    columns_to_drop = ["Present Days", "Absent Days", "Toral Working Days"]  # Ensure correct column names
    df = df.drop(columns=[col for col in columns_to_drop if col in df.columns], errors='ignore')


    return df




# ### **📌 Step 4: Process Attendance Data**

# In[26]:


import pandas as pd
import numpy as np

def process_attendance_data(df):

    # Step 1: Clean 'AdmissionNo'
    df = df[~(df["AdmissionNo"].astype(str) == "786") & ~df["AdmissionNo"].astype(str).str.match(r"^[a-zA-Z]")].copy()

    # Step 2: Extract Class and Section
    df["Class"] = df["Class"].astype(str).str.replace(r"ICSE \((.*?)\)", r"\1", regex=True)
    
    student_df = pd.read_csv(r"D:\GITHUB\kotak-school-dbms\output_data\fees_report_2024_25.csv")
    
    print("✅ Students Before Merging\n", len(df["AdmissionNo"].unique()))
    
    # Step 3: Keep only rows where AdmissionNo is in student_df
    df = df[df["AdmissionNo"].isin(student_df["ADM_NO"])]
    
    print("✅ Students After Merging\n", len(df["AdmissionNo"].unique()))
    
    # Step 3: Unpivot DataFrame
    df_unpivot = pd.melt(df, id_vars=["AdmissionNo", "Name", "Class"], 
                        var_name="Date", value_name="AttendanceStatus")

    # Step 4: Convert 'Date' to datetime
    df_unpivot["Date"] = pd.to_datetime(df_unpivot["Date"], format='%d.%m.%Y', errors='coerce')

    # Step 5: Log invalid 'Date' values
    if df_unpivot["Date"].isna().sum() > 0:
        print("⚠️ Warning: Some Date values were invalid and converted to NaT.")

    df_unpivot = df_unpivot[~df_unpivot["AttendanceStatus"].eq("H")].reset_index(drop=True)

    # Step 6: Sorting
    df_unpivot = df_unpivot.sort_values("Date", ascending=False).reset_index(drop=True)

    # Step 7: Identify students with P, A, or H
    students_with_attendance = df_unpivot[df_unpivot['AttendanceStatus'].isin(["P", "A", "H"])]['AdmissionNo'].unique()

    # Step 8: Assign 'TC' if student has previous attendance records
    df_unpivot['AttendanceStatus'] = df_unpivot.apply(
        lambda row: "TC" if pd.isna(row['AttendanceStatus']) and row['AdmissionNo'] in students_with_attendance else row['AttendanceStatus'],
        axis=1
    )
    
    # Step 9: Prioritize Attendance Status
    priority_map = {'P': 2, 'A': 1, 'H': 3, 'Not Joined': 4, 'TC': 5}
    df_unpivot['Priority'] = df_unpivot["AttendanceStatus"].map(priority_map)

    df_unpivot = df_unpivot.sort_values(by=['AdmissionNo', 'Date', 'Priority']) \
                            .drop_duplicates(subset=['AdmissionNo', 'Date'], keep='first') \
                            .drop(columns=['Priority'])
                                
    # Step 10: Final sorting
    df_unpivot = df_unpivot[['Date', 'AdmissionNo', 'Name', 'Class', 'AttendanceStatus']]
    df_unpivot.sort_values(by=['Date'], ascending=False, inplace=True)
    
    df_unpivot['Class'] = df_unpivot['Class'].str.replace("Pre KG - ", "Pre KG")

    # Step 11: Replace Attendance Status with meaningful labels
    df_unpivot["AttendanceStatus"] = df_unpivot["AttendanceStatus"].replace({
        'P': "Present", 'A': "Absent", 'H': "Holiday", 'Not Joined': "Not Joined", 'TC': "TC"
    })

    # Step 12: Extract unique holidays
    df_unpivot = pd.concat([
        df_unpivot[df_unpivot["AttendanceStatus"].isin(["Present", "Absent", "TC", "Not Joined"])],
        df_unpivot[df_unpivot["AttendanceStatus"] == "Holiday"].drop_duplicates(subset=["Date"])
    ]).reset_index(drop=True)

    # Step 13: Class & Section Mapping
    class_section_mapping = {
    "Pre KG": 1, "LKG - A": 2, "LKG - B": 3, "UKG - A": 4, "UKG - B": 5, "UKG - C": 6,
    "I - A": 7, "I - B": 8, "I - C": 9, "I - D": 10, "II - A": 11, "II - B": 12, "II - C": 13, "II - D": 14,
    "III - A": 15, "III - B": 16, "III - C": 17, "III - D": 18, "IV - A": 19, "IV - B": 20, "IV - C": 21, "IV - D": 22,
    "V - A": 23, "V - B": 24, "V - C": 25, "V - D": 26, "VI - A": 27, "VI - B": 28, "VI - C": 29, "VI - D": 30,
    "VII - A": 31, "VII - B": 32, "VII - C": 33, "VII - D": 34, "VIII - A": 35, "VIII - B": 36, "VIII - C": 37,
    "IX - A": 38, "IX - B": 39, "IX - C": 40, "X - A": 41, "X - B": 42, "X - C": 43}

    df_unpivot['ClassNo'] = df_unpivot['Class'].map(class_section_mapping)

    # Step 14: Grade Mapping
    grade_mapping = [
        ("Pre KG", 1), ("LKG", 2), ("UKG", 3),
        ("I", 4), ("II", 5), ("III", 6), ("IV", 7), ("V", 8),
        ("VI", 9), ("VII", 10), ("VIII", 11), ("IX", 12), ("X", 13)
    ]

    conditions = [df_unpivot['Class'].str.contains(fr"\b{k}\b", na=False, regex=True) for k, _ in grade_mapping]
    choices = [v for _, v in grade_mapping]
    df_unpivot['gradeId'] = np.select(conditions, choices, default=0)

    # Step 15: AttendanceStatus Mapping
    AttendanceStatus_mapping = [("Absent", 1), ("Present", 2), ("TC", 3), ("Holiday", 4)]
    conditions = [df_unpivot['AttendanceStatus'].str.contains(k, na=False) for k, _ in AttendanceStatus_mapping]
    choices = [v for _, v in AttendanceStatus_mapping]
    df_unpivot['AttendanceStatusId'] = np.select(conditions, choices, default=0)

    # Step 16: Branch Mapping
    branch_mapping = [
        ('Pre KG', 1), ('LKG', 1), ('UKG', 1),
        ('I', 2), ('II', 2), ('III', 2), ('IV', 2), ('V', 2),
        ('VI', 3), ('VII', 3), ('VIII', 3), ('IX', 3), ('X', 3)
    ]

    conditions = [df_unpivot['Class'].str.contains(fr"\b{k}\b", na=False, regex=True) for k, _ in branch_mapping]
    choices = [v for _, v in branch_mapping]
    df_unpivot['branchId'] = np.select(conditions, choices, default=0)

    # Step 17: Branch Name Mapping
    branch_name_mapping = {1: 'Kindergarten', 2: 'Primary', 3: 'Higher'}
    df_unpivot['branchName'] = df_unpivot['branchId'].map(branch_name_mapping)
    

    grade_mapping_reversed = {
    1: "Pre KG", 2: "LKG", 3: "UKG",
    4: "I", 5: "II", 6: "III", 7: "IV", 8: "V",
    9: "VI", 10: "VII", 11: "VIII", 12: "IX", 13: "X"
}
    

    df_unpivot['className'] = df_unpivot['gradeId'].map(grade_mapping_reversed)

    # Step 19: Final DataFrame Cleanup
    df_ids = df_unpivot[["ClassNo", "Class", "gradeId", "className", "branchId", "branchName",]].drop_duplicates(subset=["ClassNo"])
    df_ids = df_ids.sort_values(by=['ClassNo']).reset_index(drop=True)
    df_ids.to_csv(r"D:\GITHUB\kotak-school-dbms\output_data\class_table_2024_25.csv", index=False)
    
    AttendanceStatus_table = df_unpivot[['AttendanceStatusId','AttendanceStatus']].drop_duplicates(subset=["AttendanceStatusId"])
    
    AttendanceStatus_table.to_csv(r"D:\GITHUB\kotak-school-dbms\output_data\AttendanceStatus_table_2024_25.csv", index=False)
    
    df_unpivot.to_csv(r"D:\GITHUB\kotak-school-dbms\output_data\attendance_report_2024_25.csv", index=False)    

    df_unpivot = df_unpivot[['Date', 'AdmissionNo', 'ClassNo', 'gradeId', 'branchId', 'AttendanceStatusId']]
    
    return df_unpivot


# ### **📌 Step 5: Insert Data into MySQL**

# In[27]:


def update_database(df):
    """Insert attendance data into MySQL database."""
    password = urllib.parse.quote(MYSQL_CREDENTIALS["password"])
    engine = create_engine(f"mysql+pymysql://{MYSQL_CREDENTIALS['username']}:{password}"
                           f"@{MYSQL_CREDENTIALS['host']}:{MYSQL_CREDENTIALS['port']}/{MYSQL_CREDENTIALS['database']}")
    
    try:
        print(f"Connecting to database {MYSQL_CREDENTIALS['database']} at {MYSQL_CREDENTIALS['host']}...\n")
        
        with engine.begin() as conn:
            print(f"Truncating existing table: {TABLE_NAME}")
            conn.execute(text(f"TRUNCATE TABLE {TABLE_NAME};"))
            print(f"Inserting data into {TABLE_NAME} table...\n")
            
            # Try inserting the data in chunks (optional to prevent overload)
            df.to_sql(name=TABLE_NAME, con=engine, if_exists='append', index=False, chunksize=1000)  # Chunks of 1000 rows
            print(f"✅ Data successfully inserted into '{TABLE_NAME}' table.\n")
    
    except Exception as e:
        print(f"❌ An error occurred. Check the logs for details. Error: {e}")
        logging.error(f"❌ Database update failed: {e}")
        logging.error(f"❌ Failed Data Sample (first 5 rows): \n{df.head()}")
        logging.error(f"Total Rows in DataFrame: {df.shape[0]}")
        
        # Capture more details to help debug
        logging.error("MySQL Connection Information:")
        logging.error(f"Host: {MYSQL_CREDENTIALS['host']}")
        logging.error(f"Database: {MYSQL_CREDENTIALS['database']}")
        logging.error(f"Port: {MYSQL_CREDENTIALS['port']}")
        logging.error("Error Traceback:")
        import traceback
        logging.error(traceback.format_exc())


# ### **📌 Step 6: Run the Full Pipeline**

# In[28]:


def main():
    file1 = r"D:\GITHUB\kotak-school-dbms\source_data\Attendance Reports\AttendanceReportUptoSeptember_2024_25.csv"
    file2 = r"D:\GITHUB\kotak-school-dbms\source_data\Attendance Reports\AttendanceOctoberToDecember_2024_25.csv"
    file3 = r"D:\GITHUB\kotak-school-dbms\source_data\Attendance Reports\AttendanceUptoFebruary_2024_25.csv"
    output_file = r"D:\GITHUB\kotak-school-dbms\output_data\AttendanceReport_2024_25.csv"
    
    try:
        print("Loading and cleaning data...\n")
        df = load_and_clean_data(file1, file2, file3)
        print(f"✅ Data loaded with {df.shape[0]} rows.\n")
        
        print("Processing attendance data...\n")
        df_unpivot = process_attendance_data(df)
        df_unpivot.to_csv(output_file, index=False)
        print(f"✅ Processed data with {df_unpivot.shape[0]} rows.\n")
        print("✅ Columns are:\n", df_unpivot.columns)
        # print(df_unpivot[df_unpivot["Date"] == "2025-02-03"].to_string())
                
        print("Updating database...\n")
        update_database(df_unpivot)
        print("✅ Data updated successfully!\n")

        print("✅ Attendance report processing completed successfully!\n")
        print(f"✅ No of Rows: {df_unpivot.shape[0]}\n")
        
    except Exception as e:
        print(f"❌ An unexpected error occurred. Error: {e}\n")
        logging.error(f"❌ Unexpected error: {e}\n")


# Run the script
main()


# <h2 align="center"><b>Class Table 2024-25</b></h2>

# In[29]:


import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from sqlalchemy import create_engine, text
import urllib.parse
import traceback
import logging
from sqlalchemy import create_engine, text


MYSQL_CREDENTIALS = {
    "username": "root",
    "password": "Hari@123",
    "host": "localhost",
    "port": "3306",
    "database": "schooldb",
}
TABLE_NAME = "class_table_2024_25"


# In[30]:


df = pd.read_csv(r"D:\GITHUB\kotak-school-dbms\output_data\class_table_2024_25.csv")
df.head()


# In[31]:


df.columns


# In[32]:


# Define Table Schema (Modify based on actual data types)
TABLE_SCHEMA = f"""
CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
    ClassNo INT PRIMARY KEY,
    Class VARCHAR(50),
    gradeId INT,
    className VARCHAR(50),
    branchId INT,
    branchName VARCHAR(50)
);"""


# In[33]:


def update_database(df):
    """Insert attendance data into MySQL database."""
    password = urllib.parse.quote(MYSQL_CREDENTIALS["password"])
    engine = create_engine(f"mysql+pymysql://{MYSQL_CREDENTIALS['username']}:{password}"
                           f"@{MYSQL_CREDENTIALS['host']}:{MYSQL_CREDENTIALS['port']}/{MYSQL_CREDENTIALS['database']}")
    
    try:
        print(f"Connecting to database {MYSQL_CREDENTIALS['database']} at {MYSQL_CREDENTIALS['host']}...")
        logging.info(f"Connecting to database {MYSQL_CREDENTIALS['database']} at {MYSQL_CREDENTIALS['host']}...")

        with engine.begin() as conn:
            # **Create Table if it does not exist**
            print(f"Checking if table '{TABLE_NAME}' exists...")
            conn.execute(text(TABLE_SCHEMA))
            print(f"✅ Table '{TABLE_NAME}' is ready.")

            # **Truncate the table before inserting data**
            print(f"Truncating existing table: {TABLE_NAME}")
            conn.execute(text(f"TRUNCATE TABLE {TABLE_NAME};"))

            # **Insert Data**
            print(f"Inserting data into {TABLE_NAME} table...")
            df.to_sql(name=TABLE_NAME, con=engine, if_exists='append', index=False, chunksize=1000, method='multi')

            print(f"✅ Data successfully inserted into '{TABLE_NAME}' table.")
            logging.info(f"✅ Data successfully inserted into '{TABLE_NAME}' table.")

    except Exception as e:
        error_message = f"❌ An error occurred: {e}"
        print(error_message)
        logging.error(error_message)
        logging.error("Error Traceback:\n" + traceback.format_exc())


# In[34]:


update_database(df)


# <h2 align="center"><b>FEE COLLECTION REPORT 2024-25</b></h2>

# ### **Import Required Libraries**

# In[35]:


import requests
from bs4 import BeautifulSoup
import pandas as pd
import urllib.parse
from sqlalchemy import create_engine, text

### **Define Login Credentials and MySQL Credentials**
# 🔹 Login Credentials
login_url = "https://app.myskoolcom.tech/kotak_vizag/login"
data_url = "https://app.myskoolcom.tech/kotak_vizag/office_fee/fee_consolidate_report_print?&from=2024-04-01&to=&is_transport_fee=&college_id=&course_id=&branch_id=&semister_id=&section_id=&academic_years_id=&payment_type_id=&fee_status=&status=1&imageField=Search"

credentials = {
    "uname": "harikiran",
    "psw": "812551"
}

MYSQL_CREDENTIALS = {
    "username": "root",
    "password": "Hari@123",
    "host": "localhost",
    "port": "3306",
    "database": "schooldb",
}

TABLE_NAME = "fees_collection_2024_25"


# In[36]:


### **Function to Log in to Website**
def login_to_website():
    session = requests.Session()
    login_response = session.post(login_url, data=credentials)
    if "Invalid" in login_response.text:
        print("❌ Login failed! Check credentials.\n")
        return None
    else:
        print("✅ Login successful!\n")
        return session


# In[37]:


### **Function to Fetch All Fee Tables**
def fetch_all_fee_tables(session):
    response = session.get(data_url)
    soup = BeautifulSoup(response.text, "html.parser")

    # Find all fee tables
    fee_tables = soup.find_all("table", class_="b-t")

    all_data = []  # List to store all rows

    # Loop through each table and extract data
    for table in fee_tables:
        df = table_to_dataframe(table)
        if df is not None:
            all_data.append(df)

    # Merge all class data into a single DataFrame
    combined_df = pd.concat(all_data, ignore_index=True)
    return combined_df


# In[38]:


### **Function to Convert HTML Table to DataFrame**
def table_to_dataframe(table):
    if not table:
        print("❌ No table to convert!")
        return None

    # Extract column headers
    headers = [th.get_text(strip=True) for th in table.find_all("th")]

    # Extract table rows
    rows = []
    for tr in table.find_all("tr")[1:]:  # Skip header row
        cells = [td.get_text(strip=True) for td in tr.find_all("td")]
        if cells:
            rows.append(cells)

    # Convert to Pandas DataFrame
    df = pd.DataFrame(rows, columns=headers)
    return df


# In[39]:


import numpy as np

### **Function to Clean Data**
def clean_data(df):
    
    # Drop rows where the first column starts with "Total"
    df = df[~df.iloc[:, 0].astype(str).str.startswith("Total", na=False)].copy()    
    
    # Ensure 'Admission No' is treated as a string (no conversion to numeric)
    df.loc[:,'Admin No.'] = df['Admin No.'].astype(str)
    
    df.columns = ['SNo', 'AdmissionNo', 'Name', 'Abacus / Vediic Maths', 'TERM FEE',
       'Total_Fees', 'Abacus / Vediic Maths', 'TERM FEE',
       'Total_Fee_Paid', 'Discount_Concession', 'Total_Due']
    
    # Convert relevant columns to numeric (removing commas)
    numeric_columns = ["Total_Fees", "Total_Fee_Paid", "Discount_Concession", "Total_Due"]
    
    for col in numeric_columns:
        df[col] = df[col].astype(str)  # Convert everything to string
        df[col] = df[col].str.replace(",", "")  # Remove commas
        df[col] = df[col].replace(["", "None", "nan", "NaN", np.nan], np.nan)  # Replace invalid values with NaN
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)  # Convert to float, replace NaN with 0
        df[col] = df[col].astype(int)  # Convert to integer
        
    df["SNo"] = range(1, len(df) + 1)       
        
    
    df = df.drop(columns=['Abacus / Vediic Maths', 'TERM FEE', 'Abacus / Vediic Maths', 'TERM FEE'])
    

    return df


# In[40]:


### **Function to Update MySQL Database**
def update_database(df):
    password = urllib.parse.quote(MYSQL_CREDENTIALS["password"])
    engine = create_engine(f"mysql+pymysql://{MYSQL_CREDENTIALS['username']}:{password}"
                           f"@{MYSQL_CREDENTIALS['host']}:{MYSQL_CREDENTIALS['port']}/{MYSQL_CREDENTIALS['database']}")

    try:
        with engine.connect() as conn:
            # 🔹 Truncate the table before inserting new data
            conn.execute(text(f"TRUNCATE TABLE {TABLE_NAME};"))
            print(f"✅ All records from the '{TABLE_NAME}' table have been deleted.\n")

            # 🔹 Insert the data into the table
            df.to_sql(name=TABLE_NAME, con=engine, if_exists='append', index=False)
            print(f"✅ Data successfully inserted into the '{TABLE_NAME}' table.\n")

    except Exception as e:
        print(f"❌ Error occurred while updating database: {e}")


# In[41]:


### **Main Execution Flow**
def main():
    # Log in to the website
    session = login_to_website()
    if session is None:
        return

    # Fetch all fee tables
    df = fetch_all_fee_tables(session)

    if not df.empty:
        print("✅ Data extracted successfully! Cleaning data...\n")

        # Clean the data
        df = clean_data(df)
        print("✅ Columns are:'\n",df.columns)

        # Save to CSV (optional)
        df.to_csv(r"D:\GITHUB\kotak-school-dbms\output_data\fee_collection_report_2024_25.csv", index=False)
        print("✅ Data saved to 'daywise_fee_collection_report.csv'\n")

        # Insert data into MySQL database
        update_database(df)
        print(f"✅ {len(df)} records entered into the database")

        # Print sample data
        print(df.to_string(index=False))

    else:
        print("❌ No data found! The page structure might have changed.")


# In[42]:


### **Run the Main Function**
if __name__ == "__main__":
    main()

