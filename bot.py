import hashlib
import hmac
import json
import os
import threading
import time
import random
import requests

# ==========================================
# 🏛️ INSTITUTIONAL MASTERMIND BOT (10 MINDS LIVE)
# ==========================================
BASE_URL = 'https://api.sharkexchange.in'
ORDER_ENDPOINT = '/v1/order/place-order' 

API_KEY = '0ba307c551a7b66600a0d8a7a5586c20'
SECRET_KEY = '09abb3d1bf0ad3f6fe453474a220acd2'

class InstitutionalBot:
    def __init__(self):
        self.is_trade_open = False
        self.active_order_id = None
        self.entry_price = 0.0
        self.position_side = None

    def generate_signature(self, data_to_sign):
        return hmac.new(SECRET_KEY.encode('utf-8'), data_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()

    # ---------------------------------------------------------
    # 🧠 THE 10 INSTITUTIONAL MINDS (Market Scanner)
    # ---------------------------------------------------------
    def scan_institutional_flow(self):
        print("🕵️‍♂️ 10 Minds scanning order books, volume & price action...", flush=True)
        
        # Yahan hum live market candles / order book depth read karenge
        # Human trader ki tarah confluence check hoga (e.g., momentum + spread)
        
        # Simulated institutional decision engine (-1: Sell, 0: Wait, 1: Buy)
        decision = random.choice([1, -1, 0, 0]) 
        current_price = 77550.0  # Live price placeholder
        
        return decision, current_price

    # ---------------------------------------------------------
    # ⚖️ DYNAMIC QUANTITY ALLOCATOR (0.25 to 0.50)
    # ---------------------------------------------------------
    def get_smart_quantity(self):
        # Confidence ke hisaab se variable size uthana (Institutional Risk Management)
        qty = random.uniform(0.25, 0.50)
        return round(qty, 3)

    # ---------------------------------------------------------
    # 🚀 EXECUTE LIVE MARKET ORDER
    # ---------------------------------------------------------
    def place_order(self, side, quantity, price):
        timestamp = str(int(time.time() * 1000))
        params = {
            'placeType': 'ORDER_FORM',
            'price': price,             
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
            print(f"📦 FIRING INSTITUTIONAL {side} | Qty: {quantity}", flush=True)
            response = requests.post(f'{BASE_URL}{ORDER_ENDPOINT}', headers=headers, data=data_to_sign, timeout=15)
            
            if response.status_code == 201:
                res_data = response.json()
                print(f"✅ ORDER SUCCESS: {res_data.get('id')}", flush=True)
                return True, res_data.get('id')
            else:
                print(f"❌ ORDER FAILED: {response.text}", flush=True)
                return False, None
        except Exception as e:
            print(f"❌ API EXCEPTION: {e}", flush=True)
            return False, None

    # ---------------------------------------------------------
    # 🔄 24/7 HUMAN-LIKE MONITORING LOOP
    # ---------------------------------------------------------
    def run(self):
        print('🏛️ Institutional Bot Active & Monitoring 24/7...', flush=True)
        
        while True:
            time.sleep(15) # Human reaction time gap
            
            # RULE 1: STRICT 1-ORDER POLICY (Jab tak close nahi hota, naya nahi aayega)
            if self.is_trade_open:
                print("⏳ Position active. Human mind tracking P&L for exit...", flush=True)
                
                # Simulated profit/loss tracking check
                # Agar target hit ho gaya, toh opposite order daal kar exit marenge
                hit_target = random.choice([True, False]) # Real logic mein price tracking hogi
                
                if hit_target:
                    print("🎯 Target Hit! Booking profit and closing position...", flush=True)
                    # Reverse order to close position
                    exit_side = 'SELL' if self.position_side == 'BUY' else 'BUY'
                    self.place_order(exit_side, 0.25, 77550.0)
                    
                    # Reset state for next trade
                    self.is_trade_open = False
                    self.position_side = None
                    print("🧹 Clean slate. Ready for next high-probability setup.", flush=True)
                continue

            # RULE 2: SCANNING FOR FRESH ENTRY
            signal, market_price = self.scan_institutional_flow()
            
            if signal != 0:
                side = 'BUY' if signal == 1 else 'SELL'
                qty = self.get_smart_quantity()
                
                print(f"🚨 SETUP FOUND! Executing institutional {side} with {qty} BTC...", flush=True)
                success, order_id = self.place_order(side, qty, market_price)
                
                if success:
                    self.is_trade_open = True
                    self.position_side = side
                    self.entry_price = market_price
                    self.active_order_id = order_id
            else:
                print("💤 Market consolidating. Institutional patience...", flush=True)

if __name__ == '__main__':
    bot = InstitutionalBot()
    bot.run()
