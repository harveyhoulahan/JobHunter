import os
import sys

# Add parent directory to path so we can import web_app
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from web_app import app

# For production, use environment variable for database
# Set DATABASE_URL in Vercel environment variables
# Example: postgresql://user:pass@host/dbname or sqlite:///path/to/db
if os.getenv('DATABASE_URL'):
    # Production database configured
    pass
else:
    # Development mode - create empty database if needed
    from src.database.models import Database
    db = Database()
    db.create_tables()

# Vercel serverless function handler
def handler(request):
    return app(request)
