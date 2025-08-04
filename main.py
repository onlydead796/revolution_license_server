import os
import random
import string
from datetime import datetime, timedelta
from flask import Flask, request, render_template, redirect, session, flash, url_for
from dotenv import load_dotenv
import psycopg2

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("APP_SECRET")

DB_URL = os.getenv("DATABASE_URL")

def get_db():
    return psycopg2.connect(DB_URL)

def generate_license_key(length=24):  # 6x4 grup
    chars = string.ascii_uppercase + string.digits
    return '-'.join(''.join(random.choice(chars) for _ in range(4)) for _ in range(length // 4))

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM admins WHERE username = %s AND license_key = %s", (username, password))
        admin = cur.fetchone()
        conn.close()

        if admin:
            session["user"] = username
            return redirect("/panel")
        else:
            flash("Kullanıcı adı veya şifre hatalı", "danger")

    return render_template("index.html")

@app.route("/panel")
def panel():
    if "user" not in session:
        return redirect("/")
    
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM licenses ORDER BY created_at DESC")
    licenses = cur.fetchall()
    conn.close()

    return render_template("panel.html", licenses=licenses)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/add_license", methods=["POST"])
def add_license():
    if "user" not in session:
        return redirect("/")

    username = request.form.get("username", "").strip()
    key = request.form.get("key", "").strip()
    days = request.form.get("days", "").strip()

    if not username:
        flash("❌ Kullanıcı adı boş olamaz.", "danger")
        return redirect("/panel")

    if not key:
        key = generate_license_key()

    try:
        days = int(days)
        if days < 1:
            days = 30
    except:
        days = 30

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO licenses (username, license_key, expiry_days, created_at) VALUES (%s, %s, %s, %s)",
        (username, key, days, datetime.utcnow())
    )
    conn.commit()
    conn.close()

    flash("✅ Lisans başarıyla oluşturuldu.", "success")
    return redirect("/panel")

if __name__ == "__main__":
    app.run(debug=True)