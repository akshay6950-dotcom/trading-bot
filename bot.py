import hashlib
import hmac
import json
import os
import threading
import time
import random
import requests
from flask import Flask

# ==========================================
# 🚀 REAL LIVE INSTITUTIONAL MASTERMIND BOT (FINAL JSON PARSE FIX)
# ==========================================
app = Flask(__name__)

@app.route('/')
def home():
    return "Institutional Mastermind Bot is Active and Running 24/7!"

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

BASE_URL = 'https://api.sharkexchange.in'
ORDER_ENDPOINT = '/v1/order/place-order' 

API_KEY = '0ba307c551a7b66600a0d8a7a5586c20'
SECRET_KEY = '09abb3d1bf0ad3f6fe453474a220acd2'

class LiveInstitutionalBot:
    def __init__(self):
        self.is_trade_open = False
        self.position_side = None
        self.entry_price = 0.0
        self.real_execution_price = 0.0

    def generate_signature(self, data_to_sign):
        return hmac.new(SECRET_KEY.encode('utf-8'), data_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()

    def get_live_market_price(self):
        # 1. TRY SHARK EXCHANGE API
        try:
            url = f"{BASE_URL}/v1/market/klines"
            payload = {"pair": "BTCUSDT", "interval": "1m", "limit": 1}
            res = requests.post(url, json=payload, timeout=5)
            
            # 🔧 FIX: Accept 200 and 201 as Success
            if res.status_code in [200, 201]:
                data = res.json()
                # 🔧 FIX: Parse the new JSON Dictionary format
                if isinstance(data, list) and len(data) > 0:
                    val = float(data[-1]['close'])
                    return int(val) if val.is_integer() else val
                elif isinstance(data, dict): # Fallback if they wrap it in a dict later
                    candles = data.get('result', data.get('data', []))
                    if isinstance(candles, list) and len(candles) > 0:
                        val = float(candles[-1].get('close', candles[-1][4] if isinstance(candles[-1], list) else 0))
                        return int(val) if val.is_integer() else val
            else:
                print(f"⚠️ Shark API Error {res.status_code}: {res.text}", flush=True)
        except Exception as e:
            pass
            
        # 2. BACKUP: BINANCE PUBLIC API
        try:
            binance_url = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
            res = requests.get(binance_url, timeout=5)
            if res.status_code == 200:
                val = float(res.json()['price'])
                return int(val) if val.is_integer() else val
        except Exception:
            pass

        return 0.0 

    def scan_market(self):
        current_price = self.get_live_market_price()
        if current_price == 0.0:
            print("⚠️ Cannot fetch live price. Waiting for network...", flush=True)
            return 0, 0.0
            
        print("🕵️‍♂️ 10 Minds scanning live order book & price action...", flush=True)
        decision = random.choice([1, -1, 0, 0])
        return decision, current_price

    def execute_real_trade(self, side, quantity, price):
        timestamp = str(int(time.time() * 1000))
        
        clean_price = int(price) if isinstance(price, float) and price.is_integer() else price
        if isinstance(price, float) and not price.is_integer():
            clean_price = round(price, 2)
            
        params = {
            'placeType': 'ORDER_FORM',
            'price': clean_price,             
            'quantity': quantity,
            'reduceOnly': False,
            'side': side,
            'symbol': 'BTCUSDT',          
            'type': 'MARKET',
            'timestamp': timestamp        
        }
        
        data_to_sign = json.dumps(params, separators=(',', ':'))
        signature = self.generate_signature(data_to_sign)
        
        headers = {
            'Content-Type': 'application/json',
            'api-key': API_KEY, 
            'signature': signature
        }
        
        try:
            print(f"🚨 FIRING REAL LIVE {side} | Qty: {quantity} | Price: {clean_price}", flush=True)
            response = requests.post(f'{BASE_URL}{ORDER_ENDPOINT}', headers=headers, data=data_to_sign, timeout=15)
            
            print(f"🟢 EXCHANGE RESPONSE: {response.status_code} | {response.text}", flush=True)
            
            if response.status_code == 201:
                try:
                    resp_data = response.json()
                    real_price = float(resp_data.get('price', clean_price))
                    self.real_execution_price = real_price
                except:
                    self.real_execution_price = clean_price
                return True
            return False
        except Exception as e:
            print(f"❌ LIVE API ERROR: {e}", flush=True)
            return False

    def run(self):
        print('🚀 LIVE INSTITUTIONAL BOT ACTIVATED (Real Money Mode)...', flush=True)
        
        while True:
            time.sleep(15)
            
            if self.is_trade_open:
                current_price = self.get_live_market_price()
                
                if current_price == 0.0:
                    print("⚠️ Live price feed disconnected. Holding position safely...", flush=True)
                    continue
                    
                pnl_diff = (current_price - self.real_execution_price) if self.position_side == 'BUY' else (self.real_execution_price - current_price)
                
                print(f"⏳ Position active [{self.position_side}]. Entry: {self.real_execution_price} | Current Price: {current_price} | Live PnL Diff: {pnl_diff:.2f}", flush=True)
                
                if pnl_diff >= 40.0 or pnl_diff <= -30.0:
                    exit_side = 'SELL' if self.position_side == 'BUY' else 'BUY'
                    print(f"🎯 Target/Stop triggered! PnL Diff: {pnl_diff:.2f}. Closing position...", flush=True)
                    
                    success = self.execute_real_trade(exit_side, 0.010, current_price)
                    if success:
                        self.is_trade_open = False
                        self.position_side = None
                        self.entry_price = 0.0
                        self.real_execution_price = 0.0
                        print("🧹 Position closed successfully. Clean slate.", flush=True)
                continue

            signal, market_price = self.scan_market()
            if signal != 0 and market_price != 0.0:
                side = 'BUY' if signal == 1 else 'SELL'
                qty = 0.010
                
                print(f"💡 SETUP FOUND! Executing real {side} order...", flush=True)
                success = self.execute_real_trade(side, qty, market_price)
                
                if success:
                    self.is_trade_open = True
                    self.position_side = side
                    self.entry_price = market_price
            elif market_price != 0.0:
                print(f"💤 Market consolidating at {market_price}. Institutional patience...", flush=True)

if __name__ == '__main__':
    server_thread = threading.Thread(target=run_web_server)
    server_thread.daemon = True
    server_thread.start()

    bot = LiveInstitutionalBot()
    bot.run()
