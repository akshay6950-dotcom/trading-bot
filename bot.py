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
# ⚙️ QUICK TEST: 0.01 BTC | MARKET ORDER | 5x LEVERAGE
# ==========================================
BASE_URL = 'https://api.sharkexchange.in'
ORDER_ENDPOINT_PATH = '/v1/order/place-order' 
MY_RENDER_URL = 'https://trading-bot-4axq.onrender.com'

API_KEY = '0ba307c551a7b66600a0d8a7a5586c20'
SECRET_KEY = '09abb3d1bf0ad3f6fe453474a220acd2'

class MarketTestBot:
    def generate_signature(self, payload_str: str) -> str:
        return hmac.new(
            SECRET_KEY.encode('utf-8'), 
            payload_str.encode('utf-8'), 
            hashlib.sha256
        ).hexdigest()

    def run(self):
        print('🧪 QUICK MARKET TEST (0.01 BTC, 5x) STARTED...', flush=True)
        time.sleep(5)
        
        endpoint = f'{BASE_URL}{ORDER_ENDPOINT_PATH}'
        
        # 🧠 THE PAYLOAD: EXACTLY AS REQUESTED
        payload = {
            'timestamp': int(time.time() * 1000),
            'placeType': 'ORDER_FORM',
            'quantity': 0.01,            # Choti testing quantity
            'side': 'BUY',
            'symbol': 'BTC_INR',
            'type': 'MARKET',            # Direct market execution
            'reduceOnly': False,
            'marginAsset': 'INR',
            'deviceType': 'WEB',
            'userCategory': 'EXTERNAL',
            'leverage': 5                # 5x Margin
        }

        try:
            # Converting to pure JSON string without extra spaces
            data_to_sign = json.dumps(payload, separators=(',', ':'))
            signature = self.generate_signature(data_to_sign)
            
            headers = {
                'Content-Type': 'application/json', 
                'api-key': API_KEY, 
                'signature': signature
            }
            
            print(f'📦 FIRING PAYLOAD: {data_to_sign}', flush=True)
            response = requests.post(endpoint, headers=headers, data=data_to_sign, timeout=15)
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
    return '🧪 Market Test Bot is Running! 🚀'

if __name__ == '__main__':
    threading.Thread(target=lambda: MarketTestBot().run(), daemon=True).start()
    threading.Thread(target=keep_alive_ping, daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
