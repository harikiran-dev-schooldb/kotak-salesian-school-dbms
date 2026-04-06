import pandas as pd


def find_missing_students(atom_df, daywise_df):

    merged = atom_df.merge(
        daywise_df,
        left_on="admission_no",
        right_on="admissionno",
        how="left",
        indicator=True
    )

    missing = merged[merged["_merge"] == "left_only"]

    return missing