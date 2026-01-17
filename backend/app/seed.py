"""Temporary database seed script to validate hospital strain schema."""
from datetime import date
from sqlalchemy.orm import Session
from .db import SessionLocal
from .models import Region, PipelineRun, HospitalCapacityDaily


def seed_database():
    """Seed the database with test data. Idempotent - safe to run multiple times."""
    db: Session = SessionLocal()
    
    try:
        # 1. Get or create Test Region
        test_region = db.query(Region).filter(Region.name == "Test Region").first()
        if not test_region:
            test_region = Region(
                name="Test Region",
                population=1000000
            )
            db.add(test_region)
            db.flush()  # Flush to get the region_id
            print(f"Created Test Region with ID: {test_region.region_id}")
        else:
            print(f"Reusing existing Test Region with ID: {test_region.region_id}")
        
        # 2. Create PipelineRun
        pipeline_run = PipelineRun(
            source="manual_seed",
            status="success",
            rows_in=1,
            rows_loaded=1
        )
        db.add(pipeline_run)
        db.flush()  # Flush to get the run_id
        print(f"Created PipelineRun with ID: {pipeline_run.run_id}")
        
        # 3. Check if HospitalCapacityDaily row exists for today and this region
        today = date.today()
        existing_capacity = db.query(HospitalCapacityDaily).filter(
            HospitalCapacityDaily.date == today,
            HospitalCapacityDaily.region_id == test_region.region_id
        ).first()
        
        if existing_capacity:
            print(f"Capacity row for {today} and Test Region already exists. Skipping.")
        else:
            capacity = HospitalCapacityDaily(
                date=today,
                region_id=test_region.region_id,
                total_beds=1000,
                occupied_beds=850,
                icu_beds=100,
                icu_occupied=92,
                source_run_id=pipeline_run.run_id
            )
            db.add(capacity)
            print(f"Created HospitalCapacityDaily row for {today}")
        
        # Commit all changes
        db.commit()
        print("Seed completed successfully!")
        
    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()

