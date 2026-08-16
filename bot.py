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

# ==========================================
# CONFIGURATION & SETTINGS
# ==========================================
BASE_URL = 'https://api.sharkexchange.in'

ORDER_ENDPOINT_PATH = '/v1/order/place-order' 
POSITION_ENDPOINT_PATH = '/v1/positions' 

MY_RENDER_URL = 'https://trading-bot-4axq.onrender.com'

MARGIN_ASSET = 'INR'
DEVICE_TYPE = 'WEB'
USER_CATEGORY = 'EXTERNAL'
API_KEY = '0ba307c551a7b66600a0d8a7a5586c20'
SECRET_KEY = '09abb3d1bf0ad3f6fe453474a220acd2'

SYMBOL_YAHOO = 'BTC-USD'
SYMBOL_EXCHANGE = 'BTC_INR'

BTC_QUANTITY = 0.025  
LEVERAGE = 5

class SharkLiveBTCBot:
    def __init__(self):
        pass

    def generate_signature(self, data_to_sign: str) -> str:
        return hmac.new(
            SECRET_KEY.encode('utf-8'), 
            data_to_sign.encode('utf-8'), 
            hashlib.sha256
        ).hexdigest()

    def place_order(self, side: str):
        endpoint = f'{BASE_URL}{ORDER_ENDPOINT_PATH}'
        
        payload = {
            'timestamp': int(time.time() * 1000),
            'placeType': 'ORDER_FORM',
            'quantity': BTC_QUANTITY,
            'side': side,
            'symbol': SYMBOL_EXCHANGE,
            'type': 'MARKET',
            'reduceOnly': False,
            'marginAsset': MARGIN_ASSET,
            'deviceType': DEVICE_TYPE,
            'userCategory': USER_CATEGORY,
            'leverage': LEVERAGE
        }
        
        try:
            data_to_sign = json.dumps(payload, separators=(',', ':'))
            signature = self.generate_signature(data_to_sign)
            
            headers = {
                'Content-Type': 'application/json', 
                'api-key': API_KEY, 
                'signature': signature
            }
            
            response = requests.post(endpoint, headers=headers, data=data_to_sign, timeout=15)
            print(f'🟢 ORDER STATUS [{side}]: {response.status_code} | {response.text}', flush=True)
            
            if response.status_code == 200:
                return True
            return False
        except Exception:
            print(f'❌ API ERROR DETAILED:', flush=True)
            traceback.print_exc()
            return False

    def is_trade_active_on_exchange(self):
        """Ab yeh function sirf naam nahi, balki quantity > 0 check karega!"""
        endpoint = f'{BASE_URL}{POSITION_ENDPOINT_PATH}'
        payload = {'timestamp': int(time.time() * 1000)}
        
        try:
            query_string = urlencode(payload)
            signature = self.generate_signature(query_string)
            
            headers = {
                'api-key': API_KEY, 
                'signature': signature
            }
            
            response = requests.get(f"{endpoint}?{query_string}", headers=headers, timeout=10)
            
            if response.status_code == 200:
                data_str = response.text
                
                # NAYA FEATURE: Exchange exactly kya bhej raha hai, usko Render par print karo
                print(f"🔍 EXCHANGE RAW REPLY: {data_str}", flush=True)
                
                # Agar list/dict khali hai
                if data_str.strip() in ["[]", "{}"]:
                    return False
                
                try:
                    data = response.json()
                    
                    # Agar exchange ne dictionary bheji hai (eg: {"data": [...]})
                    if isinstance(data, dict):
                        for key in data.values():
                            if isinstance(key, list):
                                data = key
                                break
                    
                    # Agar list of positions hai, toh check karo quantity zero toh nahi!
                    if isinstance(data, list):
                        for pos in data:
                            symbol = str(pos.get('symbol', '')).upper()
                            # Alag-alag APIs alag naam use karti hain quantity ke liye
                            raw_qty = pos.get('positionQty', pos.get('quantity', pos.get('size', pos.get('positionAmt', 0))))
                            qty = float(raw_qty) if raw_qty else 0.0
                            
                            # Agar BTC_INR hai AUR quantity zero se zyada hai, tabhi trade open manenge
                            if SYMBOL_EXCHANGE in symbol and abs(qty) > 0:
                                return True
                                
                        return False # BTC_INR ka naam tha par quantity 0 thi
                except Exception as parse_e:
                    print(f"⚠️ JSON PARSE ERROR: {parse_e}", flush=True)

                # Agar upar ka JSON logic fail ho jaye, toh simple check lagao
                if SYMBOL_EXCHANGE in data_str and '"0"' not in data_str and '"0.0"' not in data_str:
                    return True
                return False 
            else:
                print(f'⚠️ API CALL FAILED [{response.status_code}]: {response.text}', flush=True)
                return False # API fail hone par hamesha ke liye lock mat ho
        except Exception as e:
            print(f'⚠️ STATUS CHECK ERROR: {e}', flush=True)
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
        
        is_long = (e21 > e50) and (price <= e21) if mode == 'TREND' else (rsi_val < 30)
        is_short = (e21 < e50) and (price >= e21) if mode == 'TREND' else (rsi_val > 70)
        
        return is_long, is_short, price, mode, rsi_val

    def run(self):
        print('🚀 SMART MONITORING BOT STARTED | 1H CHART | QTY: 0.025...', flush=True)
        while True:
            try:
                # STEP 1: Exchange se live pucho (Quantity check ke saath)
                trade_is_open = self.is_trade_active_on_exchange()
                
                # STEP 2: Logic Check
                if trade_is_open:
                    print("🔒 EXCHANGE STATUS: Purani trade open hai. Naya trade LOCKED hai till close.", flush=True)
                else:
                    is_long, is_short, price, mode, rsi = self.get_adaptive_signals()
                    print(f'📡 CLEAR TO SCAN | Price: {price:.2f} | RSI: {rsi:.2f} | Mode: {mode}', flush=True)
                    
                    if is_long:
                        print("📈 SIGNAL: BUY (Oversold / Trend Support)", flush=True)
                        if self.place_order('BUY'): 
                            print("🔒 ORDER PLACED! Bot is now locked for this position.", flush=True)
                    elif is_short:
                        print("📉 SIGNAL: SELL (Overbought / Trend Resistance)", flush=True)
                        if self.place_order('SELL'): 
                            print("🔒 ORDER PLACED! Bot is now locked for this position.", flush=True)
                
                time.sleep(60) 
            except Exception as e:
                print(f'⚠️ TEMPORARY LOOP ERROR: {e}', flush=True)
                time.sleep(30)


def keep_alive_ping():
    while True:
        time.sleep(600) 
        try:
            requests.get(MY_RENDER_URL, timeout=10)
            print("⚡ ANTI-SLEEP PING SUCCESSFUL! Bot is awake.", flush=True)
        except Exception:
            pass


@app.route('/')
def home(): 
    return 'Bot is syncing LIVE with Exchange (Checking Exact Quantities!). Fully automated!'

if __name__ == '__main__':
    threading.Thread(target=lambda: SharkLiveBTCBot().run(), daemon=True).start()
    threading.Thread(target=keep_alive_ping, daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
