import os
import random
import string
from datetime import datetime, timedelta
from flask import Flask, render_template_string, request, redirect, url_for, session, flash
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('APP_SECRET_KEY', 'default_secret_key_123456789')

# MongoDB bağlantısı
MONGO_URI = os.getenv('MONGO_URI')
client = MongoClient(MONGO_URI)
db = client.get_default_database()  # Eğer URI'da db belirtilmediyse, db adını buraya yazabilirsin
licenses_col = db.licenses  # Koleksiyon adı

def generate_license_key(length=16):
    chars = string.ascii_uppercase + string.digits
    return '-'.join(''.join(random.choice(chars) for _ in range(4)) for _ in range(length // 4))

# TEMPLATE aynen kalacak, değiştirmeye gerek yok

# Ana sayfa - Lisansları MongoDB'den çek
@app.route('/', methods=['GET'])
def home():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    licenses = list(licenses_col.find({}, {'_id': 0}))  # _id gizledik
    return render_template_string(TEMPLATE, licenses=licenses)

# Login kısmı değişmedi

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

# Lisans oluşturma MongoDB'ye ekle
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

    new_lic = {
        "username": username,
        "key": key,
        "expiry": expiry_days,
        "created_at": datetime.utcnow().strftime("%Y-%m-%d")
    }

    licenses_col.insert_one(new_lic)

    flash(f"Lisans başarıyla oluşturuldu: {key}", "success")
    return redirect(url_for('home'))

# Lisans silme MongoDB'den sil
@app.route('/delete/<key>')
def delete(key):
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    result = licenses_col.delete_one({"key": key})

    if result.deleted_count:
        flash("Lisans başarıyla silindi.", "warning")
    else:
        flash("Lisans bulunamadı.", "danger")

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

    lic = licenses_col.find_one({"key": license_key})
    if lic:
        created = datetime.strptime(lic['created_at'], "%Y-%m-%d")
        expiry_days = lic['expiry']
        expiry_date = created + timedelta(days=expiry_days)
        if datetime.utcnow() > expiry_date:
            return {"status": "error", "message": "Lisans süresi dolmuş."}, 403
        else:
            return {"status": "success", "message": "Lisans geçerli.", "username": lic['username']}

    return {"status": "error", "message": "Lisans bulunamadı."}, 404


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)), debug=True)
