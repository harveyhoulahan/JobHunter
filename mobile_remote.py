"""
Mobile Remote Control for JobHunter
Lightweight Flask app that proxies commands to your local desktop instance
"""
from flask import Flask, render_template, jsonify, request
import requests
import os
from datetime import datetime

app = Flask(__name__)

# Your desktop's public URL (we'll use ngrok or tailscale)
DESKTOP_URL = os.environ.get('DESKTOP_URL', 'http://localhost:5002')

@app.route('/')
def index():
    """Mobile-friendly control panel"""
    return render_template('mobile_control.html')

@app.route('/api/trigger_scrape', methods=['POST'])
def trigger_scrape():
    """Trigger scrape on desktop"""
    try:
        response = requests.post(f"{DESKTOP_URL}/api/run_scrape", timeout=5)
        return jsonify(response.json())
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/status', methods=['GET'])
def get_status():
    """Get desktop status"""
    try:
        response = requests.get(f"{DESKTOP_URL}/api/status", timeout=5)
        return jsonify(response.json())
    except Exception as e:
        return jsonify({
            'success': False, 
            'error': 'Desktop offline',
            'desktop_url': DESKTOP_URL
        }), 503

@app.route('/api/jobs/recent', methods=['GET'])
def get_recent_jobs():
    """Get recent jobs from desktop"""
    try:
        response = requests.get(f"{DESKTOP_URL}/api/jobs/recent", timeout=10)
        return jsonify(response.json())
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5003))
    app.run(host='0.0.0.0', port=port)
