import os
import random
import string
from datetime import datetime, timedelta
from flask import Flask, render_template_string, request, redirect, url_for, session, flash
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('APP_SECRET_KEY', 'default_secret_key_123456789')

def get_db_connection():
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise Exception("DATABASE_URL environment variable is not set!")
    return psycopg2.connect(database_url)

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS licenses (
            id SERIAL PRIMARY KEY,
            username VARCHAR(100) NOT NULL,
            license_key VARCHAR(50) UNIQUE NOT NULL,
            expiry_days INTEGER NOT NULL,
            created_at TIMESTAMP NOT NULL
        )
    ''')
    conn.commit()
    cur.close()
    conn.close()

init_db()

def generate_license_key(length=16):
    chars = string.ascii_uppercase + string.digits
    return '-'.join(''.join(random.choice(chars) for _ in range(4)) for _ in range(length // 4))

TEMPLATE = '''
<!-- Senin mevcut admin panel HTML şablonun burada olacak -->
'''

@app.route('/', methods=['GET'])
def home():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM licenses ORDER BY created_at DESC")
    licenses = cur.fetchall()
    cur.close()
    conn.close()
    return render_template_string(TEMPLATE, licenses=licenses)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        admin_username = os.getenv('ADMIN_USERNAME')
        admin_password = os.getenv('ADMIN_PASSWORD')

        if not admin_username or not admin_password:
            flash("Admin kullanıcı adı veya şifresi ortam değişkenlerinde ayarlı değil.", "danger")
            return redirect(url_for('login'))

        if username == admin_username and password == admin_password:
            session['logged_in'] = True
            flash("Giriş başarılı!", "success")
            return redirect(url_for('home'))
        else:
            flash("Kullanıcı adı veya şifre hatalı!", "danger")

    return render_template_string(TEMPLATE)

@app.route('/create', methods=['POST'])
def create():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    username = request.form['username']
    key = request.form.get('key', '').strip()
    expiry_days = request.form.get('expiry', '').strip()

    if not key:
        key = generate_license_key()

    try:
        expiry_days = int(expiry_days)
        if expiry_days <= 0:
            expiry_days = 30
    except:
        expiry_days = 30

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO licenses (username, license_key, expiry_days, created_at) VALUES (%s, %s, %s, %s)",
        (username, key, expiry_days, datetime.utcnow())
    )
    conn.commit()
    cur.close()
    conn.close()

    flash(f"Lisans başarıyla oluşturuldu: {key}", "success")
    return redirect(url_for('home'))

@app.route('/delete/<key>')
def delete(key):
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM licenses WHERE license_key = %s", (key,))
    conn.commit()
    cur.close()
    conn.close()

    flash("Lisans başarıyla silindi.", "warning")
    return redirect(url_for('home'))

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash("Başarıyla çıkış yapıldı.", "info")
    return redirect(url_for('login'))

@app.route('/api/check_license', methods=['POST'])
def check_license():
    data = request.get_json()
    if not data or 'license_key' not in data:
        return {"status": "error", "message": "Lisans anahtarı gönderilmedi."}, 400

    license_key = data['license_key'].strip().upper()

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM licenses WHERE license_key = %s", (license_key,))
    lic = cur.fetchone()
    cur.close()
    conn.close()

    if lic:
        created = lic['created_at']
        expiry_days = lic['expiry_days']
        expiry_date = created + timedelta(days=expiry_days)
        if datetime.utcnow() > expiry_date:
            return {"status": "error", "message": "Lisans süresi dolmuş."}, 403
        else:
            return {
                "status": "success",
                "message": "Lisans geçerli.",
                "username": lic['username'],
                "expire_date": expiry_date.strftime("%Y-%m-%d")
            }

    return {"status": "error", "message": "Lisans bulunamadı."}, 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)), debug=True)
