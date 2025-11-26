from web_app import app

# Vercel serverless function handler
def handler(request):
    return app(request)
