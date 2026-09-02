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
    return "Institutional Desk Bot (True Market Mindset) Active 24/7!"

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

BASE_URL = 'https://api.sharkexchange.in'
ORDER_ENDPOINT = '/v1/order/place-order' 

API_KEY = '0ba307c551a7b66600a0d8a7a5586c20'
SECRET_KEY = '09abb3d1bf0ad3f6fe453474a220acd2'

class InstitutionalDeskBot:
    def __init__(self):
        self.is_trade_open = False
        self.position_side = None
        self.entry_price = 0.0
        self.real_execution_price = 0.0
        self.cooldown_end_time = 0 
        self.sync_active_position_from_exchange()

    def generate_signature(self, data_to_sign):
        return hmac.new(SECRET_KEY.encode('utf-8'), data_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()

    def sync_active_position_from_exchange(self):
        try:
            timestamp = str(int(time.time() * 1000))
            params = {'symbol': 'BTCUSDT', 'timestamp': timestamp}
            data_to_sign = json.dumps(params, separators=(',', ':'))
            signature = self.generate_signature(data_to_sign)
            
            headers = {
                'Content-Type': 'application/json',
                'api-key': API_KEY, 
                'signature': signature
            }
            
            res = requests.post(f"{BASE_URL}/v1/position/open-position", headers=headers, data=data_to_sign, timeout=5)
            if res.status_code in [200, 201]:
                data = res.json()
                if data and isinstance(data, dict) and float(data.get('quantity', 0)) > 0:
                    self.is_trade_open = True
                    self.position_side = data.get('side', 'BUY')
                    self.real_execution_price = float(data.get('entryPrice', 0))
                    print(f"🛡️ Institutional Sync: Active position detected [{self.position_side} @ {self.real_execution_price}]", flush=True)
                    return
        except Exception as e:
            print(f"⚠️ Sync Notice: {e}", flush=True)
            
        self.cooldown_end_time = time.time() + 30
        print("🛡️ Desk initialized. Clean state ready.", flush=True)

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
        """
        🧠 Institutional Mindset: Reads deep market velocity and order flow momentum 
        across multiple candles, ignoring minor retail noise.
        """
        try:
            url = f"{BASE_URL}/v1/market/klines"
            payload = {"pair": "BTCUSDT", "interval": "1m", "limit": 12}
            res = requests.post(url, json=payload, timeout=5)
            
            if res.status_code in [200, 201]:
                data = res.json()
                if isinstance(data, list) and len(data) >= 8:
                    closes = [float(c['close']) for c in data if 'close' in c]
                    current_price = closes[-1]
                    
                    # Institutional momentum calculation across recent structure
                    momentum_shift = closes[-1] - closes[-4]
                    structural_volatility = sum(abs(closes[i] - closes[i-1]) for i in range(1, len(closes))) / (len(closes) - 1)
                    
                    print(f"📊 Institutional Desk View | Price: {current_price} | Momentum: {momentum_shift:.1f} | Volatility Filter: {structural_volatility:.1f}", flush=True)
                    
                    # Clear institutional conviction trigger (ignoring micro-noise)
                    if momentum_shift > (structural_volatility * 1.5):
                        print("🚀 Institutional Flow: Strong structural accumulation. BUY execution...", flush=True)
                        return 1, current_price
                    elif momentum_shift < -(structural_volatility * 1.5):
                        print("🔻 Institutional Flow: Strong structural distribution. SELL execution...", flush=True)
                        return -1, current_price
                    else:
                        return 0, current_price
        except Exception as e:
            print(f"⚠️ Scan Notice: {e}", flush=True)
            
        current_price = self.get_live_market_price()
        return 0, current_price

    def execute_real_trade(self, side, quantity, price, is_reduce_only=False):
        timestamp = str(int(time.time() * 1000))
        
        clean_price = int(price) if isinstance(price, float) and price.is_integer() else price
        if isinstance(price, float) and not price.is_integer():
            clean_price = round(price, 2)
            
        params = {
            'placeType': 'ORDER_FORM',
            'price': clean_price,             
            'quantity': quantity,
            'reduceOnly': bool(is_reduce_only), 
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
            order_type = "EXIT (REDUCE-ONLY)" if is_reduce_only else "ENTRY"
            print(f"🚨 INSTITUTIONAL ORDER [{side}] ({order_type}) | Qty: {quantity} | Price: {clean_price}", flush=True)
            response = requests.post(f'{BASE_URL}{ORDER_ENDPOINT}', headers=headers, data=data_to_sign, timeout=15)
            
            print(f"🟢 EXCHANGE RESPONSE: {response.status_code} | {response.text}", flush=True)
            
            if response.status_code == 201:
                if not is_reduce_only:
                    try:
                        resp_data = response.json()
                        real_price = float(resp_data.get('price', clean_price))
                        self.real_execution_price = real_price
                    except:
                        self.real_execution_price = clean_price
                return True
            return False
        except Exception as e:
            print(f"❌ API ERROR: {e}", flush=True)
            return False

    def run(self):
        print('🚀 INSTITUTIONAL DESK BOT ACTIVATED (No Panic Wiggles, True Structure Flow)...', flush=True)
        
        while True:
            time.sleep(15)
            
            if self.is_trade_open:
                current_price = self.get_live_market_price()
                
                if current_price == 0.0:
                    continue
                    
                price_diff = (current_price - self.real_execution_price) if self.position_side == 'BUY' else (self.real_execution_price - current_price)
                actual_profit_usdt = price_diff * 0.015
                
                print(f"⏳ Managing Position [{self.position_side}]. Entry: {self.real_execution_price} | Current: {current_price} | PnL: ${actual_profit_usdt:.2f}", flush=True)
                
                # 🧠 INSTITUTIONAL MINDSET EXIT LOGIC:
                # 1. Take solid profit when target is achieved ($10+).
                # 2. Give room to breathe: Only cut if the trend completely breaks against us (-$8 structural buffer), 
                #    preventing any premature panic over minor wiggles.
                if actual_profit_usdt >= 10.0 or actual_profit_usdt <= -8.0:
                    exit_side = 'SELL' if self.position_side == 'BUY' else 'BUY'
                    print(f"🎯 Institutional Desk Action: Finalizing trade at PnL: ${actual_profit_usdt:.2f}.", flush=True)
                    
                    success = self.execute_real_trade(exit_side, 0.015, current_price, is_reduce_only=True)
                    if success:
                        self.is_trade_open = False
                        self.position_side = None
                        self.entry_price = 0.0
                        self.real_execution_price = 0.0
                        self.cooldown_end_time = time.time() + 90
                        print("🧹 Position cleared cleanly. Desk scanning next major wave...", flush=True)
                continue

            if time.time() < self.cooldown_end_time:
                print("⏳ Desk analyzing order book depth...", flush=True)
                continue

            signal, market_price = self.scan_market()
            if signal != 0 and market_price != 0.0:
                side = 'BUY' if signal == 1 else 'SELL'
                qty = 0.015
                
                print(f"💡 INSTITUTIONAL SETUP CONFIRMED! Executing real {side}...", flush=True)
                success = self.execute_real_trade(side, qty, market_price, is_reduce_only=False)
                
                if success:
                    self.is_trade_open = True
                    self.position_side = side
                    self.entry_price = market_price
            elif market_price != 0.0:
                print(f"💤 Waiting for true institutional volume...", flush=True)

if __name__ == '__main__':
    server_thread = threading.Thread(target=run_web_server)
    server_thread.daemon = True
    server_thread.start()

    bot = InstitutionalDeskBot()
    bot.run()
