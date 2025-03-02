SELECT conname, conrelid::regclass, pg_get_constraintdef(oid) 
FROM pg_constraint 
WHERE conrelid = 'students_2024_25'::regclass;

SELECT column_name FROM information_schema.columns 
WHERE table_name = 'students_2024_25';

SELECT column_name, character_maximum_length 
FROM information_schema.columns 
WHERE table_name = 'students_2024_25';

ALTER TABLE students_2024_25 ALTER COLUMN mobile TYPE VARCHAR(25);

CREATE TABLE fees_table_2024_25 (
    SNo SERIAL PRIMARY KEY,
    STUDENT_NAME VARCHAR(100),
    ADM_NO VARCHAR(20) UNIQUE NOT NULL,
    FB_NO VARCHAR(20),
    CLASS VARCHAR(20),
    Term1 NUMERIC(10,2) DEFAULT 0,
    Term2 NUMERIC(10,2) DEFAULT 0,
    Term3 NUMERIC(10,2) DEFAULT 0,
    Term4 NUMERIC(10,2) DEFAULT 0,
    TotalFeePaid NUMERIC(10,2) DEFAULT 0,
    Discount_Concession NUMERIC(10,2) DEFAULT 0,
    TotalFeeDue NUMERIC(10,2) DEFAULT 0,
    Fine NUMERIC(10,2) DEFAULT 0,
    ClassNo INT,
    TotalFees NUMERIC(10,2) GENERATED ALWAYS AS 
        (TotalFeePaid + Discount_Concession + TotalFeeDue) STORED,
    PaymentStatusId INT
);


SELECT * FROM students_2024_25;

SELECT COUNT(*) FROM students_2024_25;

SELECT * FROM fees_table_2024_25;

SELECT COUNT(*) FROM fees_table_2024_25;


SELECT column_name FROM information_schema.columns WHERE table_name = 'fees_table_2024_25';





