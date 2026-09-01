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
# ⚙️ THE FINAL BOT (CRASH BYPASSED)
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
        print('🧪 FINAL BOT INITIATED (No orderType)...', flush=True)
        time.sleep(5)
        
        timestamp = str(int(time.time() * 1000))
        
        # 🧠 THE PERFECT PAYLOAD
        params = {
            'timestamp': timestamp,         
            'placeType': 'ORDER_FORM',
            'quantity': 0.002,
            'side': 'BUY',
            'symbol': 'BTC_INR',
            'type': 'MARKET',               # Kept this one
            # 'orderType': 'MARKET'         <-- HATA DIYA (Server was rejecting this)
            'reduceOnly': False,
            'marginAsset': 'INR',
            'deviceType': 'WEB',
            'userCategory': 'EXTERNAL',
            'price': 5000000                
        }

        try:
            data_to_sign = json.dumps(params, separators=(',', ':'))
            signature = self.generate_signature(SECRET_KEY, data_to_sign)
            
            headers = {
                'Content-Type': 'application/json',
                'api-key': API_KEY, 
                'signature': signature
            }
            
            print(f'📦 FIRING FINAL PAYLOAD: {data_to_sign}', flush=True)
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
