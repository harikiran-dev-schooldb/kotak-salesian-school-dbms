from logger import logger

def validate_dataframe(df):

    if df.empty:
        raise ValueError("Dataframe is empty")

    if "amount" in df.columns:
        invalid = df["amount"].isna().sum()

        if invalid > 0:
            logger.warning(f"{invalid} rows contain invalid amounts")

    logger.info("Validation passed")

    return True