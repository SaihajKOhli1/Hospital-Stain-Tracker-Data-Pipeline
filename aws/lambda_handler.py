"""AWS Lambda handler for S3-triggered ETL."""
import os
import json
from app.etl.ingest_capacity_s3 import run_from_s3


def handler(event, context):
    """
    Lambda handler for S3 Put events.
    
    Expects standard S3 event format:
    {
        "Records": [{
            "s3": {
                "bucket": {"name": "bucket-name"},
                "object": {"key": "path/to/file.csv"}
            }
        }]
    }
    """
    # Parse S3 event
    record = event["Records"][0]
    bucket = record["s3"]["bucket"]["name"]
    key = record["s3"]["object"]["key"]
    
    # URL decode the key (S3 events may have URL-encoded keys)
    import urllib.parse
    key = urllib.parse.unquote_plus(key)
    
    # Get source name from environment variable or use default
    source = os.getenv("SOURCE_NAME", "hhs_capacity")
    
    # Run ETL
    try:
        result = run_from_s3(bucket, key, source)
        
        # Log compact summary
        log_msg = (
            f"ETL completed | bucket={bucket} | key={key} | "
            f"run_id={result['run_id']} | "
            f"rows_in={result['rows_in']} | "
            f"rows_loaded={result['rows_loaded']} | "
            f"rows_rejected={result['rows_rejected']}"
        )
        print(log_msg)
        
        return result
        
    except Exception as e:
        error_msg = f"ETL failed | bucket={bucket} | key={key} | error={str(e)}"
        print(error_msg)
        raise

