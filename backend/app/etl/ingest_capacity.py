"""ETL script to ingest hospital capacity CSV data into PostgreSQL."""
import argparse
import os
from datetime import datetime, date
from pathlib import Path
from typing import List, Dict, Any, Tuple
import pandas as pd
from sqlalchemy.dialects.postgresql import insert as pg_insert
import uuid

from ..db import SessionLocal
from ..models import PipelineRun, Region, HospitalCapacityDaily


def parse_date(date_str: str) -> date:
    """Parse date string to datetime.date object."""
    try:
        return pd.to_datetime(date_str).date()
    except Exception as e:
        raise ValueError(f"Invalid date format: {date_str}") from e


def validate_row(row: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Validate a single row of capacity data.
    Returns (is_valid, error_message).
    """
    # Check required fields
    if pd.isna(row.get('date')):
        return False, "date is required"
    if pd.isna(row.get('region')):
        return False, "region is required"
    if pd.isna(row.get('total_beds')):
        return False, "total_beds is required"
    if pd.isna(row.get('occupied_beds')):
        return False, "occupied_beds is required"
    
    # Check numeric fields are not negative
    if row.get('total_beds', 0) < 0:
        return False, "total_beds cannot be negative"
    if row.get('occupied_beds', 0) < 0:
        return False, "occupied_beds cannot be negative"
    
    # Validate occupied_beds <= total_beds
    if row.get('occupied_beds', 0) > row.get('total_beds', 0):
        return False, "occupied_beds cannot exceed total_beds"
    
    # Validate ICU fields if present
    if not pd.isna(row.get('icu_beds')):
        if row.get('icu_beds', 0) < 0:
            return False, "icu_beds cannot be negative"
        
        if not pd.isna(row.get('icu_occupied')):
            if row.get('icu_occupied', 0) < 0:
                return False, "icu_occupied cannot be negative"
            if row.get('icu_occupied', 0) > row.get('icu_beds', 0):
                return False, "icu_occupied cannot exceed icu_beds"
    
    return True, ""


def get_or_create_region(db, region_name: str) -> uuid.UUID:
    """Get existing region or create new one. Returns region_id."""
    region = db.query(Region).filter(Region.name == region_name).first()
    if region:
        return region.region_id
    
    new_region = Region(name=region_name)
    db.add(new_region)
    db.flush()
    return new_region.region_id


def process_capacity_csv(input_path: str, source: str) -> dict:
    """
    Runs the ETL for a local CSV path.
    Returns a dict with run_id, rows_in, rows_loaded, rows_rejected, rejects_path (if any).
    """
    db = SessionLocal()
    run_id = None
    rejects_path = None
    
    try:
        # Create PipelineRun with status="running"
        pipeline_run = PipelineRun(
            source=source,
            status="running",
            rows_in=0,
            rows_loaded=0,
            rows_rejected=0,
            notes=f"Input file: {input_path}"
        )
        db.add(pipeline_run)
        db.flush()
        run_id = pipeline_run.run_id
        print(f"Created PipelineRun: {run_id}")
        
        # Read CSV
        print(f"Reading CSV: {input_path}")
        df = pd.read_csv(input_path)
        total_rows = len(df)
        pipeline_run.rows_in = total_rows
        db.flush()
        
        # Map columns
        column_mapping = {
            'date': 'date',
            'state': 'region',
            'inpatient_beds': 'total_beds',
            'inpatient_beds_used': 'occupied_beds',
            'total_staffed_adult_icu_beds': 'icu_beds',
            'staffed_adult_icu_bed_occupancy': 'icu_occupied'
        }
        
        # Check required HHS columns exist (before mapping)
        # Expected columns: 'date', 'state', 'inpatient_beds', 'inpatient_beds_used', 
        #                  'total_staffed_adult_icu_beds', 'staffed_adult_icu_bed_occupancy'
        missing_cols = [k for k in column_mapping.keys() if k not in df.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")
        
        # Select and rename columns
        df = df[list(column_mapping.keys())].rename(columns=column_mapping)
        
        # Parse date
        df['date'] = df['date'].apply(parse_date)
        
        # Validate rows
        print("Validating rows...")
        accepted_rows = []
        rejected_rows = []
        
        for idx, row in df.iterrows():
            row_dict = row.to_dict()
            is_valid, error_msg = validate_row(row_dict)
            
            if is_valid:
                accepted_rows.append(row_dict)
            else:
                rejected_row = row_dict.copy()
                rejected_row['_reject_reason'] = error_msg
                rejected_row['_original_index'] = idx
                rejected_rows.append(rejected_row)
        
        # Write rejected rows to CSV
        if rejected_rows:
            rejects_dir = Path("/tmp/rejects")
            rejects_dir.mkdir(parents=True, exist_ok=True)
            rejects_path = rejects_dir / f"capacity_rejects_{run_id}.csv"
            
            rejects_df = pd.DataFrame(rejected_rows)
            rejects_df.to_csv(rejects_path, index=False)
            print(f"Wrote {len(rejected_rows)} rejected rows to {rejects_path}")
        
        # Process accepted rows
        print(f"Processing {len(accepted_rows)} accepted rows...")
        
        # Get or create regions and build region_id mapping
        region_id_map = {}
        for row in accepted_rows:
            region_name = row['region']
            if region_name not in region_id_map:
                region_id_map[region_name] = get_or_create_region(db, region_name)
        
        # Prepare capacity data for upsert
        capacity_data = []
        for row in accepted_rows:
            capacity_data.append({
                'date': row['date'],
                'region_id': region_id_map[row['region']],
                'total_beds': int(row['total_beds']),
                'occupied_beds': int(row['occupied_beds']),
                'icu_beds': int(row['icu_beds']) if not pd.isna(row.get('icu_beds')) else None,
                'icu_occupied': int(row['icu_occupied']) if not pd.isna(row.get('icu_occupied')) else None,
                'source_run_id': run_id
            })
        
        # Upsert capacity data using PostgreSQL ON CONFLICT
        if capacity_data:
            stmt = pg_insert(HospitalCapacityDaily).values(capacity_data)
            # Use excluded table for ON CONFLICT updates
            excluded = stmt.excluded
            stmt = stmt.on_conflict_do_update(
                index_elements=['date', 'region_id'],
                set_={
                    'total_beds': excluded.total_beds,
                    'occupied_beds': excluded.occupied_beds,
                    'icu_beds': excluded.icu_beds,
                    'icu_occupied': excluded.icu_occupied,
                    'source_run_id': excluded.source_run_id
                }
            )
            db.execute(stmt)
        
        # Update PipelineRun
        pipeline_run.status = "success"
        pipeline_run.rows_loaded = len(accepted_rows)
        pipeline_run.rows_rejected = len(rejected_rows)
        pipeline_run.ended_at = datetime.now()
        
        db.commit()
        print(f"Successfully loaded {len(accepted_rows)} rows, rejected {len(rejected_rows)} rows")
        
        # Return summary
        return {
            'run_id': str(run_id),
            'rows_in': total_rows,
            'rows_loaded': len(accepted_rows),
            'rows_rejected': len(rejected_rows),
            'rejects_path': str(rejects_path) if rejects_path else None
        }
        
    except Exception as e:
        db.rollback()
        if run_id:
            # Update PipelineRun status to failed
            failed_run = db.query(PipelineRun).filter(PipelineRun.run_id == run_id).first()
            if failed_run:
                failed_run.status = "failed"
                failed_run.ended_at = datetime.now()
                failed_run.notes = f"Error: {str(e)}"
                db.commit()
        print(f"Error during ingestion: {e}")
        raise
    finally:
        db.close()


def main():
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description="Ingest hospital capacity CSV data")
    parser.add_argument(
        "--input",
        required=True,
        help="Path to input CSV file"
    )
    parser.add_argument(
        "--source",
        required=True,
        help="Source identifier for the pipeline run"
    )
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input):
        raise FileNotFoundError(f"Input file not found: {args.input}")
    
    result = process_capacity_csv(args.input, args.source)
    print(f"ETL completed: {result}")


if __name__ == "__main__":
    main()

