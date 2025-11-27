-- ==============================
-- Kotak Salesian School Database Schema
-- ==============================

-- 1️⃣ STUDENTS TABLE
CREATE TABLE IF NOT EXISTS students (
    id SERIAL PRIMARY KEY,
    adm_no VARCHAR,
    class_nos VARCHAR,
    grade_id VARCHAR,
    academic_year_id INT,
    status_id INT,
    branch_id INT
);

-- 2️⃣ STUDENT_LIST TABLE
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

-- 3️⃣ FEES_TABLE
CREATE TABLE IF NOT EXISTS fees_table (
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

-- 4️⃣ DAYWISE_FEES_COLLECTION TABLE
CREATE TABLE IF NOT EXISTS daywise_fees_collection (
    "SNo" TEXT,
    "AdmissionNo" TEXT,
    "Date" DATE,
    "ReceivedAmount" NUMERIC,
    "academic_year_id" INTEGER
);
