import hashlib
import hmac
import json
import os
import threading
import time
import traceback
from flask import Flask
import pandas as pd
import pandas_ta as ta
import requests
import yfinance as yf

app = Flask(__name__)

# ==========================================
# CONFIGURATION
# ==========================================
BASE_URL = 'https://api.sharkexchange.in'

# SHARK EXCHANGE OFFICIAL ENDPOINT (From Screenshot)
ORDER_ENDPOINT_PATH = '/api/v1/order/place-order' 

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

    def generate_signature(self, data_to_sign: str) -> str:
        # Docs ke hisaab se JSON string ko hash karna hai
        return hmac.new(
            SECRET_KEY.encode('utf-8'), 
            data_to_sign.encode('utf-8'), 
            hashlib.sha256
        ).hexdigest()

    def place_order(self, side: str):
        endpoint = f'{BASE_URL}{ORDER_ENDPOINT_PATH}'
        
        # Payload ekdam official docs ke table ke hisaab se
        payload = {
            'timestamp': int(time.time() * 1000),
            'placeType': 'ORDER_FORM',
            'quantity': BTC_QUANTITY,
            'side': side,
            'symbol': SYMBOL_EXCHANGE,
            'type': 'MARKET',
            'orderType': 'MARKET',
            'reduceOnly': False,
            'marginAsset': MARGIN_ASSET,
            'deviceType': DEVICE_TYPE,
            'userCategory': USER_CATEGORY,
            'leverage': LEVERAGE
        }
        
        try:
            # Docs ke right-side python snippet ke hisaab se string banana
            data_to_sign = json.dumps(payload, separators=(',', ':'))
            signature = self.generate_signature(data_to_sign)
            
            # Naye official headers
            headers = {
                'Content-Type': 'application/json', 
                'api-key': API_KEY, 
                'signature': signature
            }
            
            # Send exactly the signed JSON string
            response = requests.post(endpoint, headers=headers, data=data_to_sign, timeout=15)
            print(f'🟢 ORDER STATUS [{side}]: {response.status_code} | {response.text}', flush=True)
            
            if response.status_code == 200:
                return True
            return False
        except Exception:
            print(f'❌ API ERROR DETAILED:', flush=True)
            traceback.print_exc()
            return False

    def fetch_data(self):
        df = yf.download(SYMBOL_YAHOO, period='5d', interval='1h', progress=False)
        
        if df.empty:
            raise ValueError("Yahoo Finance se data nahi mila, agle minute retry karega.")
            
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
        
        if df.empty:
             raise ValueError("Dataframe khali hai indicators ke baad.")
             
        row = df.iloc[-1]
        
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
            except Exception as e:
                print(f'⚠️ TEMPORARY LOOP ERROR: {e}', flush=True)
                time.sleep(30)

@app.route('/')
def home(): 
    return 'Bot is running live!'

if __name__ == '__main__':
    threading.Thread(target=lambda: SharkLiveBTCBot().run(), daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
