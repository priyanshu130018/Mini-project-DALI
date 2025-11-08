"""Flask server to serve DALI frontend"""

from flask import Flask, send_from_directory, jsonify
import os
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Serve static files from frontend folder
@app.route('/')
def index():
    return send_from_directory('frontend', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('frontend', path)

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'service': 'DALI Web Interface'})

if __name__ == '__main__':
    logger.info("🌐 Starting DALI Web Server...")
    logger.info("📱 Open browser: http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=False)
