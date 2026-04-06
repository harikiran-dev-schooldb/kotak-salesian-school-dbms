import requests
import pandas as pd
from io import StringIO
from bs4 import BeautifulSoup
from logger import logger

def fetch_html(url):

    logger.info(f"Fetching {url}")

    response = requests.get(url)

    if response.status_code != 200:
        raise Exception("Failed to fetch report")

    return response.text


def html_table_to_dataframe(html):

    soup = BeautifulSoup(html, "html.parser")

    table = soup.find("table")

    df = pd.read_html(StringIO(str(table)))[0]

    logger.info(f"Extracted {len(df)} rows")

    return df