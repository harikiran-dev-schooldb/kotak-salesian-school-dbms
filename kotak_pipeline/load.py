from db import get_engine
from logger import logger

def load_dataframe(df, table):

    engine = get_engine()

    logger.info(f"Inserting {len(df)} rows into {table}")

    df.to_sql(
        table,
        engine,
        if_exists="append",
        index=False,
        method="multi",
        chunksize=5000
    )

    logger.info("Insert completed")