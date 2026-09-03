import hashlib
import hmac
import json
import os
import threading
import time
import requests
from flask import Flask
import traceback

app = Flask(__name__)

@app.route('/')
def home():
    return "Institutional Organic Desk Bot V3 is Active 24/7! (Ironclad Shield Mode)"

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
        self.real_execution_price = 0.0
        self.trade_qty = 0.002  # Testing Quantity - Jab confidence aa jaye toh ise badha dena
        self.cooldown_end_time = 0 
        self.max_unrealized_pnl = 0.0

    def generate_signature(self, data_to_sign):
        return hmac.new(SECRET_KEY.encode('utf-8'), data_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()

    def get_live_market_price(self):
        try:
            url = f"{BASE_URL}/v1/market/klines"
            payload = {"pair": "BTCUSDT", "interval": "1m", "limit": 1}
            res = requests.post(url, json=payload, timeout=5)
            
            if res.status_code in [200, 201]:
                data = res.json()
                if isinstance(data, list) and len(data) > 0:
                    val = float(data[-1].get('close', 0.0))
                    if val > 0:
                        return int(val) if val.is_integer() else val
        except Exception:
            pass
            
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
        try:
            url = f"{BASE_URL}/v1/market/klines"
            payload = {"pair": "BTCUSDT", "interval": "1m", "limit": 5}
            res = requests.post(url, json=payload, timeout=5)
            
            if res.status_code in [200, 201]:
                data = res.json()
                if isinstance(data, list) and len(data) >= 3:
                    closes = [float(c['close']) for c in data if 'close' in c]
                    current_price = closes[-1]
                    
                    recent_velocity = closes[-1] - closes[-2]
                    avg_fluctuation = sum(abs(closes[i] - closes[i-1]) for i in range(1, len(closes))) / (len(closes) - 1)
                    
                    print(f"📊 Live Desk Pulse | Current Price: {current_price} | Micro-Velocity: {recent_velocity:.1f}", flush=True)
                    
                    if recent_velocity > (avg_fluctuation * 1.3):
                        return 1, current_price
                    elif recent_velocity < -(avg_fluctuation * 1.3):
                        return -1, current_price
                    else:
                        return 0, current_price
        except Exception as e:
            pass # Keep logs clean from minor API hiccups
            
        current_price = self.get_live_market_price()
        return 0, current_price

    def execute_real_trade(self, side, quantity, price, is_exit=False):
        timestamp = str(int(time.time() * 1000))
        
        clean_price = int(price) if isinstance(price, float) and price.is_integer() else price
        if isinstance(price, float) and not price.is_integer():
            clean_price = round(price, 2)
            
        params = {
            'placeType': 'ORDER_FORM',
            'price': clean_price,             
            'quantity': quantity,
            'reduceOnly': is_exit,      
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
            print(f"🚨 FIRING REAL LIVE {side} | Qty: {quantity} | Price: {clean_price} | Exit: {is_exit}", flush=True)
            response = requests.post(f'{BASE_URL}{ORDER_ENDPOINT}', headers=headers, data=data_to_sign, timeout=15)
            
            if response.status_code == 201:
                return True
            else:
                print(f"❌ EXCHANGE ERROR: {response.status_code} | {response.text}", flush=True)
            return False
        except Exception as e:
            print(f"❌ LIVE API ERROR: {e}", flush=True)
            return False

    def run(self):
        print('🚀 FULLY DYNAMIC INSTITUTIONAL BOT ACTIVATED (Ironclad Shield Mode)...', flush=True)
        
        while True:
            try:
                time.sleep(10)
                
                if self.is_trade_open:
                    current_price = self.get_live_market_price()
                    
                    if current_price is None or current_price == 0.0:
                        continue
                        
                    price_diff = float(current_price) - float(self.real_execution_price)
                    if self.position_side == 'SELL':
                        price_diff = -price_diff
                        
                    actual_profit_usdt = price_diff * self.trade_qty
                    
                    if actual_profit_usdt > self.max_unrealized_pnl:
                        self.max_unrealized_pnl = actual_profit_usdt
                    
                    print(f"⏳ Live Position [{self.position_side}] Locked. Entry: {self.real_execution_price} | Current: {current_price} | PnL: ${actual_profit_usdt:.2f} (Peak: ${self.max_unrealized_pnl:.2f})", flush=True)
                    
                    exit_triggered = False
                    exit_reason = ""
                    
                    # Target scaling adjusted for small test quantity. You can adjust back to 3.0 and -4.0 once using 0.03 BTC.
                    if self.max_unrealized_pnl > 0.5 and (self.max_unrealized_pnl - actual_profit_usdt) >= 0.2:
                        exit_triggered = True
                        exit_reason = f"Trailing Stop Triggered (Securing ${actual_profit_usdt:.2f} Profit)"
                    elif actual_profit_usdt <= -1.0:
                        exit_triggered = True
                        exit_reason = "Dynamic Risk Floor Hit (Cutting Losses)"
                    
                    if exit_triggered:
                        exit_side = 'SELL' if self.position_side == 'BUY' else 'BUY'
                        print(f"🎯 Desk Decision: {exit_reason}. Cleaning up...", flush=True)
                        
                        success = self.execute_real_trade(exit_side, self.trade_qty, current_price, is_exit=True)
                        
                        if success:
                            self.is_trade_open = False
                            self.position_side = None
                            self.real_execution_price = 0.0
                            self.max_unrealized_pnl = 0.0
                            self.cooldown_end_time = time.time() + 60 
                            print("🧹 Position closed successfully. System Resetting...", flush=True)
                        else:
                            print("⚠️ Exit order failed. Retrying on next loop...", flush=True)
                    continue

                if time.time() < self.cooldown_end_time:
                    print("⏳ Desk cooling off... Watching order flow...", flush=True)
                    continue

                signal, market_price = self.scan_market()
                if signal != 0 and market_price is not None and market_price != 0.0:
                    side = 'BUY' if signal == 1 else 'SELL'
                    
                    print(f"💡 DESK CONVERGENCE! Executing real {side} order organically...", flush=True)
                    success = self.execute_real_trade(side, self.trade_qty, market_price, is_exit=False)
                    
                    if success:
                        self.is_trade_open = True
                        self.position_side = side
                        self.real_execution_price = market_price
                        self.max_unrealized_pnl = 0.0
                elif market_price is not None and market_price != 0.0:
                    print(f"💤 Desk monitoring live market depth... Waiting for heavy volume...", flush=True)
                    
            except Exception as e:
                print(f"🛡️ IRONCLAD SHIELD ACTIVATED: Caught an unexpected error ({e}). Keeping system alive...", flush=True)
                time.sleep(5)
                continue

if __name__ == '__main__':
    server_thread = threading.Thread(target=run_web_server)
    server_thread.daemon = True
    server_thread.start()

    bot = LiveInstitutionalBot()
    bot.run()
