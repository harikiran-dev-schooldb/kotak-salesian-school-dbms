USE schooldb;

CREATE TABLE fees_table (
	SNo INT,
    ADM_NO VARCHAR(10) PRIMARY KEY,
    STUDENT_NAME VARCHAR(100) NOT NULL,
    FB_NO VARCHAR(10),
    CLASS VARCHAR(10),
    TotalFees INT NOT NULL,
    Term1 INT DEFAULT 0,
    Term2 INT DEFAULT 0,
    Term3 INT DEFAULT 0,
    Term4 INT DEFAULT 0,
    TotalFeePaid INT DEFAULT 0,
    Discount_Concession INT DEFAULT 0,
    TotalFeeDue INT DEFAULT 0,
    Fine INT DEFAULT 0,
    PaymentStatus VARCHAR(50),
    ClassNo INT
);



CREATE TABLE attendance_report (
    Date DATE NOT NULL,
    AdmissionNo VARCHAR(20),
    ClassNo INT,
    gradeId INT,
    branchId INT,
    AttendanceStatusId VARCHAR(20)
);

ALTER TABLE attendance_report DROP INDEX `AdmissionNo`;
ALTER TABLE attendance_report ADD UNIQUE (`Date`, `AdmissionNo`);

CREATE TABLE attendance_report1 (
    Date DATE NOT NULL,
    AdmissionNo VARCHAR(20),
    Name VARCHAR(100) NOT NULL,
    Class VARCHAR(20),
    ClassNo INT,
    gradeId INT,
    branchId INT,
    AttendanceStatusId VARCHAR(20)
);

ALTER TABLE attendance_report1 DROP INDEX `AdmissionNo`;
ALTER TABLE attendance_report1 ADD UNIQUE (`Date`, `AdmissionNo`);


CREATE TABLE students (
	SNo INT,
    AdmissionNo VARCHAR(10) PRIMARY KEY,
    STUDENT_NAME VARCHAR(255),
    Class VARCHAR(50),
    Gender VARCHAR(10),
    MotherName VARCHAR(255),
    FatherName VARCHAR(255),
    PenNo VARCHAR(50),
    DOB DATE,
    Mobile VARCHAR(50),
    Religion VARCHAR(20),
    Caste VARCHAR(10),
    SubCaste VARCHAR(20),
    `IIndLang` VARCHAR(20),
    Remarks TEXT,
    ClassNo INT,
    JoinedYear TEXT
);

CREATE TABLE fees_collection (
    SNo INT ,
    AdmissionNo VARCHAR(20) NOT NULL,
    Name VARCHAR(100) NOT NULL,
    Total_Fees INT NOT NULL,
    Total_Fee_Paid INT NOT NULL,
    Discount_Concession INT NOT NULL,
    Total_Due INT NOT NULL
);


-- DESCRIBING TABLES

DESCRIBE fees_table;

DESCRIBE attendance_report;

DESCRIBE students;

DESCRIBE class_table;

-- DROPPING TABLES

DROP TABLE fees_table;

DROP TABLE attendance_report;

DROP TABLE students;

DROP TABLE class_table;

-- FEES TABLE

SELECT * FROM students;

SELECT * FROM class_table;

SELECT COUNT(*) FROM students;

SELECT * FROM fees_table ORDER BY SNo;

SELECT ClassNo,Class,COUNT(*) AS Strength FROM fees_table GROUP BY ClassNo,CLASS ORDER BY ClassNo DESC ;

SELECT * FROM fees_table WHERE PaymentStatus="Not Paid";

-- DAY WISE REPORTS

SELECT * FROM daywise_fees_collection WHERE AdmissionNo="14940";

SELECT count(*) FROM daywise_fees_collection;

SELECT * FROM attendance_report WHERE AttendanceStatus = "Present" ;

SELECT * FROM attendance_report WHERE Date = curdate() - 1 AND AttendanceStatus = "Absent" ORDER BY ClassNo;

SELECT * FROM attendance_report ;

SELECT Date, count(*) AS Students FROM attendance_report GROUP BY Date ORDER BY Students ASC;

SELECT COUNT(DISTINCT Date) AS UniqueDates FROM attendance_report;


SELECT COUNT(*) FROM attendance_report;

-- Student Info



SELECT * FROM students ORDER BY SNo, ClassNo ASC;

SELECT COUNT(*) FROM students;

SHOW CREATE TABLE attendance_report;

