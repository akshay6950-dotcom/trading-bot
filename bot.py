import hashlib
import hmac
import json
import os
import threading
import time
import traceback
from urllib.parse import urlencode
from flask import Flask
import requests

app = Flask(__name__)

# ==========================================
# ⚙️ THE FINAL DIAGNOSTIC: LIMIT ORDER & STRINGS
# ==========================================
BASE_URL = 'https://api.sharkexchange.in'
ORDER_ENDPOINT_PATH = '/v1/order/place-order' 
MY_RENDER_URL = 'https://trading-bot-4axq.onrender.com'

API_KEY = '0ba307c551a7b66600a0d8a7a5586c20'
SECRET_KEY = '09abb3d1bf0ad3f6fe453474a220acd2'

class FinalRescueBot:
    def generate_signature(self, payload_str: str) -> str:
        return hmac.new(
            SECRET_KEY.encode('utf-8'), 
            payload_str.encode('utf-8'), 
            hashlib.sha256
        ).hexdigest()

    def run(self):
        print('🧪 FINAL DIAGNOSTIC (LIMIT ORDER + STRING FORMAT) STARTED...', flush=True)
        time.sleep(5)
        
        endpoint = f'{BASE_URL}{ORDER_ENDPOINT_PATH}'
        
        # 🧠 FIX 1 & 2: Changed to LIMIT order + Sent numbers as STRINGS ("0.025", "5")
        payload = {
            'timestamp': int(time.time() * 1000),
            'placeType': 'ORDER_FORM',
            'quantity': "0.025",         # String format
            'side': 'BUY',
            'symbol': 'BTC_INR',
            'type': 'LIMIT',             # LIMIT order bypasses empty orderbook crash
            'price': "5000000",          # Safe low price (Trade will NOT execute)
            'reduceOnly': False,          
            'marginAsset': 'INR',
            'deviceType': 'WEB',
            'userCategory': 'EXTERNAL',
            'leverage': "5"              # String format
        }

        try:
            data_to_sign = json.dumps(payload, sort_keys=True, separators=(',', ':'))
            signature = self.generate_signature(data_to_sign)
            
            headers = {
                'Content-Type': 'application/json', 
                'api-key': API_KEY, 
                'signature': signature
            }
            
            print(f'📦 FIRING RESCUE PAYLOAD: {data_to_sign}', flush=True)
            response = requests.post(endpoint, headers=headers, data=data_to_sign, timeout=15)
            print(f'🟢 FINAL ORDER STATUS: {response.status_code} | {response.text}', flush=True)
            
        except Exception:
            print(f'❌ API ERROR DETAILED:', flush=True)
            traceback.print_exc()

def keep_alive_ping():
    while True:
        time.sleep(600) 
        try:
            requests.get(MY_RENDER_URL, timeout=10)
        except Exception:
            pass

@app.route('/')
def home(): 
    return '🧪 Final Rescue Bot is Running! 🚀'

if __name__ == '__main__':
    threading.Thread(target=lambda: FinalRescueBot().run(), daemon=True).start()
    threading.Thread(target=keep_alive_ping, daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
