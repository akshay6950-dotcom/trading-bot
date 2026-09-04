import time
import requests
import json
import hmac
import hashlib
import threading
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Whale Bot is Live!")

def start_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

BASE_URL = 'https://api.sharkexchange.in'
SYMBOL = "BTCUSDT"
TRADE_QTY = 0.002

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
            print(f"[{time.strftime('%I:%M:%S %p')}] ✅ ORDER SUCCESS!", flush=True)
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
            depth_url = f"{BASE_URL}/v1/market/depth/{SYMBOL}"
            depth_res = requests.get(depth_url, timeout=5)
            d_json = depth_res.json()
            
            bids, asks = [], []
            if isinstance(d_json, dict):
                d_data = d_json.get('data', d_json)
                if isinstance(d_data, dict):
                    bids = d_data.get('b', [])
                    asks = d_data.get('a', [])

            if isinstance(bids, list) and bids:
                bid_vol = sum([float(b[1]) for b in bids[:10] if isinstance(b, list) and len(b) > 1])
            if isinstance(asks, list) and asks:
                ask_vol = sum([float(a[1]) for a in asks[:10] if isinstance(a, list) and len(a) > 1])

            kline_url = f"{BASE_URL}/v1/market/klines?priceType=MARK_PRICE"
            kline_payload = {"pair": SYMBOL, "interval": "1m", "limit": 5}
            kline_res = requests.post(kline_url, json=kline_payload, headers={'Content-Type': 'application/json'}, timeout=5)
            k_json = kline_res.json()
            
            k_list = []
            if isinstance(k_json, list):
                k_list = k_json
            elif isinstance(k_json, dict):
                k_data = k_json.get('data', k_json)
                if isinstance(k_data, list):
                    k_list = k_data
                elif isinstance(k_data, dict):
                    k_list = k_data.get('klines', k_data.get('list', []))

            if isinstance(k_list, list) and len(k_list) > 0:
                latest = k_list[-1]
                if isinstance(latest, list) and len(latest) > 4:
                    current_price = float(latest[4])
                    if len(latest) > 5:
                        cur_vol = float(latest[5])
                elif isinstance(latest, dict):
                    current_price = float(latest.get('close', 0.0))
                    cur_vol = float(latest.get('volume', 1.0))

            return current_price, bid_vol, ask_vol, cur_vol, avg_vol
        except Exception as e:
            return current_price, bid_vol, ask_vol, cur_vol, avg_vol

    def run_strategy(self):
        print(f"[{time.strftime('%I:%M:%S %p')}] 🚀 WHALE BOT LOCKED V11 (Permanent State)", flush=True)
        while True:
            try:
                price, bid_vol, ask_vol, cur_vol, avg_vol = self.get_market_intelligence()
                if price > 0:
                    pnl = 0.0
                    if self.is_position_open:
                        pnl = round(price - self.entry_price if self.position_side == "BUY" else self.entry_price - price, 2)
                        print(f"[{time.strftime('%I:%M:%S %p')}] SCAN | Price: {price} | Bids: {bid_vol:.1f} | Asks: {ask_vol:.1f} | POS: {self.position_side} | PnL: ${pnl}", flush=True)
                    else:
                        print(f"[{time.strftime('%I:%M:%S %p')}] SCAN | Price: {price} | Bids Vol: {bid_vol:.1f} | Asks Vol: {ask_vol:.1f}", flush=True)
                    
                    if not self.is_position_open:
                        if bid_vol > (ask_vol * 1.5):
                            print(f"[{time.strftime('%I:%M:%S %p')}] ⚡ BUY SIGNAL DETECTED!", flush=True)
                            if self.execute_real_trade("BUY"):
                                self.is_position_open = True
                                self.position_side = "BUY"
                                self.entry_price = price
                                
                        elif ask_vol > (bid_vol * 1.5):
                            print(f"[{time.strftime('%I:%M:%S %p')}] ⚡ SELL SIGNAL DETECTED!", flush=True)
                            if self.execute_real_trade("SELL"):
                                self.is_position_open = True
                                self.position_side = "SELL"
                                self.entry_price = price
                    else:
                        if self.position_side == "BUY" and ask_vol > (bid_vol * 1.5):
                            print(f"[{time.strftime('%I:%M:%S %p')}] 🔄 REVERSAL EXIT TRIGGER (Sellers Took Over) | PnL: ${pnl}", flush=True)
                            if self.execute_real_trade("SELL", is_exit=True):
                                self.is_position_open = False
                                self.position_side = None
                                self.entry_price = 0.0
                                
                        elif self.position_side == "SELL" and bid_vol > (ask_vol * 1.5):
                            print(f"[{time.strftime('%I:%M:%S %p')}] 🔄 REVERSAL EXIT TRIGGER (Buyers Took Over) | PnL: ${pnl}", flush=True)
                            if self.execute_real_trade("BUY", is_exit=True):
                                self.is_position_open = False
                                self.position_side = None
                                self.entry_price = 0.0

            except Exception as e:
                pass
            time.sleep(4)

if __name__ == "__main__":
    try:
        my_ip = requests.get('https://api.ipify.org', timeout=5).text
        print(f"\n=======================================================")
        print(f"🚀 RENDER SERVER IP: {my_ip}")
        print(f"=======================================================\n")
    except:
        pass

    threading.Thread(target=start_server, daemon=True).start()
    bot = InstitutionalWhaleBot()
    bot.run_strategy()
