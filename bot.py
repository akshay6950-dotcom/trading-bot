import hashlib
import hmac
import json
import os
import threading
import time
from flask import Flask
import requests

app = Flask(__name__)

# ==========================================
# ⚙️ THE FINAL BOT (EXACT UI PAYLOAD MATCH)
# ==========================================
BASE_URL = 'https://api.sharkexchange.in'
ORDER_ENDPOINT_PATH = '/v1/order/place-order' 
MY_RENDER_URL = 'https://trading-bot-4axq.onrender.com'

API_KEY = '0ba307c551a7b66600a0d8a7a5586c20'
SECRET_KEY = '09abb3d1bf0ad3f6fe453474a220acd2'

class FinalBot:
    def generate_signature(self, api_secret, data_to_sign):
        return hmac.new(api_secret.encode('utf-8'), data_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()

    def run(self):
        print('🧪 FINAL UI MATCH BOT INITIATED...', flush=True)
        time.sleep(5)
        
        timestamp = str(int(time.time() * 1000))
        
        # 🧠 THE PERFECT PAYLOAD (Copied exactly from your F12 Network Tab)
        params = {
            'placeType': 'ORDER_FORM',
            'price': 77615.5,             # UI sends a price even for MARKET
            'quantity': 0.002,
            'reduceOnly': False,
            'side': 'BUY',
            'symbol': 'BTCUSDT',          # 🚨 NO UNDERSCORE! This was crashing their engine!
            'type': 'MARKET',
            'timestamp': timestamp        # Required only for API Signature auth
        }

        try:
            # Sort keys to false to maintain the exact dictionary structure if needed,
            # but usually json.dumps does it right. We will use separators to remove spaces.
            data_to_sign = json.dumps(params, separators=(',', ':'))
            signature = self.generate_signature(SECRET_KEY, data_to_sign)
            
            headers = {
                'Content-Type': 'application/json',
                'api-key': API_KEY, 
                'signature': signature
            }
            
            print(f'📦 FIRING EXACT UI PAYLOAD: {data_to_sign}', flush=True)
            response = requests.post(f'{BASE_URL}{ORDER_ENDPOINT_PATH}', headers=headers, data=data_to_sign, timeout=15)
            
            print(f'🟢 FINAL ORDER STATUS: {response.status_code} | {response.text}', flush=True)
            
        except Exception as e:
            print(f'❌ API ERROR: {e}', flush=True)

def keep_alive_ping():
    while True:
        time.sleep(600) 
        try:
            requests.get(MY_RENDER_URL, timeout=10)
        except Exception:
            pass

@app.route('/')
def home(): 
    return '🧪 Final Bot is Running! 🚀'

if __name__ == '__main__':
    threading.Thread(target=lambda: FinalBot().run(), daemon=True).start()
    threading.Thread(target=keep_alive_ping, daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
