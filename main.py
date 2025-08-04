import os
import string
import random
import psycopg2
from flask import Flask, render_template, request, redirect, session, flash
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
        days_left = (expiry_date - datetime.utcnow()).days

        licenses.append({
            "id": row[0],
            "username": row[1],
            "key": row[2],
            "start_date": start_date.strftime("%Y-%m-%d"),
            "expiry_date": expiry_date.strftime("%Y-%m-%d 23:59:59"),
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

    now = datetime.utcnow()
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

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)), debug=True)