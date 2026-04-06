import pandas as pd
from logger import logger


def clean_columns(df):

    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(" ", "_")
    )

    return df


def convert_types(df):

    if "amount" in df.columns:
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce")

    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")

    return df


def remove_empty_rows(df):

    df = df.dropna(how="all")

    return df


def transform(df):

    logger.info("Transforming data")

    df = clean_columns(df)

    df = convert_types(df)

    df = remove_empty_rows(df)

    return df