from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from sqlalchemy.orm import Session, aliased
from sqlalchemy import text, func
from typing import List, Optional
from datetime import date as date_type, timedelta, datetime
from pathlib import Path
import os
from .db import get_db, init_db
from .models import PipelineRun, Region, HospitalCapacityDaily, MetricsDaily
from .settings import settings

# Build ID for Railway verification
BUILD_ID = "railway-proof-2026-01-17-0225"

app = FastAPI(title="Strain Tracker API")


@app.get("/_railway", include_in_schema=False)
def railway_health():
    return PlainTextResponse("ok", status_code=200)


# CORS origins configuration
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "").strip()
CORS_ORIGINS = [
    "https://hospital-stain-tracker-data-pipelin.vercel.app",
    "http://localhost:3000",
    "http://localhost:5173",
]
if FRONTEND_ORIGIN and FRONTEND_ORIGIN not in CORS_ORIGINS:
    CORS_ORIGINS.append(FRONTEND_ORIGIN)


class ConditionalCORSMiddleware(BaseHTTPMiddleware):
    """Custom CORS middleware that excludes /health endpoint."""
    
    async def dispatch(self, request: Request, call_next):
        # Skip CORS for /health endpoint
        if request.url.path == "/health":
            response = await call_next(request)
            return response
        
        # Apply CORS headers for all other routes
        origin = request.headers.get("origin")
        if origin in CORS_ORIGINS:
            response = await call_next(request)
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "false"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "*"
            return response
        
        # Handle preflight OPTIONS requests
        if request.method == "OPTIONS":
            response = Response()
            if origin in CORS_ORIGINS:
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Credentials"] = "false"
                response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
                response.headers["Access-Control-Allow-Headers"] = "*"
            return response
        
        response = await call_next(request)
        return response


# Add custom CORS middleware
app.add_middleware(ConditionalCORSMiddleware)

# Diagnostic prints for Railway troubleshooting
print("[DIAG] cwd:", os.getcwd())
print("[DIAG] file:", Path(__file__).resolve())


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    init_db()
    # Print startup banner
    print("\n" + "="*50)
    print("🚑 Hospital Strain Tracker API running")
    print("Base URL: http://localhost:8000")
    print("Docs: http://localhost:8000/docs")
    print("="*50 + "\n")


@app.get("/health")
async def health():
    """Health check endpoint - simplest possible, no DB or file reads."""
    return {"ok": True}


@app.get("/__hc_proof")
async def hc_proof(request: Request):
    """Debug endpoint for healthcheck troubleshooting."""
    return {
        "method": request.method,
        "path": request.url.path,
        "time": datetime.now().isoformat()
    }


@app.get("/__whoami")
async def whoami():
    """Debug endpoint to verify Railway deployment and paths."""
    return {
        "build_id": BUILD_ID,
        "cwd": os.getcwd(),
        "main_file": str(Path(__file__).resolve())
    }


@app.get("/__build")
async def build_id():
    """Return build ID as plain text."""
    return PlainTextResponse(BUILD_ID)


@app.get("/__cors")
async def cors_debug():
    """Debug endpoint to verify CORS origins configuration."""
    return {
        "origins": CORS_ORIGINS,
        "env_frontend_origin": FRONTEND_ORIGIN
    }


@app.get("/runs")
async def get_runs(db: Session = Depends(get_db)) -> List[dict]:
    """Get last 20 pipeline runs ordered by started_at descending."""
    runs = db.query(PipelineRun).order_by(PipelineRun.started_at.desc()).limit(20).all()
    return [
        {
            "run_id": str(run.run_id),
            "source": run.source,
            "status": run.status,
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "ended_at": run.ended_at.isoformat() if run.ended_at else None,
            "rows_in": run.rows_in,
            "rows_loaded": run.rows_loaded,
            "rows_rejected": run.rows_rejected,
            "notes": run.notes,
        }
        for run in runs
    ]


@app.get("/capacity/latest")
async def get_latest_capacity(
    db: Session = Depends(get_db),
    date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format. If not provided, returns latest available date.")
):
    """Get hospital capacity data by date. If no date provided, returns latest available date."""
    target_date = None
    
    # If date parameter is provided, parse and validate it
    if date is not None:
        try:
            target_date = date_type.fromisoformat(date)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid date format: '{date}'. Expected format: YYYY-MM-DD"
            )
    else:
        # Find the latest date if no date parameter provided
        latest_date_result = db.query(func.max(HospitalCapacityDaily.date)).scalar()
        if latest_date_result is None:
            return {"date": None, "rows": []}
        target_date = latest_date_result
    
    # Get all capacity rows for the target date, joined with regions
    capacity_rows = (
        db.query(HospitalCapacityDaily, Region)
        .join(Region, HospitalCapacityDaily.region_id == Region.region_id)
        .filter(HospitalCapacityDaily.date == target_date)
        .all()
    )
    
    rows = []
    for capacity, region in capacity_rows:
        bed_occ_pct = round(capacity.occupied_beds / capacity.total_beds, 4) if capacity.total_beds > 0 else None
        icu_occ_pct = (
            round(capacity.icu_occupied / capacity.icu_beds, 4)
            if capacity.icu_beds and capacity.icu_occupied is not None and capacity.icu_beds > 0
            else None
        )
        
        rows.append({
            "region": region.name,
            "total_beds": capacity.total_beds,
            "occupied_beds": capacity.occupied_beds,
            "bed_occ_pct": bed_occ_pct,
            "icu_beds": capacity.icu_beds,
            "icu_occupied": capacity.icu_occupied,
            "icu_occ_pct": icu_occ_pct,
        })
    
    return {
        "date": target_date.isoformat(),
        "rows": rows
    }


