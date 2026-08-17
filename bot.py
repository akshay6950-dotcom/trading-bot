import hashlib
import hmac
import json
import os
import threading
import time
from urllib.parse import urlencode
from flask import Flask
import requests

app = Flask(__name__)

BASE_URL = 'https://api.sharkexchange.in'
API_KEY = '0ba307c551a7b66600a0d8a7a5586c20'
SECRET_KEY = '09abb3d1bf0ad3f6fe453474a220acd2'
MY_RENDER_URL = 'https://trading-bot-4axq.onrender.com'

class DiagnosticsBot:
    def generate_signature(self, data_to_sign: str) -> str:
        return hmac.new(
            SECRET_KEY.encode('utf-8'), 
            data_to_sign.encode('utf-8'), 
            hashlib.sha256
        ).hexdigest()

    def check_account_and_markets(self):
        # 1. Check Account Info / Balance endpoint
        endpoint = f'{BASE_URL}/v1/account' # or wallet/balance endpoint
        payload = {'timestamp': int(time.time() * 1000)}
        try:
            query_string = urlencode(payload)
            signature = self.generate_signature(query_string)
            headers = {'api-key': API_KEY, 'signature': signature}
            response = requests.get(f"{endpoint}?{query_string}", headers=headers, timeout=10)
            print(f"🔍 ACCOUNT INFO STATUS: {response.status_code} | {response.text}", flush=True)
        except Exception as e:
            print(f"⚠️ Account check error: {e}", flush=True)

        # 2. Check Exchange Symbols info
        try:
            sym_resp = requests.get(f"{BASE_URL}/v1/market/symbols", timeout=10)
            print(f"🔍 SYMBOLS API STATUS: {sym_resp.status_code} | {sym_resp.text[:300]}...", flush=True)
        except Exception as e:
            print(f"⚠️ Symbols check error: {e}", flush=True)

    def run(self):
        print('🛠️ DIAGNOSTICS BOT STARTED...', flush=True)
        while True:
            self.check_account_and_markets()
            time.sleep(60)

def keep_alive_ping():
    while True:
        time.sleep(600) 
        try:
            requests.get(MY_RENDER_URL, timeout=10)
        except Exception:
            pass

@app.route('/')
def home(): 
    return '🛠️ Diagnostics Bot is Running! 🚀'

if __name__ == '__main__':
    threading.Thread(target=lambda: DiagnosticsBot().run(), daemon=True).start()
    threading.Thread(target=keep_alive_ping, daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
