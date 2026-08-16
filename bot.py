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
# ⚙️ CONFIGURATION & SETTINGS
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

# 👇 EXACT APPROVED STRATEGY SETTINGS 👇
BTC_QUANTITY = 0.100  
LEVERAGE = 5

TAKE_PROFIT_PCT = 1.8      # 1.8% Profit Booking
INITIAL_SL_PCT = 1.2       # 1.2% Base Stop Loss
TRAILING_DIST_PCT = 0.8    # 0.8% Trailing Distance

class SharkLiveBTCBot:
    def __init__(self):
        # Local state to track Trailing SL Live
        self.extreme_price = 0.0
        self.current_sl = 0.0
        self.current_tp = 0.0

    def generate_signature(self, data_to_sign: str) -> str:
        return hmac.new(
            SECRET_KEY.encode('utf-8'), 
            data_to_sign.encode('utf-8'), 
            hashlib.sha256
        ).hexdigest()

    def place_order(self, side: str, reduce_only: bool = False):
        endpoint = f'{BASE_URL}{ORDER_ENDPOINT_PATH}'
        payload = {
            'timestamp': int(time.time() * 1000),
            'placeType': 'ORDER_FORM',
            'quantity': BTC_QUANTITY,
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
                            raw_price = pos.get('entryPrice', pos.get('avgPrice', pos.get('positionPrice', 0)))
                            entry_price = float(raw_price) if raw_price else 0.0
                            side = 'LONG' if qty > 0 else 'SHORT'
                            
                            if SYMBOL_EXCHANGE in symbol and abs(qty) > 0:
                                return True, side, entry_price
                except Exception:
                    pass
                return False, None, 0.0
            elif response.status_code == 400 and "positionId" in response.text:
                return False, None, 0.0
            return False, None, 0.0
        except Exception:
            return False, None, 0.0

    def get_live_price_1m(self):
        try:
            df = yf.download(SYMBOL_YAHOO, period='1d', interval='1m', progress=False)
            if not df.empty:
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = [col[0] for col in df.columns]
                return float(df['Close'].iloc[-1])
        except:
            pass
        return 0.0

    def fetch_data_1h(self):
        df = yf.download(SYMBOL_YAHOO, period='5d', interval='1h', progress=False)
        if df.empty:
            raise ValueError("Yahoo Finance se data fetch fail, retrying...")
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
        df = self.fetch_data_1h()
        row = df.iloc[-1]
        price, adx_val, rsi_val = row['CLOSE'], row['ADX_14'], row['RSI_14']
        e21 = row[[c for c in df.columns if 'EMA_21' in c][0]]
        e50 = row[[c for c in df.columns if 'EMA_50' in c][0]]
        
        mode = 'TREND' if adx_val > 25 else 'SIDEWAYS'
        is_long = (e21 > e50) and (price <= e21) if mode == 'TREND' else (rsi_val < 30)
        is_short = (e21 < e50) and (price >= e21) if mode == 'TREND' else (rsi_val > 70)
        return is_long, is_short, price, mode, rsi_val

    def run(self):
        print('🚀 FINAL LIVE BOT (1.8% TP | 0.8% TRAILING SL) STARTED...', flush=True)
        while True:
            try:
                is_open, pos_side, entry_price = self.get_open_position_details()
                
                # --- AUTO-EXIT LOGIC WITH INSTANT LIVE SCAN ---
                if is_open and entry_price > 0:
                    live_price = self.get_live_price_1m()
                    if live_price > 0:
                        
                        if pos_side == 'LONG':
                            if self.current_tp == 0.0: self.current_tp = entry_price * (1 + (TAKE_PROFIT_PCT / 100))
                            if self.current_sl == 0.0: self.current_sl = entry_price * (1 - (INITIAL_SL_PCT / 100))
                            if self.extreme_price == 0.0: self.extreme_price = entry_price
                            
                            if live_price > self.extreme_price:
                                self.extreme_price = live_price
                                new_sl = self.extreme_price * (1 - (TRAILING_DIST_PCT / 100))
                                if new_sl > self.current_sl: 
                                    self.current_sl = new_sl
                                    
                            print(f"🔒 LIVE [LONG] | Entry: {entry_price:.2f} | Current: {live_price:.2f} | TP: {self.current_tp:.2f} | Trail-SL: {self.current_sl:.2f}", flush=True)

                            if live_price >= self.current_tp:
                                print("✅ TARGET 1.8% HIT! Instant Profit Booked.", flush=True)
                                if self.place_order('SELL', reduce_only=True): self.current_tp, self.current_sl, self.extreme_price = 0.0, 0.0, 0.0
                            elif live_price <= self.current_sl:
                                print("🛑 TRAILING SL HIT! Position Closed.", flush=True)
                                if self.place_order('SELL', reduce_only=True): self.current_tp, self.current_sl, self.extreme_price = 0.0, 0.0, 0.0

                        elif pos_side == 'SHORT':
                            if self.current_tp == 0.0: self.current_tp = entry_price * (1 - (TAKE_PROFIT_PCT / 100))
                            if self.current_sl == 0.0: self.current_sl = entry_price * (1 + (INITIAL_SL_PCT / 100))
                            if self.extreme_price == 0.0: self.extreme_price = entry_price
                            
                            if live_price < self.extreme_price:
                                self.extreme_price = live_price
                                new_sl = self.extreme_price * (1 + (TRAILING_DIST_PCT / 100))
                                if new_sl < self.current_sl: 
                                    self.current_sl = new_sl
                                    
                            print(f"🔒 LIVE [SHORT] | Entry: {entry_price:.2f} | Current: {live_price:.2f} | TP: {self.current_tp:.2f} | Trail-SL: {self.current_sl:.2f}", flush=True)

                            if live_price <= self.current_tp:
                                print("✅ TARGET 1.8% HIT! Instant Profit Booked.", flush=True)
                                if self.place_order('BUY', reduce_only=True): self.current_tp, self.current_sl, self.extreme_price = 0.0, 0.0, 0.0
                            elif live_price >= self.current_sl:
                                print("🛑 TRAILING SL HIT! Position Closed.", flush=True)
                                if self.place_order('BUY', reduce_only=True): self.current_tp, self.current_sl, self.extreme_price = 0.0, 0.0, 0.0

                # --- ENTRY LOGIC ---
                elif not is_open:
                    self.extreme_price, self.current_sl, self.current_tp = 0.0, 0.0, 0.0
                    
                    is_long, is_short, price, mode, rsi = self.get_adaptive_signals()
                    print(f'📡 SCANNING | Price: {price:.2f} | RSI: {rsi:.2f} | Mode: {mode}', flush=True)
                    
                    if is_long:
                        print("📈 BUY SIGNAL DETECTED. Executing Trade...", flush=True)
                        if self.place_order('BUY'): print("🔒 LONG ACTIVE! Live Monitoring Started.", flush=True)
                    elif is_short:
                        print("📉 SELL SIGNAL DETECTED. Executing Trade...", flush=True)
                        if self.place_order('SELL'): print("🔒 SHORT ACTIVE! Live Monitoring Started.", flush=True)
                
                time.sleep(30) # Har 30 second mein live price fetch karega
            except Exception as e:
                print(f'⚠️ LOOP RETRY: {e}', flush=True)
                time.sleep(60)

def keep_alive_ping():
    while True:
        time.sleep(600) 
        try:
            requests.get(MY_RENDER_URL, timeout=10)
        except Exception:
            pass

@app.route('/')
def home(): 
    return '🚀 Bot is Live! Scanning with 1.8% TP & 0.8% Trailing SL 🚀'

if __name__ == '__main__':
    threading.Thread(target=lambda: SharkLiveBTCBot().run(), daemon=True).start()
    threading.Thread(target=keep_alive_ping, daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
