Cách chạy 2 file 
Bước 1: Chạy 
server.py sẽ sinh ra key
python server.py
2025-05-18 17:12:35,413 [INFO] Loaded Fernet key from .env

2025-05-18 17:12:35,425 [INFO] Starting Flask server with KEY: V0429G-GlyXHD2a6NfRCiRcAcFFbn7JvP9oe35kz6Sc=
 * Serving Flask app 'server'
 * Debug mode: off
2025-05-18 17:12:35,457 [INFO] ←[31m←[1mWARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.←[0m
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:5000
 * Running on http://192.168.2.35:5000
2025-05-18 17:12:35,458 [INFO] ←[33mPress CTRL+C to quit←[0m

Bước 2
Chạy file client.py 
Để chạy file này cần Copy key từ bước 1 paste vào đoạn

KEY = b'PUT_YOUR_SERVER_KEY_HERE'  # Example: b'gXjB4Z3X9y7zK2mPqWvL8tR5nF0hJ6uYxC1dE2aB3cI='
