import time
import requests
import json
import hmac
import hashlib
import threading
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

# ==========================================
# 1. RENDER DUMMY WEB SERVER
# ==========================================
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Whale Bot is Live!")

def start_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

# ==========================================
# 2. BOT CONFIGURATION & API DETAILS
# ==========================================
BASE_URL = 'https://api.sharkexchange.in'
SYMBOL = "BTCUSDT"
TRADE_QTY = 0.002
PROFIT_TARGET = 10.0
STOP_LOSS = -5.0

API_KEY = "0ff546ba089385f091f4dd5f52444cb1"
API_SECRET = "77b402a85f4ba4951a25753e66a2a670"

class InstitutionalWhaleBot:
    def __init__(self):
        self.is_position_open = False
        self.position_side = None
        self.entry_price = 0.0

    def generate_signature(self, data_to_sign):
        return hmac.new(
            API_SECRET.encode('utf-8'), 
            data_to_sign.encode('utf-8'), 
            hashlib.sha256
        ).hexdigest()

    def execute_real_trade(self, side, is_exit=False):
        trade_type = "EXIT" if is_exit else "ENTRY"
        print(f"[{time.strftime('%I:%M:%S %p')}] 🚀 PREPARING {trade_type} {side} ORDER...", flush=True)
        
        timestamp = str(int(time.time() * 1000))
        params = {
            'timestamp': timestamp,
            'placeType': 'ORDER_FORM',
            'quantity': TRADE_QTY,
            'side': side.upper(),
            'symbol': SYMBOL,
            'type': 'MARKET',
            'reduceOnly': is_exit,
            'marginAsset': 'INR',
            'deviceType': 'WEB',
            'userCategory': 'EXTERNAL'
        }

        data_to_sign = json.dumps(params, separators=(',', ':'))
        signature = self.generate_signature(data_to_sign)

        headers = {
            'api-key': API_KEY,
            'signature': signature,
            'Content-Type': 'application/json'
        }

        try:
            response = requests.post(f'{BASE_URL}/v1/order/place-order', json=params, headers=headers)
            response.raise_for_status()
            res_data = response.json()
            print(f"[{time.strftime('%I:%M:%S %p')}] ✅ ORDER SUCCESS: ID {res_data.get('clientOrderId', 'N/A')}", flush=True)
            return True
        except requests.exceptions.HTTPError as err:
            print(f"[{time.strftime('%I:%M:%S %p')}] ❌ ORDER HTTP ERROR: {err.response.text if err.response else err}", flush=True)
            return False
        except Exception as e:
            print(f"[{time.strftime('%I:%M:%S %p')}] ❌ ORDER EXCEPTION: {str(e)}", flush=True)
            return False

    def get_market_intelligence(self):
        current_price, bid_vol, ask_vol, cur_vol, avg_vol = 0.0, 1.0, 1.0, 1.0, 1.0
        try:
            # Sahi DEPTH URL (Bina query parameter ke)
            depth_url = f"{BASE_URL}/v1/market/depth/{SYMBOL}"
            depth_res = requests.get(depth_url, timeout=5)
            d_json = depth_res.json()
            
            if isinstance(d_json, dict) and 'bids' in d_json:
                bids = d_json.get('bids', [])
                asks = d_json.get('asks', [])
                bid_vol = sum([float(b[1]) for b in bids[:10]]) if bids else 1.0
                ask_vol = sum([float(a[1]) for a in asks[:10]]) if asks else 1.0

            # Sahi KLINE POST Request
            kline_url = f"{BASE_URL}/v1/market/klines?priceType=MARK_PRICE"
            kline_payload = {"pair": SYMBOL, "interval": "1m", "limit": 5}
            kline_res = requests.post(kline_url, json=kline_payload, headers={'Content-Type': 'application/json'}, timeout=5)
            k_json = kline_res.json()

            if isinstance(k_json, list) and len(k_json) > 0:
                latest = k_json[-1]
                current_price = float(latest[4]) if isinstance(latest, list) else float(latest.get('close', 0.0))
                cur_vol = float(latest[5]) if isinstance(latest, list) else float(latest.get('volume', 1.0))
                if len(k_json) > 1:
                    avg_vol = sum([float(k[5]) if isinstance(k, list) else float(k.get('volume', 1.0)) for k in k_json[:-1]]) / (len(k_json) - 1)

            return current_price, bid_vol, ask_vol, cur_vol, avg_vol
        except Exception as e:
            print(f"[{time.strftime('%I:%M:%S %p')}] ⚠️ API DATA ERROR: {str(e)}", flush=True)
            return current_price, bid_vol, ask_vol, cur_vol, avg_vol

    def run_strategy(self):
        print(f"[{time.strftime('%I:%M:%S %p')}] 🚀 WHALE BOT DEPLOYED V4 | QTY: {TRADE_QTY}", flush=True)
        
        while True:
            try:
                price, bid_vol, ask_vol, cur_vol, avg_vol = self.get_market_intelligence()
                
                if price > 0:
                    if not self.is_position_open:
                        print(f"[{time.strftime('%I:%M:%S %p')}] SCAN | Price: {price} | Bids: {bid_vol:.1f} | Asks: {ask_vol:.1f} | Vol: {cur_vol:.1f}", flush=True)
                        
                        if bid_vol > (ask_vol * 1.5) and cur_vol > (avg_vol * 1.2):
                            print(f"[{time.strftime('%I:%M:%S %p')}] ⚡ BUY TRIGGER FIRED!", flush=True)
                            if self.execute_real_trade("BUY"):
                                self.is_position_open = True
                                self.position_side = "BUY"
                                self.entry_price = price
                                
                        elif ask_vol > (bid_vol * 1.5) and cur_vol > (avg_vol * 1.2):
                            print(f"[{time.strftime('%I:%M:%S %p')}] ⚡ SELL TRIGGER FIRED!", flush=True)
                            if self.execute_real_trade("SELL"):
                                self.is_position_open = True
                                self.position_side = "SELL"
                                self.entry_price = price
                    else:
                        pnl = round(price - self.entry_price if self.position_side == "BUY" else self.entry_price - price, 2)
                        print(f"[{time.strftime('%I:%M:%S %p')}] ⏳ POSITION [{self.position_side}] | Entry: {self.entry_price} | PnL: ${pnl}", flush=True)
                        
                        if pnl >= PROFIT_TARGET or pnl <= STOP_LOSS:
                            exit_side = "SELL" if self.position_side == "BUY" else "BUY"
                            print(f"[{time.strftime('%I:%M:%S %p')}] EXIT TRIGGER | PnL: ${pnl}", flush=True)
                            if self.execute_real_trade(exit_side, is_exit=True):
                                self.is_position_open = False
                                self.position_side = None
                                self.entry_price = 0.0

            except Exception as e:
                print(f"[{time.strftime('%I:%M:%S %p')}] ❌ Loop Exception: {str(e)}", flush=True)
            time.sleep(4)

if __name__ == "__main__":
    try:
        my_ip = requests.get('https://api.ipify.org', timeout=5).text
        print(f"\n=======================================================")
        print(f"🚀 RENDER SERVER IP: {my_ip} (Match this with Shark!)")
        print(f"=======================================================\n")
    except:
        pass

    threading.Thread(target=start_server, daemon=True).start()
    bot = InstitutionalWhaleBot()
    bot.run_strategy()
