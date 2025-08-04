import os
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

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if username == ADMIN_USER and password == ADMIN_PASS:
            session["user"] = username
            return redirect("/panel")
        flash("Hatalı kullanıcı adı veya şifre", "danger")
    return render_template("login.html")

@app.route("/panel")
def panel():
    if "user" not in session:
        return redirect("/")
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, key, expire_date FROM licenses ORDER BY expire_date ASC")
    rows = cur.fetchall()
    conn.close()

    licenses = []
    for row in rows:
        days_left = (row[3] - datetime.today().date()).days
        licenses.append({
            "id": row[0],
            "key": row[2],
            "expire_date": row[3].strftime("%Y-%m-%d"),
            "days_left": days_left
        })

    return render_template("index.html", licenses=licenses)

@app.route("/add_license", methods=["POST"])
def add_license():
    if "user" not in session:
        return redirect("/")
    key = request.form["key"]
    days = request.form["days"]
    try:
        days = int(days)
        if days < 1:
            days = 30
    except:
        days = 30
    expire_date = datetime.today().date() + timedelta(days=days)

    conn = get_db()
    cur = conn.cursor()
    cur.execute("INSERT INTO licenses (key, expire_date) VALUES (%s, %s, %s)", (key, expire_date))
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