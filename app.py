import os
from flask import Flask, render_template_string, request, redirect, url_for, session, jsonify
import json, random, string
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = os.getenv('APP_SECRET_KEY', 'default_secret_key_123456789')

LICENSE_FILE = "licenses.json"


ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "test")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "tester123")

if not os.path.exists(LICENSE_FILE):
    with open(LICENSE_FILE, 'w') as f:
        json.dump([], f)

def generate_license_key(length=16):
    chars = string.ascii_uppercase + string.digits
    return '-'.join(''.join(random.choice(chars) for _ in range(4)) for _ in range(length // 4))

TEMPLATE = '''
<!doctype html>
<title>Pussly Admin Panel</title>
<h2>Admin Panel - Lisans Yönetimi</h2>
{% if session.get('logged_in') %}
  <p><a href="{{ url_for('logout') }}">Çıkış Yap</a></p>
  <form method="POST" action="/create">
    <input name="username" placeholder="Kullanıcı Adı" required>
    <input name="key" placeholder="Lisans Anahtarı (Boş bırakılırsa otomatik oluşturulur)">
    <input name="expiry" placeholder="Süre (gün, örn: 30)" required>
    <button type="submit">Lisans Oluştur</button>
  </form>
  <h3>Mevcut Lisanslar</h3>
  <ul>
    {% for lic in licenses %}
      <li>{{ lic['username'] }} | {{ lic['key'] }} | {{ lic['expiry'] }} gün
      <a href="/delete/{{ lic['key'] }}">[Sil]</a></li>
    {% endfor %}
  </ul>
{% else %}
  <form method="POST">
    <input name="username" placeholder="Kullanıcı Adı" required>
    <input name="password" placeholder="Şifre" required>
    <button type="submit">Giriş Yap</button>
  </form>
  {% if error %}<p style="color:red">{{ error }}</p>{% endif %}
{% endif %}
'''

@app.route('/', methods=['GET', 'POST'])
def home():
    error = None
    if request.method == 'POST':
        if request.form['username'] == ADMIN_USERNAME and request.form['password'] == ADMIN_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('home'))
        else:
            error = 'Hatalı kullanıcı adı veya şifre'
    with open(LICENSE_FILE) as f:
        licenses = json.load(f)
    return render_template_string(TEMPLATE, licenses=licenses, error=error)

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
    return redirect(url_for('home'))

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('home'))

@app.route('/api/check_license', methods=['POST'])
def check_license_api():
    data = request.get_json()
    username = data.get("username")
    key = data.get("key")

    with open(LICENSE_FILE) as f:
        licenses = json.load(f)

    for lic in licenses:
        if lic["username"] == username and lic["key"] == key:
            created_at_str = lic.get("created_at")
            expiry_days = lic.get("expiry", 0)
            if created_at_str and expiry_days:
                created_at = datetime.strptime(created_at_str, "%Y-%m-%d")
                expire_date = created_at + timedelta(days=expiry_days)
                if datetime.utcnow() > expire_date:
                    return jsonify({"success": False, "message": "Lisans süresi dolmuş."}), 401
            return jsonify({"success": True, "message": "Lisans geçerli.", "expires": expire_date.strftime("%Y-%m-%d")})

    return jsonify({"success": False, "message": "Lisans bulunamadı veya bilgileri yanlış."}), 401

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
