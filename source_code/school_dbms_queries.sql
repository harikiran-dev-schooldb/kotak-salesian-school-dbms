SELECT 'SELECT * FROM ' || tablename || ' LIMIT 10;' 
FROM pg_tables 
WHERE schemaname = 'public';

SELECT * FROM students_2024_25;
SELECT * FROM class_table_2024_25 ;
SELECT * FROM fees_table_2024_25 ;
SELECT * FROM daywise_fees_collection_2024_25 ;
SELECT * FROM attendance_report_2024_25 ;
SELECT * FROM fees_collection_2024_25 ;
SELECT * FROM fee_concession_2024_25 ;

SELECT * FROM fees_report_2024_25 ;

SELECT * FROM class_table_2024_25 WHERE classno = 1;

SELECT DISTINCT classno FROM fees_table_2024_25 
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





