# Kotak Salesian School DBMS

## Overview
The **School DBMS Project** is a database management system designed to efficiently manage student information, attendance, fee collection, and academic performance at **Kotak Salesian School**. This system ensures data integrity, improves administrative efficiency, and provides insightful analytics for better decision-making.

## Features
- **Student Management**: Store and manage student details, including name, class, section, date of birth, and contact information.
- **Attendance Tracking**: Monitor daily attendance, identify students with frequent absences, and analyze absence trends.
- **Fee Collection & Reports**: Maintain fee payment records, generate due reports, and analyze day-wise fee collections.
- **Academic Performance**: Record student grades and track academic progress.
- **Eligibility Checking System**: Automatically determine a student's class eligibility based on their date of birth.
- **Data Analytics & Reporting**: Generate various reports using Power BI for attendance trends, fee collection, and student insights.

## Technology Stack
- **Database**: MySQL (Partitioned by month for better performance)
- **Backend**: Python (For data cleaning and importing into MySQL)
- **Frontend**: Google Sheets Web App (For ease of access and user interaction)
- **Data Visualization**: Power BI (For advanced reporting and insights)
- **Excel & Google Sheets**: For managing and analyzing data

## Database Structure
The database consists of multiple tables for efficient organization:
1. **Students**: Stores student details
2. **Attendance_Report**: Records attendance history
3. **Fees_Table**: Manages fee payments
4. **Daywise_Fees_Collection**: Tracks daily fee transactions
5. **Classes, Sections, Branches**: Organizes students into appropriate categories

## Power BI Reports & Insights
- **Student Attendance Analysis**
  - Identify students with more than 10 absences
  - Detect long absence streaks excluding holidays
  - Calculate monthly absence trends
  - Track students with high consecutive absence days
- **Fee Collection Dashboard**
  - View daily and monthly collection trends
  - Identify overdue payments
- **Performance Analytics**
  - Compare attendance vs academic performance
  - Identify students at academic risk

## How to Use
1. **Data Entry**: Input student data, attendance, and fee details into MySQL via Google Sheets or Python scripts.
2. **Data Processing**: Run automated scripts to clean and process data.
3. **Visualization**: Connect Power BI to MySQL for real-time insights.
4. **Decision Making**: Use reports for improving attendance, fee collection, and academic performance.

## Future Enhancements
- **Automated Notifications** for fee dues and absentee alerts
- **Mobile App Integration** for easy access to reports
- **AI-based Predictive Analytics** to identify at-risk students

## Contributors
- **Harikiran** - Data Administrator, Kotak Salesian School

## License
This project is for internal use at Kotak Salesian School and is not open-source.

---
For any inquiries or further developments, please contact the school administration.

