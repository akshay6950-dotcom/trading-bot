import time
import requests
import threading
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

# --- 1. DUMMY WEB SERVER (RENDER KO KHUSH RAKHNE KE LIYE) ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive and trading!")

def start_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()
# -------------------------------------------------------------

BASE_URL = 'https://api.sharkexchange.in'
DEPTH_ENDPOINT = '/v1/market/depth'
KLINE_ENDPOINT = '/v1/market/klines'
SYMBOL = "BTCUSDT"
TRADE_QTY = 0.025

class InstitutionalWhaleBot:
    def __init__(self):
        self.is_position_open = False
        self.entry_price = 0.0

    def execute_real_trade(self, side):
        print(f"[{time.strftime('%I:%M:%S %p')}] 🚀 EXECUTING {side} ORDER | Qty: {TRADE_QTY}", flush=True)
        return True

    def get_market_intelligence(self):
        try:
            # Exchange se direct jawab mang rahe hain
            depth_res = requests.get(f"{BASE_URL}{DEPTH_ENDPOINT}?symbol={SYMBOL}&limit=5", timeout=5)
            print(f"[{time.strftime('%I:%M:%S %p')}] DEBUG DEPTH: {depth_res.text}", flush=True)
            
            res_json = depth_res.json()
            bids, asks = [], []
            if isinstance(res_json, dict) and res_json.get("code", 0) == 0:
                bids = res_json.get('data', {}).get('bids', [])
                asks = res_json.get('data', {}).get('asks', [])
            
            bid_vol = sum([float(b[1]) for b in bids]) if bids else 10.0
            ask_vol = sum([float(a[1]) for a in asks]) if asks else 10.0
            
            kline_res = requests.get(f"{BASE_URL}{KLINE_ENDPOINT}?symbol={SYMBOL}&interval=1m&limit=5", timeout=5)
            print(f"[{time.strftime('%I:%M:%S %p')}] DEBUG KLINE: {kline_res.text}", flush=True)
            
            k_json = kline_res.json()
            klines = []
            if isinstance(k_json, dict) and k_json.get("code", 0) == 0:
                klines = k_json.get('data', [])
            
            if klines and len(klines) > 0:
                current_price = float(klines[-1][4])
            else:
                current_price = 81000.0

            return current_price, bid_vol, ask_vol

        except Exception as e:
            print(f"[{time.strftime('%I:%M:%S %p')}] API Error: {str(e)}", flush=True)
            return 81000.0, 10.0, 10.0

    def run_strategy(self):
        print(f"[{time.strftime('%I:%M:%S %p')}] 🚀 BOT ACTIVE WITH DUMMY SERVER...", flush=True)
        while True:
            try:
                price, bid_vol, ask_vol = self.get_market_intelligence()
                print(f"[{time.strftime('%I:%M:%S %p')}] SCAN | Price: {price} | Bids: {bid_vol:.1f} | Asks: {ask_vol:.1f}", flush=True)
            except Exception as e:
                print(f"[{time.strftime('%I:%M:%S %p')}] Loop Exception: {str(e)}", flush=True)
            
            time.sleep(4)

if __name__ == "__main__":
    # Yeh line pehle dummy web server start karegi taaki Render error na de
    threading.Thread(target=start_server, daemon=True).start()
    
    # Aur uske baad tera bot start ho jayega
    bot = InstitutionalWhaleBot()
    bot.run_strategy()
