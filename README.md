# Strain Tracker

A FastAPI-based backend for tracking hospital strain data with PostgreSQL database.

## Tech Stack

- Python 3.11
- FastAPI + Uvicorn
- SQLAlchemy 2.x
- PostgreSQL 16 (via Docker)
- Pydantic for settings and validation

## Quick Start

1. **Copy environment variables:**
   ```bash
   cp .env.example .env
   ```

2. **Start services:**
   ```bash
   docker compose up --build
   ```

3. **Test the API:**
   ```bash
   # Health check
   curl http://localhost:8000/health
   
   # Get pipeline runs
   curl http://localhost:8000/runs
   ```

   Or open in browser:
   - http://localhost:8000/health
   - http://localhost:8000/runs

## API Endpoints

- `GET /health` - Health check endpoint that verifies database connectivity
- `GET /runs` - Returns the last 20 pipeline runs ordered by started_at descending
- `GET /capacity/latest` - Returns the latest hospital capacity data by date

## Project Structure

```
strain-tracker/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py          # FastAPI application
│   │   ├── db.py            # Database connection and session management
│   │   ├── models.py        # SQLAlchemy models
│   │   └── settings.py      # Pydantic settings
│   ├── requirements.txt
│   └── Dockerfile
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
```

## Database

The application uses PostgreSQL 16 running in Docker. The database connection can be configured via:
- `DATABASE_URL` environment variable (preferred), or
- Individual components: `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`

Tables are automatically created on application startup via `init_db()`.

## Run ETL Locally

1. **Start services:**
   ```bash
   docker compose up
   ```

2. **Run the ETL script:**
   ```bash
   docker compose exec backend python -m app.etl.ingest_capacity --input data/raw/hospital_capacity_raw.csv --source hhs_capacity
   ```

3. **Verify the results:**
   - Check pipeline runs: http://localhost:8000/runs
   - Check latest capacity data: http://localhost:8000/capacity/latest

The ETL script will:
- Create a pipeline run record
- Read and validate the CSV file
- Reject invalid rows (written to `data/rejects/capacity_rejects_<run_id>.csv`)
- Upsert regions and capacity data
- Update the pipeline run with success/failure status

## AWS Lambda Deployment

The ETL is Lambda-container ready for S3-triggered processing.

### Build Lambda Container Image

Build the Lambda container image locally:

```bash
docker build -f aws/Dockerfile.lambda -t strain-tracker-lambda .
```

This creates a container image with:
- AWS Lambda Python 3.11 base image
- All backend dependencies (pandas, pyarrow, boto3, etc.)
- ETL code and Lambda handler

### Lambda Handler

The Lambda handler (`aws/lambda_handler.py`) processes S3 Put events:
- Parses S3 event to extract bucket and key
- Downloads CSV from S3 to `/tmp`
- Runs ETL processing
- Returns summary with run_id, rows_in, rows_loaded, rows_rejected

### Deployment

To deploy:
1. Push the container image to Amazon ECR
2. Create Lambda function using the container image
3. Configure S3 bucket event to trigger Lambda on Put events
4. Set environment variables (e.g., `SOURCE_NAME`, database connection)

See `aws/events/s3_put_example.json` for example S3 event format.

## Frontend

The frontend is a React + TypeScript application built with Vite.

1. **Navigate to frontend directory:**
   ```bash
   cd frontend
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Start the development server:**
   ```bash
   npm run dev
   ```

4. **Open in browser:**
   - http://localhost:5173

The frontend displays hospital strain metrics with:
- A table showing region, bed occupancy %, ICU occupancy %, and strain index
- A bar chart visualizing strain index by region
- Date filtering to view metrics for specific dates

## Development

The backend service runs with `--reload` flag for hot-reloading during development. Code changes in `backend/app/` will automatically restart the server.

