# 🏥 Hospital Strain Tracker

Real-time hospital capacity monitoring system with automated ETL pipeline and operational dashboard.

## Architecture

**Cloud Infrastructure (AWS)**
- S3: Raw data storage with versioning
- Lambda: Containerized ETL (Docker/ECR)
- RDS Postgres: Metrics database
- VPC: Secure networking with endpoint configuration

**Backend (Python/FastAPI)**
- RESTful API for metrics querying
- SQLAlchemy ORM with PostgreSQL
- Data validation & quality checks
- Pipeline observability (run tracking, reject logging)

**Frontend (HTML/Tailwind/Chart.js)**
- Professional dark-mode dashboard
- Real-time strain index calculations
- Historical trend analysis
- CSV export functionality

## Data Pipeline

CSV Upload → S3 Trigger → Lambda ETL → Validation → RDS → API → Dashboard

**ETL Features:**
- Automatic data ingestion from HHS hospital capacity reports
- Row-level validation with reject handling
- Idempotent upserts (prevents duplicates)
- Computed metrics: bed occupancy %, ICU utilization %, strain index

**Strain Index Formula:**
```
strain_index = min(100, max(0, 0.4 × bed_score + 0.6 × icu_score))

where:
- bed_score = bed_occupancy_percentage × 100
- icu_score = icu_occupancy_percentage × 100 (if available, else bed_score)
```

The formula weights ICU occupancy at 60% and bed occupancy at 40%, reflecting the critical nature of ICU capacity. The final index is clamped between 0-100 for standardized reporting.

## Tech Stack

- **Cloud:** AWS (S3, Lambda, RDS, ECR, VPC)
- **Backend:** Python, FastAPI, SQLAlchemy, Pandas
- **Database:** PostgreSQL
- **Container:** Docker
- **Frontend:** HTML5, Tailwind CSS, Chart.js
- **Data Source:** U.S. HHS Hospital Capacity Dataset

## Key Features

✅ Automated serverless ETL pipeline
✅ 9,978+ rows of real hospital capacity data
✅ Color-coded strain indicators (crisis threshold: >80%)
✅ Day-over-day delta tracking
✅ Professional operational dashboard
✅ Data quality monitoring & observability

## Local Development

Backend:
```bash
cd backend
DATABASE_URL="postgresql://..." uvicorn app.main:app --reload
```

Dashboard:
```bash
open frontend/public/dashboard.html
```

## Deployment

Deployed on Railway with environment variables for database connection.

## Data Source

U.S. Department of Health & Human Services (HHS)  
COVID-19 Reported Patient Impact and Hospital Capacity by State
