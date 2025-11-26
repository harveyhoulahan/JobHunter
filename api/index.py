import os
import sys

# Add parent directory to path so we can import mobile_remote
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from mobile_remote import app

# Vercel serverless function handler
def handler(request):
    return app(request)
