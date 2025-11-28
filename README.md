# 📊 Kotak DBMS Dashboard

## 🔎 Overview
The **Kotak DBMS Dashboard** is a centralized data management and analytics solution built for **Kotak Salesian School**.  
It helps administrators and management teams monitor **student attendance, fee collection, concessions, and overall financial performance** using a clean and interactive Power BI dashboard.

This project integrates **database-driven data (MySQL/PostgreSQL)** with **Python-based data processing** and **Power BI visualizations** to deliver actionable insights.

---

## ✅ Key Features

### 💰 Fee & Payment Analytics
- **Students by Payment Status**  
  Visual breakdown of students based on:
  - Paid  
  - Partially Paid  
  - Not Paid  
  - RTE  

- **Amount Collected by Date**  
  Track day-wise fee collections to monitor revenue trends.

- **Total Students & Fees Summary**  
  - Total students  
  - Total fees collected  
  - Pending fees  
  - Total concessions  

- **Payment by Branches**  
  Analyze and compare fee collection across different school branches.

---

### 🧑‍🎓 Attendance & Student Tracking
- **Attendance Reports**  
  - Daily attendance trends  
  - Absentee analysis  
  - Identification of frequently absent students  

- **Students with High Absenteeism**  
  Automatically lists students with **more than 30 absences**, helping proactive intervention.

---

### 📋 Reports & Data Validation
- **Fee Reports**  
  Detailed, student-wise fee payment history.

- **Concessions Report**  
  Transparent view of concessions granted to students.

- **Excel vs App Data Comparison**  
  Ensures data accuracy by validating dashboard data against Excel records.

---

## 🛠️ Technology Stack

- **Power BI Desktop** – Dashboard & visualizations  
- **Python** – Data cleaning, processing, and automation  
- **PostgreSQL / MySQL** – Backend database  
- **Excel** – Source & validation data  

---

## 🚀 Setup Instructions

### 🔹 Prerequisites
- Install **Power BI Desktop**
- Access to **PostgreSQL or MySQL** database
- Python installed (for data preprocessing)

---

### 🔹 Steps to Use

1. **Load the Dashboard**
   - Open **Power BI Desktop**
   - Load the `KOTAK_DBMS_DASHBOARD.pbix` file

2. **Refresh Data**
   - Click **Refresh** to fetch the latest data from the database

3. **Apply Filters**
   - Class  
   - Payment Status  
   - Month  
   - Attendance Status  

4. **Explore Reports**
   - Navigate using report tabs inside Power BI

---

## 🖼️ Dashboard Screenshots

### **1. Students by Payment Status**
![Students by Payment Status](https://github.com/user-attachments/assets/5b1c3d2b-02e0-49ab-8e84-a77cd6fcdf2d)

---

### **2. Amount Collected by Date**
![Amount Collected by Date](https://github.com/user-attachments/assets/140bc118-697e-4d7d-974e-df1018707ea4)

---

### **3. Attendance Report**
![Attendance Report](https://github.com/user-attachments/assets/3130a865-daef-45b1-a677-bc66b06d54b4)

---

### **4. Fee Reports**
![Fee Reports](https://github.com/user-attachments/assets/934f0674-d5eb-4ed3-9f69-1f084878a6dc)

---

### **5. Students Having Absents More Than 30**
![High Absentee Students](https://github.com/user-attachments/assets/0ed2e07d-89ae-4de8-8c94-4b62b1082d9d)

---

## 🚧 Future Enhancements

- 🔔 **Automated Fee Reminders** via email or SMS  
- 👨‍👩‍👧 **Parent Portal** to monitor attendance & fee status  
- 📚 **Exam & Academic Performance Reports**  
- 🔐 **Role-based access** for Admin, Staff, and Parents  
- 📦 **Automated database backups & data validation**

---

## 📞 Contact

For queries, feedback, or improvements:  
**Harikiran**  
📍 Kotak Salesian School  

---

⭐ *If you find this project useful, consider giving the repository a star!*
