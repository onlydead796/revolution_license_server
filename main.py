import os
import psycopg2
from flask import Flask, render_template_string, request, redirect, session, flash
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("APP_SECRET", "secret_key")

# Veritabanı bağlantısı
def get_db():
    return psycopg2.connect(
        os.getenv("DATABASE_URL"),
        sslmode="require"
    )

# Giriş sayfası
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if username == os.getenv("ADMIN_USER") and password == os.getenv("ADMIN_PASS"):
            session["user"] = username
            return redirect("/panel")
        else:
            flash("Kullanıcı adı veya şifre yanlış", "danger")
    return render_template_string(open("templates/login.html").read())

# Panel sayfası
@app.route("/panel")
def panel():
    if "user" not in session:
        return redirect("/")
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM licenses ORDER BY id DESC")
    licenses = cur.fetchall()
    conn.close()
    return render_template_string(open("templates/index.html").read(), licenses=licenses)

# Lisans ekle
@app.route("/add_license", methods=["POST"])
def add_license():
    if "user" not in session:
        return redirect("/")
    try:
        license_key = request.form["license_key"]
        max_games = int(request.form["max_games"])
        expiry_days = int(request.form["expiry_days"])
        start_date = datetime.now()
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO licenses (license_key, max_games, start_date, expiry_days)
            VALUES (%s, %s, %s, %s)
        """, (license_key, max_games, start_date, expiry_days))
        conn.commit()
        conn.close()
        flash("✅ Lisans başarıyla eklendi", "success")
    except Exception as e:
        flash(f"Hata: {e}", "danger")
    return redirect("/panel")

# Lisans sil
@app.route("/delete_license/<int:id>", methods=["POST"])
def delete_license(id):
    if "user" not in session:
        return redirect("/")
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM licenses WHERE id = %s", (id,))
    conn.commit()
    conn.close()
    flash("🗑️ Lisans silindi", "success")
    return redirect("/panel")

# Lisans süresi uzatma (bitiş gününü arttırır)
@app.route("/extend_license/<int:id>", methods=["POST"])
def extend_license(id):
    if "user" not in session:
        return redirect("/")

    try:
        extra_days = int(request.form.get("extra_days", "0"))
        if extra_days < 1:
            flash("⚠️ En az 1 gün eklenmelidir.", "danger")
            return redirect("/panel")

        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT expiry_days FROM licenses WHERE id = %s", (id,))
        result = cur.fetchone()

        if not result:
            flash("❌ Lisans bulunamadı.", "danger")
            return redirect("/panel")

        current_days = result[0]
        new_days = current_days + extra_days

        cur.execute("UPDATE licenses SET expiry_days = %s WHERE id = %s", (new_days, id))
        conn.commit()
        conn.close()

        flash(f"✅ Lisans süresi {extra_days} gün uzatıldı.", "success")
        return redirect("/panel")
    except Exception as e:
        flash(f"❌ Hata: {str(e)}", "danger")
        return redirect("/panel")

# Oturumu kapat
@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect("/")

# Sunucu başlat
if __name__ == "__main__":
    app.run(debug=True)