import os
import json  # json modülünü buraya ekledim
from flask import Flask, render_template_string, request, redirect, url_for, session, flash
from dotenv import load_dotenv

# .env dosyasını yükle
load_dotenv()

# Flask uygulaması
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
    <style>
        .login-container {
            height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        .login-form {
            width: 100%;
            max-width: 400px;
            padding: 30px;
            background-color: #333;
            border-radius: 10px;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3);
        }
    </style>
</head>
<body class="bg-dark text-light">

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
{% else %}
    <div class="container login-container">
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
                    <input type="text" name="username" class="form-control" placeholder="Kullanıcı Adı" required>
                </div>
                <div class="mb-3">
                    <input type="password" name="password" class="form-control" placeholder="Şifre" required>
                </div>
                <div class="d-grid gap-2">
                    <button type="submit" class="btn btn-success">Giriş Yap</button>
                </div>
            </form>
        </div>
    </div>
{% endif %}

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
'''

@app.route('/', methods=['GET', 'POST'])
def home():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    with open(LICENSE_FILE) as f:
        licenses = json.load(f)
    return render_template_string(TEMPLATE, licenses=licenses)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # .env dosyasından admin kullanıcı adı ve şifreyi al
        admin_username = os.getenv('ADMIN_USERNAME', 'admin')
        admin_password = os.getenv('ADMIN_PASSWORD', 'adminpassword')

        # Kullanıcı adı ve şifreyi kontrol et
        if username == admin_username and password == admin_password:
            session['logged_in'] = True
            flash("Giriş başarılı!", "success")
            return redirect(url_for('home'))
        else:
            flash("Kullanıcı adı veya şifre hatalı!", "danger")
    
    return render_template_string(TEMPLATE)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash("Başarıyla çıkış yapıldı.", "info")
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
