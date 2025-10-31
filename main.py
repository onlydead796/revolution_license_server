import os
import string
import random
import psycopg2
from flask import Flask, request, jsonify
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("APP_SECRET_KEY")

DB_URL = os.getenv("DB_URL")

def get_db():
    return psycopg2.connect(DB_URL)

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS licenses (
            id SERIAL PRIMARY KEY,
            username VARCHAR(100) NOT NULL,
            license_key VARCHAR(50) UNIQUE NOT NULL,
            expiry_days INTEGER NOT NULL,
            start_date TIMESTAMP NOT NULL,
            created_at TIMESTAMP NOT NULL
        )
    ''')
    conn.commit()
    cur.close()
    conn.close()

def generate_license_key():
    chars = string.ascii_uppercase + string.digits
    return '-'.join(''.join(random.choice(chars) for _ in range(4)) for _ in range(6))

# --------------------- Ana Sayfa ve Panel Kapat ---------------------
@app.route("/", methods=["GET", "POST"])
def index():
    return "404 Not Found", 404

@app.route("/panel")
def panel():
    return "404 Not Found", 404

@app.route("/add_license", methods=["POST"])
def add_license():
    return "404 Not Found", 404

@app.route("/delete_license/<int:id>")
def delete_license(id):
    return "404 Not Found", 404

@app.route("/extend_license/<int:id>", methods=["POST"])
def extend_license(id):
    return "404 Not Found", 404

# --------------------- Lisans Kontrol API ---------------------
@app.route("/panel/api/check_license", methods=["POST"])
def api_check_license():
    data = request.get_json()
    username = data.get("username", "").strip()
    license_key = data.get("license_key", "").strip()

    if not username or not license_key:
        return jsonify({
            "success": False,
            "status": "error", 
            "message": "Kullanıcı adı ve lisans anahtarı gerekli"
        }), 400

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT username, license_key, start_date, expiry_days FROM licenses WHERE username = %s", (username,))
    user_row = cur.fetchone()
    conn.close()

    if not user_row:
        return jsonify({
            "success": False,
            "status": "error", 
            "message": "Kullanıcı adı hatalı"
        }), 404

    db_username, db_license_key, start_date, expiry_days = user_row
    if db_license_key != license_key:
        return jsonify({
            "success": False,
            "status": "error", 
            "message": "Lisans anahtarı hatalı"
        }), 404

    expiry_date = start_date + timedelta(days=expiry_days)
    expiry_date = expiry_date.replace(hour=23, minute=59, second=59, microsecond=0)
    days_left = max((expiry_date - datetime.utcnow()).days, 0)

    if datetime.utcnow() > expiry_date:
        return jsonify({
            "success": False,
            "status": "error",
            "message": "Lisans süresi dolmuş",
            "username": db_username,
            "license_key": db_license_key,
            "expire_date": expiry_date.strftime("%Y-%m-%d"),
            "days_left": 0
        }), 403

    return jsonify({
        "success": True,
        "status": "success",
        "username": db_username,
        "license_key": db_license_key,
        "start_date": start_date.strftime("%Y-%m-%d"),
        "expire_date": expiry_date.strftime("%Y-%m-%d"),
        "days_left": days_left
    })

# --------------------- Run App ---------------------
if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
