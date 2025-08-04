import os
import random
import string
from datetime import datetime, timedelta
from flask import Flask, render_template_string, request, redirect, url_for, session, flash
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('APP_SECRET_KEY', 'default_secret_key_123456789')

def get_db_connection():
    database_url = os.getenv('DATABASE_URL')
    if database_url:
        return psycopg2.connect(database_url)
    else:
        return psycopg2.connect(
            host="localhost",
            database="licenses_db",
            user="postgres",
            password="password"
        )

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS licenses (
            id SERIAL PRIMARY KEY,
            username VARCHAR(100) NOT NULL,
            license_key VARCHAR(50) UNIQUE NOT NULL,
            expiry_days INTEGER NOT NULL,
            created_at DATE NOT NULL
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
<!doctype html>
<html lang="tr">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Pussly Admin Panel</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://kit.fontawesome.com/a2e1e6d3c2.js" crossorigin="anonymous"></script>
    <style>
        .login-container {
            height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            background-color: #333;
        }
        .login-form {
            width: 100%;
            max-width: 400px;
            padding: 30px;
            background-color: #333;
            border-radius: 10px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.7);
            color: white;
        }
        body.admin {
            background-color: #121212;
            color: #eee;
        }
        .admin .table {
            color: #eee;
        }
        .admin a.btn-danger {
            color: white;
        }
    </style>
</head>
<body class="{% if session.get('logged_in') %}admin{% else %}bg-dark text-light{% endif %}">

{% if session.get('logged_in') %}
<div class="container py-4">

    <h1 class="mb-4 text-center"><i class="fas fa-cogs me-2"></i>Pussly Admin Panel</h1>

    {% with messages = get_flashed_messages(with_categories=true) %}
      {% if messages %}
        {% for category, message in messages %}
          <div class="alert alert-{{ category }} alert-dismissible fade show" role="alert">
            {{ message }}
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="alert" aria-label="Close"></button>
          </div>
        {% endfor %}
      {% endif %}
    {% endwith %}

    <div class="mb-3 d-flex justify-content-between align-items-center">
      <a href="{{ url_for('logout') }}" class="btn btn-danger"><i class="fas fa-sign-out-alt me-1"></i> Çıkış Yap</a>
    </div>

    <form method="POST" action="{{ url_for('create') }}" class="row g-3 mb-4">
      <div class="col-md-4">
        <input type="text" name="username" class="form-control" placeholder="Kullanıcı Adı" required>
      </div>
      <div class="col-md-4">
        <input type="text" name="key" class="form-control" placeholder="Lisans Anahtarı (Boş bırakılırsa otomatik oluşturulur)">
      </div>
      <div class="col-md-2">
        <input type="number" name="expiry" class="form-control" placeholder="Süre (gün)" required min="1" max="3650" value="30">
      </div>
      <div class="col-md-2">
        <button type="submit" class="btn btn-success w-100"><i class="fas fa-plus-circle me-1"></i> Lisansı Kaydet</button>
      </div>
    </form>

    <h3>Mevcut Lisanslar</h3>
    {% if licenses %}
    <table class="table table-striped table-dark table-hover align-middle text-center">
      <thead>
        <tr>
          <th>Kullanıcı Adı</th>
          <th>Lisans Anahtarı</th>
          <th>Süre (gün)</th>
          <th>Oluşturulma Tarihi</th>
          <th>İşlemler</th>
        </tr>
      </thead>
      <tbody>
        {% for lic in licenses %}
          <tr>
            <td>{{ lic['username'] }}</td>
            <td><code>{{ lic['license_key'] }}</code></td>
            <td>{{ lic['expiry_days'] }}</td>
            <td>{{ lic['created_at'] }}</td>
            <td>
              <a href="{{ url_for('delete', key=lic['license_key']) }}" class="btn btn-danger btn-sm" onclick="return confirm('Lisansı silmek istediğinize emin misiniz?');" title="Sil">
                Sil
              </a>
            </td>
          </tr>
        {% endfor %}
      </tbody>
    </table>
    {% else %}
      <p class="text-center">Henüz lisans eklenmemiş.</p>
    {% endif %}

</div>
{% else %}
<div class="login-container">
    <div class="login-form">
        <h1 class="mb-4 text-center"><i class="fas fa-cogs me-2"></i>Pussly Admin Panel</h1>

        {% with messages = get_flashed_messages(with_categories=true) %}
          {% if messages %}
            {% for category, message in messages %}
              <div class="alert alert-{{ category }} alert-dismissible fade show" role="alert">
                {{ message }}
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="alert" aria-label="Close"></button>
              </div>
            {% endfor %}
          {% endif %}
        {% endwith %}

        <form method="POST" action="{{ url_for('login') }}">
            <div class="mb-3">
                <input type="text" name="username" class="form-control" placeholder="Kullanıcı Adı" required autofocus>
            </div>
            <div class="mb-3">
                <input type="password" name="password" class="form-control" placeholder="Şifre" required>
            </div>
            <div class="d-grid gap-2">
                <button type="submit" class="btn btn-primary">Giriş Yap</button>
            </div>
        </form>
    </div>
</div>
{% endif %}

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
'''

@app.route('/', methods=['GET'])
def home():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM licenses")
    licenses = cur.fetchall()
    cur.close()
    conn.close()
    return render_template_string(TEMPLATE, licenses=licenses)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        admin_username = os.getenv('ADMIN_USERNAME', 'admin')
        admin_password = os.getenv('ADMIN_PASSWORD', 'adminpassword')

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
        (username, key, expiry_days, datetime.utcnow().date())
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
        if datetime.utcnow().date() > expiry_date:
            return {"status": "error", "message": "Lisans süresi dolmuş."}, 403
        else:
            return {
                "status": "success",
                "message": "Lisans geçerli.",
                "username": lic['username'],
                "expire_date": expiry_date.strftime("%Y-%m-%d")
            }
    
    return {
        "status": "error",
        "message": "Lisans bulunamadı."
    }, 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)), debug=True)