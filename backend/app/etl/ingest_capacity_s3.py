"""ETL script to ingest hospital capacity CSV data from S3."""
import argparse
import os
import tempfile
import boto3
from botocore.exceptions import ClientError

from .ingest_capacity import process_capacity_csv


def download_from_s3(bucket: str, key: str, local_path: str):
    """Download a file from S3 to a local path."""
    s3_client = boto3.client('s3')
    try:
        print(f"Downloading s3://{bucket}/{key} to {local_path}")
        s3_client.download_file(bucket, key, local_path)
        print(f"Successfully downloaded to {local_path}")
    except ClientError as e:
        raise Exception(f"Failed to download from S3: {e}")


def run_from_s3(bucket: str, key: str, source: str) -> dict:
    """
    Run ETL for an S3 object.
    Downloads from S3 to /tmp, processes, and returns result dict.
    """
    # Use /tmp for Lambda compatibility (writable in Lambda runtime)
    # Extract filename from S3 key for temp file
    filename = os.path.basename(key) or "hospital_capacity_raw.csv"
    local_path = os.path.join("/tmp", filename)
    
    try:
        # Download from S3 to temp file
        download_from_s3(bucket, key, local_path)
        
        # Process the CSV using the refactored function
        result = process_capacity_csv(local_path, source)
        
        return result
        
    finally:
        # Clean up temp file
        if os.path.exists(local_path):
            os.remove(local_path)
            print(f"Cleaned up temp file: {local_path}")


def main():
    """CLI entrypoint for S3-based ingestion."""
    parser = argparse.ArgumentParser(description="Ingest hospital capacity CSV data from S3")
    parser.add_argument(
        "--bucket",
        required=True,
        help="S3 bucket name"
    )
    parser.add_argument(
        "--key",
        required=True,
        help="S3 object key (path within bucket)"
    )
    parser.add_argument(
        "--source",
        required=True,
        help="Source identifier for the pipeline run"
    )
    
    args = parser.parse_args()
    
    result = run_from_s3(args.bucket, args.key, args.source)
    print(f"ETL completed: {result}")


if __name__ == "__main__":
    main()

