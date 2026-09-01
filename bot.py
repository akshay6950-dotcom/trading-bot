import hashlib
import hmac
import json
import os
import threading
import time
import random
import requests

# ==========================================
# 🧠 THE MASTERMIND BOT (10 HUMAN MINDS)
# ==========================================
BASE_URL = 'https://api.sharkexchange.in'
ORDER_ENDPOINT = '/v1/order/place-order' 

API_KEY = 'YOUR_API_KEY'
SECRET_KEY = 'YOUR_SECRET_KEY'

class MastermindBot:
    def __init__(self):
        self.is_trade_open = False  # The Strict Priority Rule: One order at a time
        self.current_position_side = None
        self.entry_price = 0.0

    def generate_signature(self, data_to_sign):
        return hmac.new(SECRET_KEY.encode('utf-8'), data_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()

    # ---------------------------------------------------------
    # 🕵️‍♂️ THE 10 MINDS SCANNER (Human Logic Simulation)
    # ---------------------------------------------------------
    def scan_market(self):
        print("🔍 10 Minds Scanning the market...", flush=True)
        # Yahan hum market data pull karenge (e.g., current price, volume)
        # Abhi ke liye hum isko ek simulated human decision banate hain
        
        # Simulated logic combining multiple factors
        # 1 = Strong Buy, -1 = Strong Sell, 0 = Wait (No clear trend)
        decision_score = random.choice([1, -1, 0, 0, 1]) 
        current_market_price = 77500.0 # Yeh actual API se pull hoga
        
        return decision_score, current_market_price

    # ---------------------------------------------------------
    # 🎯 THE DYNAMIC SIZER (0.25 to 0.50 BTC)
    # ---------------------------------------------------------
    def get_dynamic_quantity(self):
        # Human mind ki tarah confidence ke hisaab se quantity uthayega
        qty = random.uniform(0.25, 0.50)
        return round(qty, 3) # Max 3 decimal places for API safety

    # ---------------------------------------------------------
    # 🚀 THE EXECUTIONER
    # ---------------------------------------------------------
    def execute_trade(self, side, quantity, price):
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
        
        headers = {'Content-Type': 'application/json', 'api-key': API_KEY, 'signature': signature}
        
        print(f"📦 PLACING {side} ORDER | Qty: {quantity} | Payload: {data_to_sign}", flush=True)
        # response = requests.post(f'{BASE_URL}{ORDER_ENDPOINT}', headers=headers, data=data_to_sign)
        # return response.status_code
        return 201 # Simulated success for now

    # ---------------------------------------------------------
    # ⚙️ THE MAIN LOOP (Runs 24/7)
    # ---------------------------------------------------------
    def run(self):
        print('🧠 Mastermind Bot Started...', flush=True)
        
        while True:
            time.sleep(10) # Har 10 second mein market dekhega (human speed)
            
            # RULE 1: Pehle check karo koi trade open hai ya nahi
            if self.is_trade_open:
                print("⏳ Trade already running. Scanning for Exit (Take Profit / Stop Loss)...", flush=True)
                # Yahan hum logic lagayenge ki agar profit hit hua toh position close kardo
                # self.is_trade_open = False (jab trade close ho jayega)
                continue

            # RULE 2: Agar trade open nahi hai, toh fresh scanning shuru karo
            decision, current_price = self.scan_market()
            
            if decision == 1:
                qty = self.get_dynamic_quantity()
                print(f"🟢 MINDS AGREED: BUY SIGNAL! Confidence Qty: {qty}", flush=True)
                status = self.execute_trade('BUY', qty, current_price)
                if status == 201:
                    self.is_trade_open = True
                    self.current_position_side = 'BUY'
                    self.entry_price = current_price
                    
            elif decision == -1:
                qty = self.get_dynamic_quantity()
                print(f"🔴 MINDS AGREED: SELL SIGNAL! Confidence Qty: {qty}", flush=True)
                status = self.execute_trade('SELL', qty, current_price)
                if status == 201:
                    self.is_trade_open = True
                    self.current_position_side = 'SELL'
                    self.entry_price = current_price
            else:
                print("🟡 MINDS CONFUSED: Waiting for better setup...", flush=True)

if __name__ == '__main__':
    bot = MastermindBot()
    bot.run()
