import hashlib
import hmac
import json
import os
import threading
import time
import traceback
from urllib.parse import urlencode
from flask import Flask
import pandas as pd
import pandas_ta as ta
import requests
import yfinance as yf

app = Flask(__name__)

# CONFIG
BASE_URL = 'https://api.sharkexchange.in'
MARGIN_ASSET = 'INR'
DEVICE_TYPE = 'WEB'
USER_CATEGORY = 'EXTERNAL'
API_KEY = '0ba307c551a7b66600a0d8a7a5586c20'
SECRET_KEY = '09abb3d1bf0ad3f6fe453474a220acd2'

SYMBOL_YAHOO = 'BTC-USD'
SYMBOL_EXCHANGE = 'BTC_INR'
BTC_QUANTITY = 0.050
LEVERAGE = 5
TRAILING_DISTANCE = 0.008

class SharkLiveBTCBot:
    def __init__(self):
        self.position = 0 
        self.entry_price = 0.0
        self.current_sl = 0.0
        self.current_tp = 0.0
        self.extreme_price = 0.0

    def generate_signature(self, params: dict) -> str:
        sorted_params = sorted(params.items())
        query_string = urlencode(sorted_params)
        return hmac.new(SECRET_KEY.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()

    def get_headers(self, params: dict) -> dict:
        return {
            'Content-Type': 'application/json', 
            'deviceType': DEVICE_TYPE, 
            'userCategory': USER_CATEGORY, 
            'X-API-KEY': API_KEY, 
            'X-SIGNATURE': self.generate_signature(params)
        }

    def place_order(self, side: str):
        endpoint = f'{BASE_URL}/api/v1/order'
        payload = {
            'symbol': SYMBOL_EXCHANGE, 
            'side': side, 
            'type': 'MARKET', 
            'quantity': BTC_QUANTITY, 
            'leverage': LEVERAGE, 
            'marginAsset': MARGIN_ASSET, 
            'timestamp': int(time.time() * 1000)
        }
        try:
            response = requests.post(endpoint, headers=self.get_headers(payload), data=json.dumps(payload), timeout=15)
            print(f'🟢 ORDER STATUS [{side}]: {response.status_code} | {response.text}', flush=True)
            return True
        except Exception:
            print(f'❌ API ERROR DETAILED:', flush=True)
            traceback.print_exc()
            return False

    def fetch_data(self):
        df = yf.download(SYMBOL_YAHOO, period='5d', interval='1h', progress=False)
        if isinstance(df.columns, pd.MultiIndex): 
            df.columns = [col[0] for col in df.columns]
        
        df.ta.ema(length=21, append=True)
        df.ta.ema(length=50, append=True)
        df.ta.rsi(length=14, append=True)
        df.ta.adx(length=14, append=True)
        df.dropna(inplace=True)
        df.columns = [c.upper() for c in df.columns]
        return df

    def get_adaptive_signals(self):
        df = self.fetch_data()
        row = df.iloc[-1]
        
        # FIXED: Changed 'RSI' to 'RSI_14'
        price, adx_val, rsi_val = row['CLOSE'], row['ADX_14'], row['RSI_14']
        
        e21 = row[[c for c in df.columns if 'EMA_21' in c][0]]
        e50 = row[[c for c in df.columns if 'EMA_50' in c][0]]
        
        mode = 'TREND' if adx_val > 25 else 'SIDEWAYS'
        is_long = (e21 > e50) and (price <= e21) if mode == 'TREND' else (rsi_val < 35)
        is_short = (e21 < e50) and (price >= e21) if mode == 'TREND' else (rsi_val > 65)
        
        return is_long, is_short, price, mode, rsi_val

    def run(self):
        print('🚀 BOT STARTED | MONITORING BTC_INR...', flush=True)
        while True:
            try:
                is_long, is_short, price, mode, rsi = self.get_adaptive_signals()
                print(f'📡 SCANNING | Price: {price:.2f} | RSI: {rsi:.2f} | Mode: {mode} | Pos: {self.position}', flush=True)
                
                # Logic block
                if self.position == 0:
                    if is_long:
                        print("📈 SIGNAL: BUY", flush=True)
                        if self.place_order('BUY'): 
                            self.position = 1
                    elif is_short:
                        print("📉 SIGNAL: SELL", flush=True)
                        if self.place_order('SELL'): 
                            self.position = -1
                
                time.sleep(60)
            except Exception:
                print(f'⚠️ CRITICAL LOOP ERROR DETAILED:', flush=True)
                traceback.print_exc()
                time.sleep(30)

@app.route('/')
def home(): 
    return 'Bot is running live!'

if __name__ == '__main__':
    threading.Thread(target=lambda: SharkLiveBTCBot().run(), daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