@app.get("/metrics/latest")
async def get_latest_metrics(
    db: Session = Depends(get_db),
    date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format. If not provided, returns latest available date.")
):
    """Get daily metrics by date. If no date provided, returns latest available date."""
    target_date = None
    
    # If date parameter is provided, parse and validate it
    if date is not None:
        try:
            target_date = date_type.fromisoformat(date)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid date format: '{date}'. Expected format: YYYY-MM-DD"
            )
    else:
        # Find the latest date if no date parameter provided
        latest_date_result = db.query(func.max(MetricsDaily.date)).scalar()
        if latest_date_result is None:
            return {"date": None, "rows": []}
        target_date = latest_date_result
    
    # Get all metrics rows for the target date, joined with regions
    metrics_rows = (
        db.query(MetricsDaily, Region)
        .join(Region, MetricsDaily.region_id == Region.region_id)
        .filter(MetricsDaily.date == target_date)
        .all()
    )
    
    rows = []
    for metrics, region in metrics_rows:
        rows.append({
            "region": region.name,
            "bed_occ_pct": metrics.bed_occ_pct,
            "icu_occ_pct": metrics.icu_occ_pct,
            "strain_index": metrics.strain_index,
        })
    
    return {
        "date": target_date.isoformat(),
        "rows": rows
    }


@app.get("/metrics/compare")
async def compare_metrics(
    db: Session = Depends(get_db),
    date: str = Query(..., description="Date in YYYY-MM-DD format")
):
    """Compare metrics for a given date with the previous day."""
    # Validate and parse date
    try:
        target_date = date_type.fromisoformat(date)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid date format: '{date}'. Expected format: YYYY-MM-DD"
        )
    
    prev_date = target_date - timedelta(days=1)
    
    # Create aliases for current and previous day metrics
    current_metrics = aliased(MetricsDaily)
    prev_metrics = aliased(MetricsDaily)
    
    # Query current day metrics joined with previous day metrics by region
    comparison_rows = (
        db.query(
            Region.name,
            current_metrics.strain_index,
            prev_metrics.strain_index.label('prev_strain_index')
        )
        .select_from(current_metrics)
        .join(Region, current_metrics.region_id == Region.region_id)
        .outerjoin(
            prev_metrics,
            (prev_metrics.region_id == current_metrics.region_id) & 
            (prev_metrics.date == prev_date)
        )
        .filter(current_metrics.date == target_date)
        .all()
    )
    
    rows = []
    for region_name, strain_index, prev_strain_index in comparison_rows:
        delta = None
        if prev_strain_index is not None:
            delta = strain_index - prev_strain_index
        
        rows.append({
            "region": region_name,
            "strain_index": strain_index,
            "prev_strain_index": prev_strain_index,
            "delta": delta
        })
    
    return {
        "date": target_date.isoformat(),
        "rows": rows
    }


@app.get("/metrics/available-dates")
async def get_available_dates(
    db: Session = Depends(get_db),
    full: bool = Query(False, description="If true, include full dates array")
):
    """Get available dates from the metrics_daily table."""
    # Efficient SQL aggregation for min, max, and count
    result = (
        db.query(
            func.min(MetricsDaily.date).label('min_date'),
            func.max(MetricsDaily.date).label('max_date'),
            func.count(func.distinct(MetricsDaily.date)).label('count')
        )
        .first()
    )
    
    min_date = result.min_date if result else None
    max_date = result.max_date if result else None
    count = result.count if result else 0
    
    # Base response
    response = {
        "min_date": min_date.isoformat() if min_date else None,
        "max_date": max_date.isoformat() if max_date else None,
        "count": count
    }
    
    # Only fetch full dates list if requested
    if full:
        date_results = (
            db.query(MetricsDaily.date)
            .distinct()
            .order_by(MetricsDaily.date.asc())
            .all()
        )
        date_strings = [row[0].isoformat() for row in date_results]
        response["dates"] = date_strings
    
    return response


@app.get("/metrics/coverage")
async def get_coverage(
    db: Session = Depends(get_db),
    min_rows: int = Query(30, description="Minimum number of rows (regions) required for a date to be included")
):
    """Get date coverage from the metrics_daily table, filtered by minimum row count."""
    # Query dates with row counts, filtered by minimum rows
    date_counts = (
        db.query(
            MetricsDaily.date,
            func.count(MetricsDaily.id).label('rows')
        )
        .group_by(MetricsDaily.date)
        .having(func.count(MetricsDaily.id) >= min_rows)
        .order_by(MetricsDaily.date.asc())
        .all()
    )
    
    # Format dates with row counts
    dates_list = [
        {"date": row.date.isoformat(), "rows": row.rows}
        for row in date_counts
    ]
    
    # Find best_date (most recent date among qualifying dates)
    best_date = None
    best_rows = 0
    if date_counts:
        # Get the maximum date from the results
        best_date_obj = max(row.date for row in date_counts)
        # Find the row count for that date
        best_row = next(row for row in date_counts if row.date == best_date_obj)
        best_date = best_date_obj.isoformat()
        best_rows = best_row.rows
    
    return {
        "min_rows": min_rows,
        "best_date": best_date,
        "best_rows": best_rows,
        "dates": dates_list
    }



