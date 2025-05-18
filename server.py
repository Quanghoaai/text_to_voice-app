# server.py
from flask import Flask, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import json
import base64
from cryptography.fernet import Fernet
import datetime
import logging
import os
from dotenv import load_dotenv

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('server.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- Load or Generate Fernet Key ---
load_dotenv()
KEY = os.getenv("FERNET_KEY")
if not KEY:
    KEY = Fernet.generate_key().decode()
    with open('.env', 'w') as f:
        f.write(f"FERNET_KEY={KEY}\n")
    logger.info(f"Generated new Fernet key: {KEY}")
else:
    logger.info("Loaded Fernet key from .env")

try:
    cipher = Fernet(KEY.encode())
except Exception as e:
    logger.error(f"Failed to initialize Fernet cipher: {e}")
    exit(1)

# --- Flask Setup ---
app = Flask(__name__)
limiter = Limiter(app=app, key_func=get_remote_address, default_limits=["100 per day", "10 per minute"])

# --- Subscription Packages ---
PACKAGES = {
    "1M": 30,
    "3M": 90,
    "6M": 180,
    "PERM": None
}

@app.route('/activate', methods=['POST'])
@limiter.limit("5 per minute")
def activate_license():
    """Handles license activation requests."""
    try:
        data = request.get_json()
        if not data:
            logger.warning("Invalid JSON request")
            return jsonify({"error": "Invalid JSON"}), 400

        machine_id = data.get('machine_id')
        package = data.get('package')

        if not machine_id or not isinstance(machine_id, str) or len(machine_id) < 8:
            logger.warning("Invalid machine_id")
            return jsonify({"error": "Invalid machine_id"}), 400

        if package not in PACKAGES:
            logger.warning(f"Invalid package: {package}")
            return jsonify({"error": "Invalid package"}), 400

        start_date = datetime.datetime.now()
        expiry_date = "Vĩnh viễn" if package == "PERM" else (
            start_date + datetime.timedelta(days=PACKAGES[package])
        ).strftime("%d/%m/%Y %H:%M:%S")

        license_data = {
            "username": "hoanq",
            "voice_id": "Free",
            "registration_date": start_date.strftime("%d/%m/%Y %H:%M:%S"),
            "status": "Đã đăng ký",
            "expiration_date": expiry_date,
            "package": package,
            "machine_id": machine_id
        }

        encrypted_data = cipher.encrypt(json.dumps(license_data).encode())
        encoded_data = base64.b64encode(encrypted_data).decode()

        logger.info(f"Activated license for machine_id: {machine_id}, package: {package}")
        return jsonify({"license": encoded_data})
    except Exception as e:
        logger.error(f"Error processing activation: {e}")
        return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    logger.info(f"Starting Flask server with KEY: {KEY}")
    app.run(host='0.0.0.0', port=5000, debug=False)