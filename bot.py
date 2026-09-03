import hashlib
import hmac
import json
import os
import threading
import time
import requests
from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "Institutional Organic Desk Bot V3 is Active 24/7! (Live Trailing & Dynamic PnL)"

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

BASE_URL = 'https://api.sharkexchange.in'
ORDER_ENDPOINT = '/v1/order/place-order' 

API_KEY = '0ba307c551a7b66600a0d8a7a5586c20'
SECRET_KEY = '09abb3d1bf0ad3f6fe453474a220acd2'

class LiveInstitutionalBot:
    def __init__(self):
        # 🧠 Institutional Memory & Dynamic Tracking
        self.is_trade_open = False  
        self.position_side = None
        self.real_execution_price = 0.0
        self.trade_qty = 0.015  
        self.cooldown_end_time = 0 
        self.max_unrealized_pnl = 0.0  # Live peak profit track karne ke liye

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
            payload = {"pair": "BTCUSDT", "interval": "1m", "limit": 5} # Fast tracking
            res = requests.post(url, json=payload, timeout=5)
            
            if res.status_code in [200, 201]:
                data = res.json()
                if isinstance(data, list) and len(data) >= 3:
                    closes = [float(c['close']) for c in data if 'close' in c]
                    current_price = closes[-1]
                    
                    recent_velocity = closes[-1] - closes[-2] # More sensitive to immediate volume
                    avg_fluctuation = sum(abs(closes[i] - closes[i-1]) for i in range(1, len(closes))) / (len(closes) - 1)
                    
                    print(f"📊 Live Desk Pulse | Current Price: {current_price} | Micro-Velocity: {recent_velocity:.1f}", flush=True)
                    
                    # Core institutional trigger logic (Sensitive for more trades)
                    if recent_velocity > (avg_fluctuation * 1.3):
                        return 1, current_price
                    elif recent_velocity < -(avg_fluctuation * 1.3):
                        return -1, current_price
                    else:
                        return 0, current_price
        except Exception as e:
            print(f"⚠️ Organic Scan Notice: {e}", flush=True)
            
        current_price = self.get_live_market_price()
        return 0, current_price

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
                return True
            return False
        except Exception as e:
            print(f"❌ LIVE API ERROR: {e}", flush=True)
            return False

    def run(self):
        print('🚀 FULLY DYNAMIC INSTITUTIONAL BOT ACTIVATED (V3 Live PnL Tracking)...', flush=True)
        
        while True:
            time.sleep(10) # Thoda fast scanning loop
            
            if self.is_trade_open:
                current_price = self.get_live_market_price()
                
                if current_price == 0.0:
                    continue
                    
                price_diff = current_price - self.real_execution_price
                if self.position_side == 'SELL':
                    price_diff = -price_diff
                    
                actual_profit_usdt = price_diff * self.trade_qty
                
                # Live Max PnL Record karna
                if actual_profit_usdt > self.max_unrealized_pnl:
                    self.max_unrealized_pnl = actual_profit_usdt
                
                print(f"⏳ Live Position [{self.position_side}] Locked. Entry: {self.real_execution_price} | Current: {current_price} | PnL: ${actual_profit_usdt:.2f} (Peak: ${self.max_unrealized_pnl:.2f})", flush=True)
                
                exit_triggered = False
                exit_reason = ""
                
                # 🧠 Dynamic Exit Logic
                # Agar profit accha khaasa ho chuka hai (>$3) aur achanak se market $1.5 peeche ghum jaye, toh trailing profit book karo
                if self.max_unrealized_pnl > 3.0 and (self.max_unrealized_pnl - actual_profit_usdt) >= 1.5:
                    exit_triggered = True
                    exit_reason = f"Trailing Stop Triggered (Securing ${actual_profit_usdt:.2f} Profit)"
                
                # Agar market shuru mein hi ulti direction mein bhaag jaye aur -$4 ka loss dikhaye toh disaster se bacho
                elif actual_profit_usdt <= -4.0:
                    exit_triggered = True
                    exit_reason = "Dynamic Risk Floor Hit (Cutting Losses)"
                
                if exit_triggered:
                    exit_side = 'SELL' if self.position_side == 'BUY' else 'BUY'
                    print(f"🎯 Desk Decision: {exit_reason}. Cleaning up...", flush=True)
                    
                    success = self.execute_real_trade(exit_side, self.trade_qty, current_price)
                    
                    if success:
                        self.is_trade_open = False
                        self.position_side = None
                        self.real_execution_price = 0.0
                        self.max_unrealized_pnl = 0.0 # Agle trade ke liye PnL reset
                        self.cooldown_end_time = time.time() + 60 
                        print("🧹 Position closed successfully. System Resetting for next convergence...", flush=True)
                    else:
                        print("⚠️ Exit order failed. Retrying on next loop...", flush=True)
                continue

            if time.time() < self.cooldown_end_time:
                print("⏳ Desk cooling off... Watching order flow...", flush=True)
                continue

            # Fully Dynamic Market Scanning
            signal, market_price = self.scan_market()
            if signal != 0 and market_price != 0.0:
                side = 'BUY' if signal == 1 else 'SELL'
                
                print(f"💡 DESK CONVERGENCE! Executing real {side} order organically...", flush=True)
                success = self.execute_real_trade(side, self.trade_qty, market_price)
                
                if success:
                    # 🔒 Lock system
                    self.is_trade_open = True
                    self.position_side = side
                    self.real_execution_price = market_price
                    self.max_unrealized_pnl = 0.0
            elif market_price != 0.0:
                print(f"💤 Desk monitoring live market depth... Waiting for heavy volume...", flush=True)

if __name__ == '__main__':
    server_thread = threading.Thread(target=run_web_server)
    server_thread.daemon = True
    server_thread.start()

    bot = LiveInstitutionalBot()
    bot.run()
