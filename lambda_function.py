"""
AWS Lambda handler that cleans a messy CSV uploaded to S3.

Triggered by an S3 "object created" event on the "input/" prefix. Downloads
the CSV, runs each row through cleaner.clean_record, and writes the cleaned
CSV back to the same bucket under the "output/" prefix.
"""

import io
import logging

import boto3
import pandas as pd

from cleaner import clean_record

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client("s3")


def lambda_handler(event, context):
    """Entry point invoked by the S3 trigger."""
    try:
        record = event["Records"][0]["s3"]
        bucket = record["bucket"]["name"]
        key = record["object"]["key"]

        # Only process files uploaded under "input/". Without this check, an
        # event on our own "output/" writes would trigger another (infinite)
        # run of this function.
        if not key.startswith("input/"):
            logger.info("Ignoring key outside input/ prefix: %s", key)
            return {
                "statusCode": 200,
                "body": f"Skipped {key}: not under input/ prefix.",
            }

        # Download the CSV object and decode it to text.
        response = s3.get_object(Bucket=bucket, Key=key)
        csv_text = response["Body"].read().decode("utf-8")

        # Load into a DataFrame, clean each row, and rebuild a DataFrame.
        df = pd.read_csv(io.StringIO(csv_text))
        cleaned_rows = [clean_record(row) for row in df.to_dict(orient="records")]
        cleaned_df = pd.DataFrame(cleaned_rows)

        cleaned_csv_text = cleaned_df.to_csv(index=False)

        # Write the cleaned CSV back under "output/", mirroring the input
        # filename with a "cleaned_" prefix.
        filename = key.split("/", 1)[1]
        output_key = f"output/cleaned_{filename}"
        s3.put_object(Bucket=bucket, Key=output_key, Body=cleaned_csv_text.encode("utf-8"))

        body = f"Processed {len(cleaned_rows)} rows from {key} to {output_key}."
        logger.info(body)
        return {"statusCode": 200, "body": body}

    except Exception:
        logger.exception("Failed to clean CSV for event: %s", event)
        raise
