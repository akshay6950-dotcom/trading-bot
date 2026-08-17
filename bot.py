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
# ⚙️ FIXED SOP CONFIGURATION (ERROR 3029 BYPASS)
# ==========================================
BASE_URL = 'https://api.sharkexchange.in'
ORDER_ENDPOINT_PATH = '/v1/order/place-order' 
POSITION_ENDPOINT_PATH = '/v1/positions' 

MY_RENDER_URL = 'https://trading-bot-4axq.onrender.com'

# Some versions of Shark Exchange API expect marginAsset or currency fields differently. 
# Let's ensure strict compliance with exchange payload schema.
MARGIN_ASSET = 'INR'          
DEVICE_TYPE = 'WEB'
USER_CATEGORY = 'EXTERNAL'
API_KEY = '0ba307c551a7b66600a0d8a7a5586c20'
SECRET_KEY = '09abb3d1bf0ad3f6fe453474a220acd2'

SYMBOL_EXCHANGE = 'BTC_INR'
LEVERAGE = 5                  
TEST_QUANTITY = 0.01          

class FixedExecutionBot:
    def __init__(self):
        pass

    def generate_signature(self, data_to_sign: str) -> str:
        return hmac.new(
            SECRET_KEY.encode('utf-8'), 
            data_to_sign.encode('utf-8'), 
            hashlib.sha256
        ).hexdigest()

    def place_order(self, side: str, reduce_only: bool = False):
        endpoint = f'{BASE_URL}{ORDER_ENDPOINT_PATH}'
        
        # Clean standardized payload matching exact exchange schema
        payload = {
            'timestamp': int(time.time() * 1000),
            'placeType': 'ORDER_FORM',
            'quantity': TEST_QUANTITY,
            'side': side,
            'symbol': SYMBOL_EXCHANGE,
            'type': 'MARKET',
            'reduceOnly': reduce_only,
            'marginAsset': MARGIN_ASSET,
            'deviceType': DEVICE_TYPE,
            'userCategory': USER_CATEGORY,
            'leverage': LEVERAGE
        }
        try:
            data_to_sign = json.dumps(payload, separators=(',', ':'))
            signature = self.generate_signature(data_to_sign)
            headers = {'Content-Type': 'application/json', 'api-key': API_KEY, 'signature': signature}
            
            print(f'📦 PAYLOAD SENT: {data_to_sign}', flush=True)
            response = requests.post(endpoint, headers=headers, data=data_to_sign, timeout=15)
            print(f'🟢 ORDER STATUS [{side}]: {response.status_code} | {response.text}', flush=True)
            
            if response.status_code == 200:
                return True
            return False
        except Exception:
            print(f'❌ API ERROR DETAILED:', flush=True)
            traceback.print_exc()
            return False

    def get_open_position_details(self):
        endpoint = f'{BASE_URL}{POSITION_ENDPOINT_PATH}'
        payload = {'timestamp': int(time.time() * 1000)}
        try:
            query_string = urlencode(payload)
            signature = self.generate_signature(query_string)
            headers = {'api-key': API_KEY, 'signature': signature}
            response = requests.get(f"{endpoint}?{query_string}", headers=headers, timeout=10)
            
            if response.status_code == 200:
                data_str = response.text
                if data_str.strip() in ["[]", "{}"]:
                    return False, None, 0.0
                try:
                    data = response.json()
                    if isinstance(data, dict):
                        for key in data.values():
                            if isinstance(key, list):
                                data = key
                                break
                    if isinstance(data, list):
                        for pos in data:
                            symbol = str(pos.get('symbol', '')).upper()
                            raw_qty = pos.get('positionQty', pos.get('quantity', pos.get('size', pos.get('positionAmt', 0))))
                            qty = float(raw_qty) if raw_qty else 0.0
                            side = 'LONG' if qty > 0 else 'SHORT'
                            
                            if SYMBOL_EXCHANGE in symbol and abs(qty) > 0:
                                return True, side, abs(qty)
                except Exception:
                    pass
                return False, None, 0.0
            elif response.status_code == 400 and "positionId" in response.text:
                return False, None, 0.0
            return False, None, 0.0
        except Exception:
            return False, None, 0.0

    def run(self):
        print('🧪 FIXED 3029 ERROR TEST BOT STARTED...', flush=True)
        test_step = 0
        while True:
            try:
                is_open, pos_side, active_qty = self.get_open_position_details()
                print(f"🔍 POSITION CHECK | Is Open: {is_open} | Side: {pos_side} | Qty: {active_qty}", flush=True)
                
                if not is_open and test_step == 0:
                    print("🚀 Placing 0.01 Test BUY Order...", flush=True)
                    if self.place_order('BUY'):
                        test_step = 1
                elif is_open and test_step == 1:
                    print("⏳ Test position active. Holding for 15 seconds...", flush=True)
                    time.sleep(15)
                    print("🛑 Closing test position with SELL (ReduceOnly)...", flush=True)
                    if self.place_order('SELL', reduce_only=True):
                        print("✅ TEST COMPLETED SUCCESSFULLY!", flush=True)
                        test_step = 2
                
                time.sleep(30)
            except Exception as e:
                print(f'⚠️ TEST LOOP NOTICE: {e}', flush=True)
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
    return '🧪 Fixed Error 3029 Bot is Running! 🚀'

if __name__ == '__main__':
    threading.Thread(target=lambda: FixedExecutionBot().run(), daemon=True).start()
    threading.Thread(target=keep_alive_ping, daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
