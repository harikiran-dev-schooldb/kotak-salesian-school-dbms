# Kotak DBMS Dashboard

## Overview
The **Kotak DBMS Dashboard** is designed for managing student attendance, fee collection, and performance tracking for Kotak Salesian School. This dashboard provides insights into student payments, attendance trends, and financial summaries.

## Features
- **Students by Payment Status**: Visual representation of fee payments (Paid, Partially Paid, Not Paid, RTE).
- **Amount Collected by Date**: Track daily fee collections.
- **Total Students and Fees Summary**: Displays the total number of students, total fees collected, pending fees, and concessions.
- **Payment by Branches**: View fee collections by different school branches.
- **Attendance Reports**: Analyze attendance trends, absentees, and students with high absentee rates.
- **Fee Reports**: Detailed student-wise fee payment history.
- **Concessions Report**: Breakdown of fee concessions given to students.
- **Excel vs. App Data Comparison**: Ensure data accuracy by comparing fee reports with Excel records.

## Setup Instructions
### Prerequisites
- Install **Power BI Desktop** to view the dashboard.
- Ensure access to the **MySQL/PostgreSQL** database for live updates.
- Use **Python for data processing** before importing into Power BI.

### Steps to Use
1. **Load the Dashboard**
   - Open Power BI and import the `KOTAK_DBMS_DASHBOARD.pbix` file.
2. **Refresh Data**
   - Click **Refresh** to update the latest data from the database.
3. **Filter Data**
   - Use dropdown filters for Class, Payment Status, Month, and Attendance Status.
4. **Analyze Reports**
   - Navigate through different report sections using the tabs in Power BI.

## Screenshots
### **1. Students by Payment Status**

![image](https://github.com/user-attachments/assets/5b1c3d2b-02e0-49ab-8e84-a77cd6fcdf2d)

### **2. Amount Collected by Date**

![image](https://github.com/user-attachments/assets/140bc118-697e-4d7d-974e-df1018707ea4)

### **3. Attendance Report**

![image](https://github.com/user-attachments/assets/3130a865-daef-45b1-a677-bc66b06d54b4)

### **4. Fee Reports**

![image](https://github.com/user-attachments/assets/934f0674-d5eb-4ed3-9f69-1f084878a6dc)

### **5. Students Having Absents More Than 30**

![image](https://github.com/user-attachments/assets/0ed2e07d-89ae-4de8-8c94-4b62b1082d9d)


## Future Enhancements
- **Automated Fee Reminders**: Send alerts for pending fees.
- **Parent Portal**: Allow parents to track attendance and fees.
- **Exam Reports**: Add student performance tracking.

For any queries or improvements, contact **Harikiran** at **Kotak Salesian School**.

