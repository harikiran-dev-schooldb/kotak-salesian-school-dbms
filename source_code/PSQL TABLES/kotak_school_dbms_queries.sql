SELECT 'SELECT * FROM ' || tablename || ' LIMIT 10;' 
FROM pg_tables 
WHERE schemaname = 'public';

SELECT * FROM students WHERE academic_year_id = 1;
SELECT * FROM student_list;

SELECT * FROM students;
DROP TABLE students;

SELECT * FROM fees_table;
DROP TABLE fees_table;

SELECT * FROM fees_table WHERE academic_year_id = 2;
DROP TABLE daywise_fees_collection;

SELECT * FROM daywise_fees_collection WHERE academic_year = '2024-25';

SELECT * FROM class_table_2024_25 ;

SELECT * FROM attendance_report;
SELECT * FROM class_table;
SELECT * FROM attendance_report WHERE academic_year_id = 2;
DROP TABLE attendance_report;

DELETE FROM attendance_report;

SELECT * FROM fees_collection WHERE academic_year_id = 2;
DROP TABLE fees_collection;

SELECT * FROM fee_concession_report ;
DROP TABLE fee_concession_report;

SELECT * FROM fees_report_2024_25 ;

SELECT * FROM class_table_2024_25 WHERE classno = 1;

SELECT DISTINCT classno FROM fees_table;

WHERE classno NOT IN (SELECT classno FROM class_table_2024_25);

SELECT conname, conrelid::regclass, confrelid::regclass
FROM pg_constraint 
WHERE conname = 'fees_table_2024_25_classno_fkey';

SELECT * FROM class_table_2024_25;

SELECT branchid, COUNT(*) FROM class_table_2024_25 GROUP BY branchid HAVING COUNT(*) > 1;

SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'fee_concession_2024_25';


SELECT indexname, indexdef 
FROM pg_indexes 
WHERE tablename = 'fee_concession_2024_25';





