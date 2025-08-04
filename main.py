import os
import psycopg2
from flask import Flask, render_template, request, redirect, session, flash
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("APP_SECRET_KEY")  # .env dosyasından okunacak

DB_URL = os.getenv("DB_URL")
ADMIN_USER = os.getenv("ADMIN_USERNAME")
ADMIN_PASS = os.getenv("ADMIN_PASSWORD")

def get_db():
    return psycopg2.connect(DB_URL)

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if username == ADMIN_USER and password == ADMIN_PASS:
            session["user"] = username
            flash("Başarıyla giriş yapıldı.", "success")
            return redirect("/panel")
        flash("Hatalı kullanıcı adı veya şifre", "danger")
    return render_template("login.html")

@app.route("/panel")
def panel():
    if "user" not in session:
        return redirect("/")
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, username, license_key, expiry_days, created_at FROM licenses ORDER BY created_at ASC")
    rows = cur.fetchall()
    conn.close()

    licenses = []
    for row in rows:
        created_date = row[4].date() if isinstance(row[4], datetime) else row[4]
        expiry_date = created_date + timedelta(days=row[3])
        days_left = (expiry_date - datetime.utcnow().date()).days

        licenses.append({
            "id": row[0],
            "username": row[1],
            "license_key": row[2],
            "expiry_date": expiry_date.strftime("%Y-%m-%d"),
            "days_left": days_left if days_left >= 0 else 0
        })

    return render_template("index.html", licenses=licenses)

@app.route("/add_license", methods=["POST"])
def add_license():
    if "user" not in session:
        return redirect("/")
    username = request.form.get("username", "").strip()
    key = request.form.get("key", "").strip()
    days = request.form.get("days", "").strip()

    if not username or not key:
        flash("Kullanıcı adı ve lisans anahtarı boş olamaz.", "danger")
        return redirect("/panel")

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
    flash("Lisans başarıyla eklendi.", "success")
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
    flash("Lisans silindi.", "warning")
    return redirect("/panel")

@app.route("/logout")
def logout():
    session.clear()
    flash("Başarıyla çıkış yapıldı.", "info")
    return redirect("/")