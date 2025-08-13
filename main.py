import os
import string
import random
import psycopg2
from flask import Flask, render_template, request, redirect, session, flash, jsonify
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("APP_SECRET_KEY")

DB_URL = os.getenv("DB_URL")
ADMIN_USER = os.getenv("ADMIN_USERNAME")
ADMIN_PASS = os.getenv("ADMIN_PASSWORD")

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

# --------------------- Panel Routes ---------------------
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if username == ADMIN_USER and password == ADMIN_PASS:
            session["user"] = username
            flash("✅ Başarıyla giriş yapıldı.", "success")
            return redirect("/panel")
        flash("❌ Hatalı kullanıcı adı veya şifre", "danger")
    return render_template("login.html")

@app.route("/panel")
def panel():
    if "user" not in session:
        return redirect("/")
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, username, license_key, expiry_days, start_date, created_at
        FROM licenses
        ORDER BY created_at ASC
    """)
    rows = cur.fetchall()
    conn.close()

    licenses = []
    for row in rows:
        start_date = row[4]
        expiry_date = start_date + timedelta(days=row[3])
        expiry_date = expiry_date.replace(hour=23, minute=59, second=59, microsecond=0)
        days_left = (expiry_date - datetime.utcnow()).days

        licenses.append({
            "id": row[0],
            "username": row[1],
            "key": row[2],
            "start_date": start_date.strftime("%Y-%m-%d"),
            "expiry_date": expiry_date.strftime("%Y-%m-%d"),
            "days_left": max(days_left, 0)
        })

    return render_template("index.html", licenses=licenses)

@app.route("/add_license", methods=["POST"])
def add_license():
    if "user" not in session:
        return redirect("/")
    username = request.form.get("username", "").strip()
    key = request.form.get("key", "").strip()
    days = request.form.get("days", "").strip()

    if not username:
        flash("⚠️ Kullanıcı adı boş olamaz.", "danger")
        return redirect("/panel")

    if not key:
        key = generate_license_key()

    try:
        days = int(days)
        if days < 1:
            days = 30
    except:
        days = 30

    now = datetime.utcnow() + timedelta(hours=3)
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO licenses (username, license_key, expiry_days, start_date, created_at) VALUES (%s, %s, %s, %s, %s)",
        (username, key, days, now, now)
    )
    conn.commit()
    conn.close()
    flash(f"✅ Lisans başarıyla eklendi: {key}", "success")
    return redirect("/panel")

@app.route("/delete_license/<int:id>")
def delete_license(id):
    if "user" not in session:
        return redirect("/")
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM licenses WHERE id = %s", (id,))
    conn.commit()
    conn.close()
    flash("🗑️ Lisans silindi.", "warning")
    return redirect("/panel")

@app.route("/logout")
def logout():
    session.clear()
    flash("👋 Başarıyla çıkış yapıldı.", "info")
    return redirect("/")

@app.route("/extend_license/<int:id>", methods=["POST"])
def extend_license(id):
    if "user" not in session:
        return redirect("/")

    try:
        extend_days = int(request.form.get("extend_days", "0"))
        if extend_days <= 0:
            flash("⚠️ Geçerli bir gün sayısı girin.", "danger")
            return redirect("/panel")
    except:
        flash("⚠️ Gün sayısı sayısal olmalı.", "danger")
        return redirect("/panel")

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT expiry_days FROM licenses WHERE id = %s", (id,))
    row = cur.fetchone()
    if not row:
        flash("❌ Lisans bulunamadı.", "danger")
        conn.close()
        return redirect("/panel")

    current_days = row[0]
    new_days = current_days + extend_days
    cur.execute("UPDATE licenses SET expiry_days = %s WHERE id = %s", (new_days, id))
    conn.commit()
    conn.close()

    flash(f"✅ Lisans süresi {extend_days} gün uzatıldı.", "success")
    return redirect("/panel")

# --------------------- Lisans Kontrol API ---------------------
@app.route("/panel/api/check_license", methods=["POST"])
def api_check_license():
    data = request.get_json()
    license_key = data.get("license_key", "").strip()

    if not license_key:
        return jsonify({"status": "error", "message": "Lisans anahtarı gerekli"}), 400

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT username, start_date, expiry_days FROM licenses WHERE license_key = %s", (license_key,))
    row = cur.fetchone()
    conn.close()

    if not row:
        return jsonify({"status": "error", "message": "Lisans bulunamadı"}), 404

    username, start_date, expiry_days = row
    expiry_date = start_date + timedelta(days=expiry_days)
    days_left = max((expiry_date - datetime.utcnow()).days, 0)

    if datetime.utcnow() > expiry_date:
        return jsonify({
            "status": "error",
            "message": "Lisans süresi dolmuş",
            "username": username,
            "expire_date": expiry_date.strftime("%Y-%m-%d"),
            "days_left": 0
        }), 403

    return jsonify({
        "status": "success",
        "username": username,
        "start_date": start_date.strftime("%Y-%m-%d"),
        "expire_date": expiry_date.strftime("%Y-%m-%d"),
        "days_left": days_left
    })

# --------------------- Run App ---------------------
if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)), debug=True)
