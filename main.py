import os
from flask import Flask, render_template_string, request, redirect, url_for, session, flash
import json, random, string
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = os.getenv('APP_SECRET_KEY', 'default_secret_key_123456789')

LICENSE_FILE = "licenses.json"

if not os.path.exists(LICENSE_FILE):
    with open(LICENSE_FILE, 'w') as f:
        json.dump([], f)

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
</head>
<body class="bg-dark text-light">
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
            <td><code>{{ lic['key'] }}</code></td>
            <td>{{ lic['expiry'] }}</td>
            <td>{{ lic['created_at'] }}</td>
            <td>
              <a href="{{ url_for('delete', key=lic['key']) }}" class="btn btn-danger btn-sm" onclick="return confirm('Lisansı silmek istediğinize emin misiniz?');" title="Sil">
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

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
'''

@app.route('/', methods=['GET', 'POST'])
def home():
    session['logged_in'] = True
    with open(LICENSE_FILE) as f:
        licenses = json.load(f)
    return render_template_string(TEMPLATE, licenses=licenses)

@app.route('/create', methods=['POST'])
def create():
    if not session.get('logged_in'):
        return redirect(url_for('home'))

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

    new_lic = {
        "username": username,
        "key": key,
        "expiry": expiry_days,
        "created_at": datetime.utcnow().strftime("%Y-%m-%d")
    }

    with open(LICENSE_FILE) as f:
        licenses = json.load(f)
    licenses.append(new_lic)
    with open(LICENSE_FILE, 'w') as f:
        json.dump(licenses, f, indent=2)
    flash(f"Lisans başarıyla oluşturuldu: {key}", "success")
    return redirect(url_for('home'))

@app.route('/delete/<key>')
def delete(key):
    if not session.get('logged_in'):
        return redirect(url_for('home'))
    with open(LICENSE_FILE) as f:
        licenses = json.load(f)
    licenses = [lic for lic in licenses if lic['key'] != key]
    with open(LICENSE_FILE, 'w') as f:
        json.dump(licenses, f, indent=2)
    flash("Lisans başarıyla silindi.", "warning")
    return redirect(url_for('home'))

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash("Başarıyla çıkış yapıldı.", "info")
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
