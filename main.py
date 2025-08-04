import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, flash
from dotenv import load_dotenv
import random
import string

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("APP_SECRET")

DB_URL = os.getenv("DATABASE_URL")

def get_db():
    conn = psycopg2.connect(DB_URL, cursor_factory=RealDictCursor)
    return conn

def generate_license_key(length=24):
    chars = string.ascii_uppercase + string.digits
    return '-'.join(''.join(random.choice(chars) for _ in range(4)) for _ in range(6))

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username == "admin" and password == "123":
            session["logged_in"] = True
            return redirect(url_for("panel"))
        else:
            flash("Kullanıcı adı veya şifre hatalı", "danger")
    return render_template("index.html")

@app.route("/panel")
def panel():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM licenses ORDER BY id DESC")
    licenses = cur.fetchall()
    cur.close()
    conn.close()

    now = datetime.now()
    for license in licenses:
        created = license['created_at']
        expiry = created + timedelta(days=license['expiry_days'])
        remaining = expiry - now
        license["expires_at"] = expiry.strftime("%Y-%m-%d %H:%M:%S")
        license["remaining_seconds"] = int(remaining.total_seconds())
    
    return render_template("panel.html", licenses=licenses)

@app.route("/add_license", methods=["POST"])
def add_license():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    
    username = request.form.get("username")
    key = request.form.get("key")
    days = int(request.form.get("days") or 30)

    if not key:
        key = generate_license_key()

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO licenses (username, license_key, expiry_days, created_at)
        VALUES (%s, %s, %s, NOW())
    """, (username, key, days))
    conn.commit()
    cur.close()
    conn.close()

    flash("Lisans başarıyla eklendi", "success")
    return redirect(url_for("panel"))

@app.route("/delete_license/<int:id>")
def delete_license(id):
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM licenses WHERE id = %s", (id,))
    conn.commit()
    cur.close()
    conn.close()

    flash("Lisans silindi", "info")
    return redirect(url_for("panel"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)