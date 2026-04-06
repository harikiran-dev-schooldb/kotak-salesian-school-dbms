from config import REPORT_URLS
from extract import fetch_html, html_table_to_dataframe
from transform import transform
from validate import validate_dataframe
from load import load_dataframe
from logger import logger


def run_pipeline():

    logger.info("Pipeline started")

    html = fetch_html(REPORT_URLS["daywise_collection"])

    df = html_table_to_dataframe(html)

    df = transform(df)

    validate_dataframe(df)

    load_dataframe(df, "daywise_collection")

    logger.info("Pipeline finished")


if __name__ == "__main__":

    run_pipeline()