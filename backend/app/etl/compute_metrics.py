"""ETL script to compute daily metrics from hospital capacity data."""
import argparse
from datetime import datetime
from typing import Optional
from sqlalchemy.dialects.postgresql import insert as pg_insert

from ..db import SessionLocal
from ..models import PipelineRun, HospitalCapacityDaily, MetricsDaily


def compute_strain_index(bed_occ_pct: float, icu_occ_pct: Optional[float]) -> float:
    """
    Compute strain index from occupancy percentages.
    Formula: min(100, max(0, 0.4*bed_score + 0.6*icu_score))
    where bed_score = bed_occ_pct * 100
    and icu_score = icu_occ_pct * 100 if present, else bed_score
    """
    bed_score = bed_occ_pct * 100
    icu_score = (icu_occ_pct * 100) if icu_occ_pct is not None else bed_score
    strain_index = 0.4 * bed_score + 0.6 * icu_score
    return round(min(100, max(0, strain_index)), 2)


def compute_metrics(source: str):
    """Main function to compute metrics from capacity data."""
    db = SessionLocal()
    run_id = None
    
    try:
        # Create PipelineRun with status="running"
        pipeline_run = PipelineRun(
            source=source,
            status="running",
            rows_in=0,
            rows_loaded=0,
            rows_rejected=0,
            notes="Metrics computation from hospital_capacity_daily"
        )
        db.add(pipeline_run)
        db.flush()
        run_id = pipeline_run.run_id
        print(f"Created PipelineRun: {run_id}")
        
        # Query all rows from hospital_capacity_daily
        print("Querying hospital capacity data...")
        capacity_rows = db.query(HospitalCapacityDaily).all()
        total_rows = len(capacity_rows)
        pipeline_run.rows_in = total_rows
        db.flush()
        print(f"Found {total_rows} capacity rows to process")
        
        # Compute metrics for each row
        metrics_data = []
        for capacity in capacity_rows:
            # Compute bed_occ_pct
            bed_occ_pct = capacity.occupied_beds / capacity.total_beds if capacity.total_beds > 0 else 0.0
            
            # Compute icu_occ_pct
            icu_occ_pct = None
            if capacity.icu_beds and capacity.icu_occupied is not None and capacity.icu_beds > 0:
                icu_occ_pct = capacity.icu_occupied / capacity.icu_beds
            
            # Compute strain_index
            strain_index = compute_strain_index(bed_occ_pct, icu_occ_pct)
            
            metrics_data.append({
                'date': capacity.date,
                'region_id': capacity.region_id,
                'bed_occ_pct': bed_occ_pct,
                'icu_occ_pct': icu_occ_pct,
                'strain_index': strain_index,
                'source_run_id': run_id
            })
        
        # Upsert metrics data using PostgreSQL ON CONFLICT
        if metrics_data:
            print(f"Upserting {len(metrics_data)} metrics rows...")
            stmt = pg_insert(MetricsDaily).values(metrics_data)
            excluded = stmt.excluded
            stmt = stmt.on_conflict_do_update(
                index_elements=['date', 'region_id'],
                set_={
                    'bed_occ_pct': excluded.bed_occ_pct,
                    'icu_occ_pct': excluded.icu_occ_pct,
                    'strain_index': excluded.strain_index,
                    'source_run_id': excluded.source_run_id
                }
            )
            db.execute(stmt)
        
        # Update PipelineRun
        pipeline_run.status = "success"
        pipeline_run.rows_loaded = len(metrics_data)
        pipeline_run.rows_rejected = 0
        pipeline_run.ended_at = datetime.now()
        
        db.commit()
        print(f"Successfully computed and loaded {len(metrics_data)} metrics rows")
        
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
        print(f"Error during metrics computation: {e}")
        raise
    finally:
        db.close()


def main():
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description="Compute daily metrics from hospital capacity data")
    parser.add_argument(
        "--source",
        required=True,
        help="Source identifier for the pipeline run"
    )
    
    args = parser.parse_args()
    compute_metrics(args.source)


if __name__ == "__main__":
    main()

