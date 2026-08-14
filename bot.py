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
POSITION_ENDPOINT_PATH = '/v1/positions' # Trade monitor karne ka rasta

MY_RENDER_URL = 'https://trading-bot-4axq.onrender.com'

MARGIN_ASSET = 'INR'
DEVICE_TYPE = 'WEB'
USER_CATEGORY = 'EXTERNAL'
API_KEY = '0ba307c551a7b66600a0d8a7a5586c20'
SECRET_KEY = '09abb3d1bf0ad3f6fe453474a220acd2'

SYMBOL_YAHOO = 'BTC-USD'
SYMBOL_EXCHANGE = 'BTC_INR'

# 👇 SETTINGS AS REQUESTED 👇
BTC_QUANTITY = 0.025  
LEVERAGE = 5

class SharkLiveBTCBot:
    def __init__(self):
        self.position = 0 # 0 = No Trade, 1 = Long, -1 = Short
        self.entry_price = 0.0

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
            'orderType': 'MARKET',
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
            
            # Agar order sach mein successfully lag gaya, tabhi True return karega
            if response.status_code == 200:
                return True
            return False
        except Exception:
            print(f'❌ API ERROR DETAILED:', flush=True)
            traceback.print_exc()
            return False

    def check_if_trade_closed(self):
        """Yeh function exchange se check karta hai ki trade abhi bhi open hai ya profit book ho gaya."""
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
                # Agar BTC_INR ka zikr response mein nahi hai, matlab trade close ho chuki hai
                if SYMBOL_EXCHANGE not in response.text:
                    return True # Trade is Closed (Profit/SL Hit)
                return False # Trade is still Open
                
            return False # Agar exchange API down ho, toh safe side position open maan lo
        except Exception as e:
            print(f'⚠️ STATUS CHECK ERROR: {e}', flush=True)
            return False

    def fetch_data(self):
        # 1-HOUR TIMEFRAME Data Fetch
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
        
        # 🟢 STRICT RSI 30/70 LOGIC (Sideways Market Ke Liye) 🟢
        is_long = (e21 > e50) and (price <= e21) if mode == 'TREND' else (rsi_val < 30)
        is_short = (e21 < e50) and (price >= e21) if mode == 'TREND' else (rsi_val > 70)
        
        return is_long, is_short, price, mode, rsi_val

    def run(self):
        print('🚀 SMART MONITORING BOT STARTED | 1H CHART | QTY: 0.025 | RSI: 30/70...', flush=True)
        while True:
            try:
                # 🛑 SAFETY CHECK: Agar pehle se koi trade chal rahi hai 🛑
                if self.position != 0:
                    print("🔒 TRADE ALREADY OPEN: Target ya SL hit hone ka wait kar raha hu...", flush=True)
                    if self.check_if_trade_closed():
                        print("✅ OLD TRADE BOOKED/CLOSED! Naye trade ke liye reset ho gaya.", flush=True)
                        self.position = 0 # Lock khol do
                    else:
                        print("⏳ STILL OPEN: Exchange par abhi bhi trade active hai. Waiting...", flush=True)
                
                # 🟢 ENTRY LOGIC: Agar koi trade open nahi hai, toh hi market scan karega 🟢
                else:
                    is_long, is_short, price, mode, rsi = self.get_adaptive_signals()
                    print(f'📡 SCANNING | Price: {price:.2f} | RSI: {rsi:.2f} | Mode: {mode} | Pos: {self.position}', flush=True)
                    
                    if is_long:
                        print("📈 SIGNAL: BUY (Oversold / Trend Support)", flush=True)
                        if self.place_order('BUY'): 
                            self.position = 1 # Trade lagte hi lock kar do
                            print("🔒 TRADE LOCKED: Ab profit book hone tak nayi trade nahi hogi.", flush=True)
                    elif is_short:
                        print("📉 SIGNAL: SELL (Overbought / Trend Resistance)", flush=True)
                        if self.place_order('SELL'): 
                            self.position = -1 # Trade lagte hi lock kar do
                            print("🔒 TRADE LOCKED: Ab profit book hone tak nayi trade nahi hogi.", flush=True)
                
                time.sleep(60) # Har 1 minute mein exchange se cross-verify karega
            except Exception as e:
                print(f'⚠️ TEMPORARY LOOP ERROR: {e}', flush=True)
                time.sleep(30)


# ==========================================
# ANTI-SLEEP PINGER (BOT KO JAGAYE RAKHNE KE LIYE)
# ==========================================
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
    return 'Bot is running FULLY SECURED on 1H timeframe. Waiting for proper booking before next trade!'

if __name__ == '__main__':
    threading.Thread(target=lambda: SharkLiveBTCBot().run(), daemon=True).start()
    threading.Thread(target=keep_alive_ping, daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
