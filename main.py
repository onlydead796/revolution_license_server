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
            created_at TIMESTAMP NOT NULL,
            is_active BOOLEAN DEFAULT TRUE
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
        SELECT id, username, license_key, expiry_days, created_at
        FROM licenses
        WHERE is_active = TRUE
        ORDER BY created_at ASC
    """)
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
            "key": row[2],
            "expiry_date": expiry_date.strftime("%Y-%m-%d 23:59:59"),  # Gün sonu olarak ayarlandı
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

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO licenses (username, license_key, expiry_days, created_at) VALUES (%s, %s, %s, %s)",
        (username, key, days, datetime.utcnow())
    )
    conn.commit()
    conn.close()
    flash(f"✅ Lisans başarıyla eklendi: {key}", "success")
    return redirect("/panel")

@app.route("/renew_license/<int:id>", methods=["POST"])
def renew_license(id):
    if "user" not in session:
        return redirect("/")
    days = request.form.get("days", "").strip()
    try:
        days = int(days)
        if days < 1:
            flash("⚠️ Gün sayısı 1'den küçük olamaz.", "danger")
            return redirect("/panel")
    except:
        flash("⚠️ Geçersiz gün sayısı.", "danger")
        return redirect("/panel")

    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE licenses SET expiry_days = expiry_days + %s WHERE id = %s AND is_active = TRUE", (days, id))
    conn.commit()
    conn.close()
    flash(f"✅ Lisans {days} gün yenilendi.", "success")
    return redirect("/panel")

@app.route("/deactivate_license/<int:id>", methods=["POST"])
def deactivate_license(id):
    if "user" not in session:
        return redirect("/")
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE licenses SET is_active = FALSE WHERE id = %s", (id,))
    conn.commit()
    conn.close()
    flash("⚠️ Lisans pasif yapıldı.", "warning")
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