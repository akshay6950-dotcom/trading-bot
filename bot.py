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
MY_RENDER_URL = 'https://trading-bot-4axq.onrender.com'
API_KEY = '0ba307c551a7b66600a0d8a7a5586c20'
SECRET_KEY = '09abb3d1bf0ad3f6fe453474a220acd2'

class XRayDiagnosticBot:
    def __init__(self):
        pass

    def generate_signature(self, payload_str: str) -> str:
        return hmac.new(
            SECRET_KEY.encode('utf-8'), 
            payload_str.encode('utf-8'), 
            hashlib.sha256
        ).hexdigest()

    def check_account_health(self):
        print("\n" + "="*60, flush=True)
        print("🕵️ DEEP DIAGNOSTIC (X-RAY) STARTED...", flush=True)
        
        # 1. CHECK POSITIONS EXACT RESPONSE
        endpoint_pos = f'{BASE_URL}/v1/positions'
        payload_pos = {'timestamp': int(time.time() * 1000)}
        qs_pos = urlencode(sorted(payload_pos.items()))
        sig_pos = self.generate_signature(qs_pos)
        headers_pos = {'api-key': API_KEY, 'signature': sig_pos}
        
        try:
            resp = requests.get(f"{endpoint_pos}?{qs_pos}", headers=headers_pos, timeout=10)
            print(f"📊 POSITIONS API RESPONSE [{resp.status_code}]: {resp.text}", flush=True)
        except Exception as e:
            print(f"❌ POSITIONS API CRASHED: {e}", flush=True)

        # 2. CHECK OPEN ORDERS (Margin Blockers) EXACT RESPONSE
        endpoint_ord = f'{BASE_URL}/v1/orders'
        payload_ord = {'timestamp': int(time.time() * 1000)}
        qs_ord = urlencode(sorted(payload_ord.items()))
        sig_ord = self.generate_signature(qs_ord)
        headers_ord = {'api-key': API_KEY, 'signature': sig_ord}
        
        try:
            resp_ord = requests.get(f"{endpoint_ord}?{qs_ord}", headers=headers_ord, timeout=10)
            print(f"📋 OPEN ORDERS API RESPONSE [{resp_ord.status_code}]: {resp_ord.text}", flush=True)
        except Exception as e:
            pass

        print("="*60 + "\n", flush=True)

    def run(self):
        while True:
            self.check_account_health()
            time.sleep(30)

def keep_alive_ping():
    while True:
        time.sleep(600) 
        try:
            requests.get(MY_RENDER_URL, timeout=10)
        except Exception:
            pass

@app.route('/')
def home(): 
    return '🕵️ X-Ray Diagnostic Bot is Running! 🚀'

if __name__ == '__main__':
    threading.Thread(target=lambda: XRayDiagnosticBot().run(), daemon=True).start()
    threading.Thread(target=keep_alive_ping, daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
