import os
import time
import hmac
import hashlib
import json
import requests
import threading
import traceback
from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "Institutional Algo V4.1 Operational 24/7!"

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# Shark Exchange Endpoints
BASE_URL = 'https://api.sharkexchange.in'
ORDER_ENDPOINT = '/v1/order/place-order'
DEPTH_ENDPOINT = '/v1/market/depth'
KLINE_ENDPOINT = '/v1/market/klines'

# API KEYS
API_KEY = '0ff546be089385f091f4dd5f52444cb1'
SECRET_KEY = '77b402e85f4ba4951e25753e66a2e670'

# TRADE SETTINGS
SYMBOL = "BTCUSDT"
TRADE_QTY = "0.025"  # EXACT QUANTITY
PROFIT_TARGET = 5.0  
STOP_LOSS = -2.0     

class InstitutionalWhaleBot:
    def __init__(self):
        self.is_position_open = False
        self.entry_price = 0.0
        self.position_side = None

    def generate_signature(self, timestamp, payload):
        message = f"{timestamp}{json.dumps(payload, separators=(',', ':'))}"
        return hmac.new(SECRET_KEY.encode('utf-8'), message.encode('utf-8'), hashlib.sha256).hexdigest()

    def get_market_intelligence(self):
        try:
            # 1. Fetch Order Book Depth
            depth_res = requests.get(f"{BASE_URL}{DEPTH_ENDPOINT}?symbol={SYMBOL}&limit=10", timeout=5)
            res_json = depth_res.json()
            depth_data = res_json.get('data', res_json) if isinstance(res_json, dict) else {}
            
            bids = depth_data.get('bids', [])
            asks = depth_data.get('asks', [])
            
            bid_vol = sum([float(b[1]) for b in bids]) if bids else 0
            ask_vol = sum([float(a[1]) for a in asks]) if asks else 0
            
            # 2. Fetch Recent Volume (Klines)
            kline_res = requests.get(f"{BASE_URL}{KLINE_ENDPOINT}?symbol={SYMBOL}&interval=1m&limit=5", timeout=5)
            k_json = kline_res.json()
            klines = k_json.get('data', k_json) if isinstance(k_json, dict) else []
            
            current_price = float(klines[-1][4]) if klines and len(klines) > 0 else 81000.0
            
            if klines and len(klines) >= 5:
                avg_vol = sum([float(k[5]) for k in klines[:-1]]) / len(klines[:-1])
                current_vol = float(klines[-1][5])
            else:
                avg_vol, current_vol = 1.0, 1.0

            return current_price, bid_vol, ask_vol, avg_vol, current_vol

        except Exception as e:
            # Silent catch to prevent spamming logs on minor network blips
            return 0.0, 0.0, 0.0, 0.0, 0.0

    def execute_real_trade(self, side, is_exit=False):
        try:
            timestamp = str(int(time.time() * 1000))
            payload = {
                "symbol": SYMBOL,
                "side": side,
                "orderType": "MARKET",
                "qty": TRADE_QTY
            }
            
            if is_exit:
                payload["reduceOnly"] = True

            signature = self.generate_signature(timestamp, payload)
            
            headers = {
                "X-API-KEY": API_KEY,
                "X-SIGNATURE": signature,
                "X-TIMESTAMP": timestamp,
                "Content-Type": "application/json"
            }

            print(f"[{time.strftime('%I:%M:%S %p')}] 🚨 FIRING {side} | Qty: {TRADE_QTY} | Exit: {is_exit}")
            
            response = requests.post(f"{BASE_URL}{ORDER_ENDPOINT}", headers=headers, json=payload)
            data = response.json()

            if response.status_code == 200 and data.get("code") == 0:
                print(f"[{time.strftime('%I:%M:%S %p')}] ✅ TRADE SUCCESS! ID: {data.get('data', {}).get('orderId')}")
                return True
            else:
                print(f"[{time.strftime('%I:%M:%S %p')}] ❌ EXCHANGE ERROR: {response.status_code} | {data.get('message')}")
                return False
        except Exception as e:
            print(f"[{time.strftime('%I:%M:%S %p')}] ❌ EXECUTION ERROR: {str(e)}")
            return False

    def run_strategy(self):
        print(f"[{time.strftime('%I:%M:%S %p')}] 🚀 INSTITUTIONAL WHALE BOT V4.1 RUNNING | QTY: {TRADE_QTY}")
        
        while True:
            try:
                price, bid_vol, ask_vol, avg_vol, cur_vol = self.get_market_intelligence()
                
                if price == 0.0:
                    time.sleep(3)
                    continue

                if not self.is_position_open:
                    # Print status cleanly every few cycles or when scanning
                    # Logic: Strong Imbalance + Volume Spike
                    if bid_vol > (ask_vol * 3) and cur_vol > (avg_vol * 2.5):
                        print(f"[{time.strftime('%I:%M:%S %p')}] ⚡ WHALE BUY WALL | Price: {price} | Bids: {bid_vol:.2f}")
                        if self.execute_real_trade("BUY"):
                            self.is_position_open = True
                            self.position_side = "BUY"
                            self.entry_price = price
                            
                    elif ask_vol > (bid_vol * 3) and cur_vol > (avg_vol * 2.5):
                        print(f"[{time.strftime('%I:%M:%S %p')}] ⚡ WHALE SELL DUMP | Price: {price} | Asks: {ask_vol:.2f}")
                        if self.execute_real_trade("SELL"):
                            self.is_position_open = True
                            self.position_side = "SELL"
                            self.entry_price = price

                else:
                    pnl = round(price - self.entry_price if self.position_side == "BUY" else self.entry_price - price, 2)
                    print(f"[{time.strftime('%I:%M:%S %p')}] ⏳ Live [{self.position_side}] | Entry: {self.entry_price} | Current: {price} | PnL: ${pnl}")
                    
                    exit_side = "SELL" if self.position_side == "BUY" else "BUY"
                    momentum_shifted = (self.position_side == "BUY" and ask_vol > bid_vol * 2) or (self.position_side == "SELL" and bid_vol > ask_vol * 2)

                    if pnl >= PROFIT_TARGET or pnl <= STOP_LOSS or momentum_shifted:
                        reason = "Target Hit" if pnl >= PROFIT_TARGET else "Stop Loss Hit" if pnl <= STOP_LOSS else "Momentum Shift"
                        print(f"[{time.strftime('%I:%M:%S %p')}] 🎯 Exiting Trade ({reason}) | PnL: ${pnl}")
                        
                        if self.execute_real_trade(exit_side, is_exit=True):
                            self.is_position_open = False
                            self.position_side = None
                            self.entry_price = 0.0

            except Exception as e:
                print(f"[{time.strftime('%I:%M:%S %p')}] ⚠️ Loop Exception: {str(e)}")
            
            time.sleep(3)

if __name__ == "__main__":
    # Start bot strategy in a background thread so the main thread handles Flask web server perfectly for Render
    bot_instance = InstitutionalWhaleBot()
    bot_thread = threading.Thread(target=bot_instance.run_strategy)
    bot_thread.daemon = True
    bot_thread.start()

    # Run Flask web server on main thread to satisfy Render deployment health checks instantly
    run_web_server()
