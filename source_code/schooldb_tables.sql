BEGIN;

-- ROLLBACK;


-- Drop existing tables if they exist
DROP TABLE IF EXISTS public.attendance_report_2024_25 CASCADE;
DROP TABLE IF EXISTS public.fees_table_2024_25 CASCADE;
DROP TABLE IF EXISTS public.fees_collection_2024_25 CASCADE;
DROP TABLE IF EXISTS public.fee_concession_2024_25 CASCADE;
DROP TABLE IF EXISTS public.fees_report_2024_25 CASCADE;
DROP TABLE IF EXISTS public.daywise_fees_collection_2024_25 CASCADE;
DROP TABLE IF EXISTS public.students_2024_25 CASCADE;
DROP TABLE IF EXISTS public.class_table_2024_25 CASCADE;



-- Recreate Tables

-- Class Table
CREATE TABLE public.class_table_2024_25
(
    classno SERIAL PRIMARY KEY,
    class VARCHAR(50),
    classid INTEGER ,
    classname VARCHAR(50),
    branchid INTEGER ,  -- ✅ Added UNIQUE constraint
    branchname VARCHAR(50)
);



-- Students Table
CREATE TABLE IF NOT EXISTS public.students_2024_25
(
    sno SERIAL,
    admissionno VARCHAR(20) PRIMARY KEY, -- Primary key
    student_name VARCHAR(100) NOT NULL,
    class VARCHAR(20),
    gender VARCHAR(10),
    mothername VARCHAR(100),
    fathername VARCHAR(100),
    penno VARCHAR(50),
    dob DATE,
    mobile VARCHAR(25),
    religion VARCHAR(50),
    caste VARCHAR(50),
    subcaste VARCHAR(50),
    iindlang VARCHAR(50),
    remarks TEXT,
    classno INTEGER,
    joinedyear INTEGER
);

-- Attendance Report
CREATE TABLE IF NOT EXISTS public.attendance_report_2024_25
(
    date DATE NOT NULL,
    admissionno VARCHAR(20) NOT NULL,
    classno INTEGER NOT NULL,
    classid INTEGER NOT NULL,
    branchid INTEGER NOT NULL,
    attendancestatusid INTEGER NOT NULL,
    PRIMARY KEY (date, admissionno), -- Composite Primary Key
    FOREIGN KEY (admissionno) REFERENCES public.students_2024_25(admissionno) ON DELETE CASCADE,
    FOREIGN KEY (classno) REFERENCES public.class_table_2024_25(classno) ON DELETE SET NULL
);

-- Fees Table
CREATE TABLE IF NOT EXISTS public.fees_table_2024_25
(
    sno SERIAL,
    adm_no VARCHAR(20) PRIMARY KEY, -- Primary key
    student_name VARCHAR(100),
    fb_no VARCHAR(20),
    class VARCHAR(20),
    term1 NUMERIC(10, 2) DEFAULT 0,
    term2 NUMERIC(10, 2) DEFAULT 0,
    term3 NUMERIC(10, 2) DEFAULT 0,
    term4 NUMERIC(10, 2) DEFAULT 0,
    totalfeepaid NUMERIC(10, 2) DEFAULT 0,
    discount_concession NUMERIC(10, 2) DEFAULT 0,
    totalfeedue NUMERIC(10, 2) DEFAULT 0,
    fine NUMERIC(10, 2) DEFAULT 0,
    classno INTEGER,
    totalfees NUMERIC(10, 2) GENERATED ALWAYS AS (totalfeepaid + discount_concession + totalfeedue) STORED,
    paymentstatusid INTEGER,
    FOREIGN KEY (adm_no) REFERENCES public.students_2024_25(admissionno) ON DELETE CASCADE,
    FOREIGN KEY (classno) REFERENCES public.class_table_2024_25(classno) ON DELETE SET NULL
);

-- Fees Collection
CREATE TABLE IF NOT EXISTS public.fees_collection_2024_25
(
    admissionno VARCHAR(20) PRIMARY KEY, -- Primary key
    name VARCHAR(100) NOT NULL,
    total_fees NUMERIC(10, 2) NOT NULL DEFAULT 0,
    total_fee_paid NUMERIC(10, 2) NOT NULL DEFAULT 0,
    discount_concession NUMERIC(10, 2) NOT NULL DEFAULT 0,
    total_due NUMERIC(10, 2) NOT NULL DEFAULT 0,
    FOREIGN KEY (admissionno) REFERENCES public.students_2024_25(admissionno) ON DELETE CASCADE
);

-- Fee Concessions
CREATE TABLE IF NOT EXISTS public.fee_concession_2024_25
(	
	id	 SERIAL,
    student_number VARCHAR(20), 
    date DATE NOT NULL,
    student_name VARCHAR(100) NOT NULL,
    discount_given NUMERIC(10, 2) NOT NULL,
    FOREIGN KEY (student_number) REFERENCES public.students_2024_25(admissionno) ON DELETE CASCADE
);


-- ALTER TABLE fee_concession_2024_25 DROP CONSTRAINT fee_concession_2024_25_pkey;

ALTER TABLE fee_concession_2024_25 ADD PRIMARY KEY (student_number, date);


-- Fees Report
CREATE TABLE IF NOT EXISTS public.fees_report_2024_25
(
    admissionno VARCHAR(20) PRIMARY KEY, -- Primary key
    name VARCHAR(100) NOT NULL,
    total_fees NUMERIC(10, 2) NOT NULL DEFAULT 0,
    total_fee_paid NUMERIC(10, 2) NOT NULL DEFAULT 0,
    discount_concession NUMERIC(10, 2) NOT NULL DEFAULT 0,
    total_due NUMERIC(10, 2) NOT NULL DEFAULT 0,
    FOREIGN KEY (admissionno) REFERENCES public.students_2024_25(admissionno) ON DELETE CASCADE
);

-- Daywise Fees Collection
CREATE TABLE IF NOT EXISTS public.daywise_fees_collection_2024_25
(
    "AdmissionNo" TEXT , 
    "SNo" TEXT PRIMARY KEY, -- Primary key
    "RecieptNo" TEXT,
    "Class" TEXT,
    "StudentName" TEXT,
    "Date" TIMESTAMP,
    "ReceivedAmount" DOUBLE PRECISION,
    "Remarks" TEXT
);

-- ALTER TABLE daywise_fees_collection_2024_25 ADD COLUMN id SERIAL PRIMARY KEY;


ALTER TABLE daywise_fees_collection_2024_25 DROP CONSTRAINT daywise_fees_collection_2024_25_pkey;


COMMIT;
