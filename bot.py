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
    return "Institutional Organic Desk Bot V3.1 is Active 24/7! (Auto-Sync & Trailing PnL)"

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

BASE_URL = 'https://api.sharkexchange.in'
ORDER_ENDPOINT = '/v1/order/place-order' 
POSITION_ENDPOINT = '/v1/position/list' # 🔍 Real-time exchange sync endpoint

API_KEY = '0ba307c551a7b66600a0d8a7a5586c20'
SECRET_KEY = '09abb3d1bf0ad3f6fe453474a220acd2'

class LiveInstitutionalBot:
    def __init__(self):
        self.trade_qty = 0.015  
        self.cooldown_end_time = 0 
        self.max_unrealized_pnl = 0.0

    def generate_signature(self, data_to_sign):
        return hmac.new(SECRET_KEY.encode('utf-8'), data_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()

    def get_exchange_position(self):
        """ 🛡️ Direct Exchange Check: Bot khud exchange se poochrega ki koi position khuli hai ya nahi """
        timestamp = str(int(time.time() * 1000))
        params = {'symbol': 'BTCUSDT', 'timestamp': timestamp}
        
        data_to_sign = json.dumps(params, separators=(',', ':'))
        signature = self.generate_signature(data_to_sign)
        
        headers = {
            'Content-Type': 'application/json',
            'api-key': API_KEY, 
            'signature': signature
        }
        
        try:
            response = requests.post(f'{BASE_URL}{POSITION_ENDPOINT}', headers=headers, data=data_to_sign, timeout=5)
            if response.status_code in [200, 201]:
                data = response.json()
                # Agar exchange response mein active position milti hai
                if isinstance(data, list) and len(data) > 0:
                    for pos in data:
                        if float(pos.get('amount', 0)) > 0 or float(pos.get('positionAmt', 0)) != 0:
                            return True, pos.get('side', 'BUY'), float(pos.get('entryPrice', pos.get('price', 0)))
                elif isinstance(data, dict):
                    # Kuch APIs dictionary format mein data deti hain
                    pos_list = data.get('data', data.get('positions', []))
                    for pos in pos_list:
                        if float(pos.get('amount', pos.get('positionAmt', 0))) != 0:
                            return True, pos.get('side', 'BUY'), float(pos.get('entryPrice', pos.get('price', 0)))
        except Exception as e:
            print(f"⚠️ Position Sync Notice: {e}", flush=True)
            
        return False, None, 0.0

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
            print(f"⚠️ Organic Scan Notice: {e}", flush=True)
            
        current_price = self.get_live_market_price()
        return 0, current_price

    def execute_real_trade(self, side, quantity, price):
        timestamp = str(int(time.time() * 1000))
        clean_price = int(price) if isinstance(price, float) and price.is_integer() else round(price, 2)
            
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
        headers = {'Content-Type': 'application/json', 'api-key': API_KEY, 'signature': signature}
        
        try:
            print(f"🚨 FIRING REAL LIVE {side} | Qty: {quantity} | Price: {clean_price}", flush=True)
            response = requests.post(f'{BASE_URL}{ORDER_ENDPOINT}', headers=headers, data=data_to_sign, timeout=15)
            print(f"🟢 EXCHANGE RESPONSE: {response.status_code} | {response.text}", flush=True)
            return response.status_code == 201
        except Exception as e:
            print(f"❌ LIVE API ERROR: {e}", flush=True)
            return False

    def run(self):
        print('🚀 INSTITUTIONAL BOT V3.1 ACTIVATED (Auto-Sync Mode)...', flush=True)
        
        while True:
            time.sleep(10)
            
            # 🔄 STEP 1: Always verify real status directly from exchange
            is_open, position_side, real_execution_price = self.get_exchange_position()
            
            if is_open and real_execution_price > 0:
                current_price = self.get_live_market_price()
                if current_price == 0.0:
                    continue
                    
                price_diff = current_price - real_execution_price
                if position_side == 'SELL':
                    price_diff = -price_diff
                    
                actual_profit_usdt = price_diff * self.trade_qty
                
                if actual_profit_usdt > self.max_unrealized_pnl:
                    self.max_unrealized_pnl = actual_profit_usdt
                
                print(f"⏳ Live Position [{position_side}] Verified. Entry: {real_execution_price} | Current: {current_price} | PnL: ${actual_profit_usdt:.2f} (Peak: ${self.max_unrealized_pnl:.2f})", flush=True)
                
                exit_triggered = False
                exit_reason = ""
                
                if self.max_unrealized_pnl > 3.0 and (self.max_unrealized_pnl - actual_profit_usdt) >= 1.5:
                    exit_triggered = True
                    exit_reason = f"Trailing Stop Triggered (Securing ${actual_profit_usdt:.2f} Profit)"
                elif actual_profit_usdt <= -4.0:
                    exit_triggered = True
                    exit_reason = "Dynamic Risk Floor Hit (Cutting Losses)"
                
                if exit_triggered:
                    exit_side = 'SELL' if position_side == 'BUY' else 'BUY'
                    print(f"🎯 Desk Decision: {exit_reason}. Cleaning up...", flush=True)
                    
                    success = self.execute_real_trade(exit_side, self.trade_qty, current_price)
                    if success:
                        self.max_unrealized_pnl = 0.0
                        self.cooldown_end_time = time.time() + 60 
                        print("🧹 Position closed successfully via Exchange Sync...", flush=True)
                continue

            # Agar exchange par koi position nahi hai, toh reset max pnl
            self.max_unrealized_pnl = 0.0

            if time.time() < self.cooldown_end_time:
                print("⏳ Desk cooling off... Watching order flow...", flush=True)
                continue

            # STEP 2: Scan market only when exchange is completely clear
            signal, market_price = self.scan_market()
            if signal != 0 and market_price != 0.0:
                side = 'BUY' if signal == 1 else 'SELL'
                print(f"💡 DESK CONVERGENCE! Executing real {side} order organically...", flush=True)
                self.execute_real_trade(side, self.trade_qty, market_price)
            elif market_price != 0.0:
                print(f"💤 Desk monitoring live market depth... Waiting for heavy volume...", flush=True)

if __name__ == '__main__':
    server_thread = threading.Thread(target=run_web_server)
    server_thread.daemon = True
    server_thread.start()

    bot = LiveInstitutionalBot()
    bot.run()
