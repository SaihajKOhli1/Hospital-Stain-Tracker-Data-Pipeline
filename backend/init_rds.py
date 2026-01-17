"""One-time script to initialize RDS database."""
import os

# NOTE: Set DATABASE_URL environment variable before running this script.
# Example: export DATABASE_URL="postgresql://USER:YOUR_PASSWORD@HOST:5432/DB"
# Or use: DATABASE_URL="postgresql://USER:YOUR_PASSWORD@HOST:5432/DB" python init_rds.py

# Read from environment variable (do not hardcode passwords!)
database_url = os.environ.get("DATABASE_URL")
if not database_url:
    raise ValueError(
        "DATABASE_URL environment variable is required.\n"
        "Example: DATABASE_URL='postgresql://USER:YOUR_PASSWORD@HOST:5432/DB'"
    )

os.environ["DATABASE_URL"] = database_url

from app.db import init_db

if __name__ == "__main__":
    print("Initializing RDS database...")
    init_db()
    print("✅ Tables created successfully!")
