import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

KOTAK_LOGIN_URL = os.getenv("KOTAK_LOGIN_URL")
KOTAK_USERNAME = os.getenv("KOTAK_USERNAME")
KOTAK_PASSWORD = os.getenv("KOTAK_PASSWORD")

DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "./downloads")

REPORT_URLS = {
    "daywise_collection": os.getenv("DAYWISE_URL"),
    "student_list": os.getenv("STUDENT_LIST_URL")
}