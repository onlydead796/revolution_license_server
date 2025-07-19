from flask import Flask, request, jsonify
from dotenv import load_dotenv
import os, socket

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('APP_SECRET_KEY')

AUTHORIZED_HWID = os.getenv('AUTHORIZED_HWID')  # Sadece senin cihazın HWID'si
LICENSE_KEY = os.getenv('LICENSE_KEY')          # Gizli lisans anahtarı

@app.route('/api/check_license', methods=['POST'])
def check_license():
    data = request.get_json()
    hwid = data.get('hwid')
    key = data.get('license_key')

    if hwid != AUTHORIZED_HWID or key != LICENSE_KEY:
        return jsonify({'status': 'error', 'message': 'Yetkisiz erişim'}), 403

    return jsonify({'status': 'success', 'message': 'Lisans doğrulandı'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
