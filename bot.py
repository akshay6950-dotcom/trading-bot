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

# 👇 FIX SETTINGS (AUTO-EXIT KE LIYE) 👇
BTC_QUANTITY = 0.025  
LEVERAGE = 5

# Set Your Target & SL Here (In Percent)
TAKE_PROFIT_PCT = 1.5  # 1.5% Profit
STOP_LOSS_PCT = 1.0    # 1.0% Loss

class SharkLiveBTCBot:
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

    def get_open_position_details(self):
        """Exchange se pucho ki kya trade open hai, kis side hai, aur Entry Price kya tha!"""
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
                            
                            # Entry price aur side nikalo
                            raw_price = pos.get('entryPrice', pos.get('avgPrice', pos.get('positionPrice', 0)))
                            entry_price = float(raw_price) if raw_price else 0.0
                            
                            # Side detect karo (Long = Positive Qty, Short = Negative Qty)
                            side = 'LONG' if qty > 0 else 'SHORT'
                            
                            if SYMBOL_EXCHANGE in symbol and abs(qty) > 0:
                                return True, side, entry_price
                                
                        return False, None, 0.0
                except Exception:
                    pass
                return False, None, 0.0
            
            elif response.status_code == 400 and "positionId" in response.text:
                return False, None, 0.0
            else:
                return False, None, 0.0
        except Exception as e:
            return False, None, 0.0

    def get_live_price_1m(self):
        """Live market price nikalne ke liye 1-minute ka chart use karega taaki SL/TP jaldi trigger ho!"""
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
        print('🚀 100% AUTOMATED BOT (ENTRY & AUTO-EXIT SL/TP) STARTED...', flush=True)
        while True:
            try:
                # STEP 1: Exchange se check karo trade open hai ya nahi
                is_open, pos_side, entry_price = self.get_open_position_details()
                
                # STEP 2: AUTO EXIT LOGIC (Agar trade open hai)
                if is_open and entry_price > 0:
                    live_price = self.get_live_price_1m()
                    if live_price > 0:
                        print(f"🔒 TRADE OPEN [{pos_side}] | Entry: {entry_price:.2f} | Current: {live_price:.2f} | Target: {TAKE_PROFIT_PCT}% | SL: {STOP_LOSS_PCT}%", flush=True)
                        
                        if pos_side == 'LONG':
                            tp_price = entry_price * (1 + (TAKE_PROFIT_PCT / 100))
                            sl_price = entry_price * (1 - (STOP_LOSS_PCT / 100))
                            
                            if live_price >= tp_price:
                                print("✅ TARGET HIT! Booking Profit Now...", flush=True)
                                self.place_order('SELL', reduce_only=True)
                            elif live_price <= sl_price:
                                print("🛑 STOP LOSS HIT! Cutting Loss to save capital...", flush=True)
                                self.place_order('SELL', reduce_only=True)
                                
                        elif pos_side == 'SHORT':
                            tp_price = entry_price * (1 - (TAKE_PROFIT_PCT / 100))
                            sl_price = entry_price * (1 + (STOP_LOSS_PCT / 100))
                            
                            if live_price <= tp_price:
                                print("✅ TARGET HIT! Booking Profit Now...", flush=True)
                                self.place_order('BUY', reduce_only=True)
                            elif live_price >= sl_price:
                                print("🛑 STOP LOSS HIT! Cutting Loss to save capital...", flush=True)
                                self.place_order('BUY', reduce_only=True)
                
                # STEP 3: ENTRY LOGIC (Agar trade khali hai)
                elif not is_open:
                    is_long, is_short, price, mode, rsi = self.get_adaptive_signals()
                    print(f'📡 CLEAR TO SCAN | Price: {price:.2f} | RSI: {rsi:.2f} | Mode: {mode}', flush=True)
                    
                    if is_long:
                        print("📈 SIGNAL: BUY (Oversold / Trend Support)", flush=True)
                        if self.place_order('BUY'): 
                            print("🔒 BUY ORDER PLACED! Auto-Exit Monitoring Active.", flush=True)
                    elif is_short:
                        print("📉 SIGNAL: SELL (Overbought / Trend Resistance)", flush=True)
                        if self.place_order('SELL'): 
                            print("🔒 SELL ORDER PLACED! Auto-Exit Monitoring Active.", flush=True)
                
                time.sleep(30) # Har 30 second mein scan karega taaki SL/TP jaldi catch ho
            except Exception as e:
                print(f'⚠️ LOOP ERROR: {e}', flush=True)
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
    return 'Bot is running 100% Automated with Auto-TP and Auto-SL!'

if __name__ == '__main__':
    threading.Thread(target=lambda: SharkLiveBTCBot().run(), daemon=True).start()
    threading.Thread(target=keep_alive_ping, daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
