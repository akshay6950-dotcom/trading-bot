import time
import urllib.request
import json
import math
import threading
import os
import builtins
import hmac
import hashlib
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime

# ==========================================
# RENDER LOGS FIX
# ==========================================
def print(*args, **kwargs):
    kwargs['flush'] = True
    builtins.print(*args, **kwargs)

# PAXG Hata diya gaya hai
SYMBOLS = ['BTC-USDT', 'ETH-USDT', 'SOL-USDT', 'XAU-USDT']
POSITION_SIZES = {'BTC-USDT': 0.035, 'ETH-USDT': 50.0, 'SOL-USDT': 10.0, 'XAU-USDT': 0.5}
CHECK_INTERVAL = 15

# Tracking Dictionaries
price_history = {symbol: [] for symbol in SYMBOLS}
active_trades = {symbol: False for symbol in SYMBOLS}
entry_prices = {symbol: 0.0 for symbol in SYMBOLS}
trade_sides = {symbol: None for symbol in SYMBOLS}
max_pnl = {symbol: 0.0 for symbol in SYMBOLS}

# ==========================================
# FETCH SECURE API KEYS FROM RENDER
# ==========================================
API_KEY = os.environ.get('API_KEY')
API_SECRET = os.environ.get('API_SECRET')

# ==========================================
# TECHNICAL INDICATORS
# ==========================================
def calculate_ema(prices, period):
    if len(prices) < period: return None
    k = 2 / (period + 1)
    ema = prices[0]
    for price in prices[1:]: ema = (price * k) + (ema * (1 - k))
    return ema

def calculate_rsi(prices, period=14):
    if len(prices) < period + 1: return 50
    gains, losses = [], []
    for i in range(1, len(prices)):
        change = prices[i] - prices[i-1]
        if change >= 0: gains.append(change); losses.append(0)
        else: gains.append(0); losses.append(abs(change))
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0: return 100
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

# ==========================================
# API PRICE FETCHER
# ==========================================
def fetch_ticker_price(symbol):
    try:
        kucoin_sym = 'PAXG-USDT' if 'XAU' in symbol else symbol
        url = f"https://api.kucoin.com/api/v1/market/orderbook/level1?symbol={kucoin_sym}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            if data['code'] == '200000': return float(data['data']['price'])
    except: pass
    try:
        clean_symbol = 'PAXGUSDT' if 'XAU' in symbol else symbol.replace('-', '')
        url = f"https://api1.binance.com/api/v3/ticker/price?symbol={clean_symbol}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            return float(json.loads(response.read().decode())['price'])
    except: return None

# ==========================================
# REAL TRADE EXECUTION & MANAGEMENT ENGINE
# ==========================================
def close_position_on_exchange(symbol, original_side):
    close_side = 'SELL' if original_side == 'BUY' else 'BUY'
    raw_qty = POSITION_SIZES.get(symbol, 0.01)
    qty = int(raw_qty) if isinstance(raw_qty, float) and raw_qty.is_integer() else raw_qty
    
    try:
        order_url = "https://api.sharkexchange.in/v1/order/place-order"
        clean_symbol = symbol.replace('-', '')
        
        # reduceOnly=True ensures it only closes the existing trade
        params = {
            'timestamp': str(int(time.time() * 1000)),
            'placeType': 'ORDER_FORM',
            'quantity': qty,
            'reduceOnly': True, 
            'side': close_side,
            'symbol': clean_symbol,
            'type': 'MARKET'
        }
        
        json_payload = json.dumps(params, separators=(',', ':'))
        signature = hmac.new(API_SECRET.encode('utf-8'), json_payload.encode('utf-8'), hashlib.sha256).hexdigest()
        
        headers = {
            "Content-Type": "application/json",
            "api-key": API_KEY,
            "signature": signature,
            "User-Agent": "Mozilla/5.0"
        }
        
        req = urllib.request.Request(order_url, data=json_payload.encode('utf-8'), headers=headers, method='POST')
        with urllib.request.urlopen(req, timeout=10) as response:
            res_data = response.read().decode()
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 🏦 EXCHANGE CONFIRMATION: Position Closed for {symbol}!")
            
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ FAILED to close {symbol} on Exchange: {e}")

def check_and_manage_trade(symbol, current_price):
    if active_trades[symbol]:
        entry_p = entry_prices[symbol]
        side = trade_sides[symbol]
        
        # Calculate Real PnL based on LONG or SHORT
        if side == 'BUY':
            pnl_pct = ((current_price - entry_p) / entry_p) * 100
        else:
            pnl_pct = ((entry_p - current_price) / entry_p) * 100
            
        # Update Highest PnL for Trailing Stop Loss
        if pnl_pct > max_pnl[symbol]:
            max_pnl[symbol] = pnl_pct
            
        target_hit = pnl_pct >= 2.5
        sl_hit = pnl_pct <= -1.0
        tsl_hit = False
        
        # Trailing SL Logic: Activate at 1.0% Profit, Trail behind by 0.5%
        if max_pnl[symbol] >= 1.0:
            if pnl_pct <= (max_pnl[symbol] - 0.5):
                tsl_hit = True
                
        if target_hit or sl_hit or tsl_hit:
            if target_hit: reason = "Target Hit 🎯"
            elif tsl_hit: reason = "Trailing SL Hit 🛡️"
            else: reason = "Stop Loss Hit 🛑"
            
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 💰 CLOSING TRADE ({reason}) for {symbol} | PnL: {round(pnl_pct, 2)}%")
            close_position_on_exchange(symbol, side)
            active_trades[symbol] = False
        else:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ⏳ Active: {symbol} | Cur: {current_price} | PnL: {round(pnl_pct, 2)}% | Max PnL: {round(max_pnl[symbol], 2)}%")
        return True
    return False

def execute_trade(symbol, side, price, reason):
    if active_trades[symbol]:
        return

    raw_qty = POSITION_SIZES.get(symbol, 0.01)
    qty = int(raw_qty) if isinstance(raw_qty, float) and raw_qty.is_integer() else raw_qty
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🚀 NEW SIGNAL ({reason}) | {symbol} | Side: {side} | Qty: {qty} | Price: {price}")
    
    if not API_KEY or not API_SECRET:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ API Keys missing! Trade skipped.")
        return

    try:
        order_url = "https://api.sharkexchange.in/v1/order/place-order"
        clean_symbol = symbol.replace('-', '')
        
        params = {
            'timestamp': str(int(time.time() * 1000)),
            'placeType': 'ORDER_FORM',
            'quantity': qty,
            'reduceOnly': False,
            'side': side,
            'symbol': clean_symbol,
            'type': 'MARKET'
        }
        
        json_payload = json.dumps(params, separators=(',', ':'))
        signature = hmac.new(API_SECRET.encode('utf-8'), json_payload.encode('utf-8'), hashlib.sha256).hexdigest()
        
        headers = {
            "Content-Type": "application/json",
            "api-key": API_KEY,
            "signature": signature,
            "User-Agent": "Mozilla/5.0"
        }
        
        req = urllib.request.Request(order_url, data=json_payload.encode('utf-8'), headers=headers, method='POST')
        with urllib.request.urlopen(req, timeout=10) as response:
            res_data = response.read().decode()
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ SUCCESS: Order opened on Shark Exchange! Reply: {res_data}")
        
        active_trades[symbol] = True
        entry_prices[symbol] = price
        trade_sides[symbol] = side
        max_pnl[symbol] = 0.0
        
    except Exception as e:
        if hasattr(e, 'read'):
            error_msg = e.read().decode()
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ FAILED on Exchange. Detail: {error_msg}")
        else:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ FAILED to connect: {e}")

# ==========================================
# BOT LOGIC LOOP
# ==========================================
def bot_loop():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] SHARK EXCHANGE LIVE ENGINE (V2.0) STARTED...")
    
    while True:
        for symbol in SYMBOLS:
            current_price = fetch_ticker_price(symbol)
            if current_price is not None:
                if check_and_manage_trade(symbol, current_price):
                    continue

                history = price_history[symbol]
                history.append(current_price)
                if len(history) > 50: history.pop(0)

                if len(history) < 5: continue

                ema_fast = calculate_ema(history, 3)
                ema_slow = calculate_ema(history, 5)
                rsi = calculate_rsi(history, 7)
                
                if rsi < 35: execute_trade(symbol, 'BUY', current_price, 'RSI Oversold')
                elif rsi > 65: execute_trade(symbol, 'SELL', current_price, 'RSI Overbought')
                elif ema_fast and ema_slow:
                    if ema_fast > ema_slow and history[-2] <= ema_slow: execute_trade(symbol, 'BUY', current_price, 'EMA Golden Cross')
                    elif ema_fast < ema_slow and history[-2] >= ema_slow: execute_trade(symbol, 'SELL', current_price, 'EMA Death Cross')
        time.sleep(CHECK_INTERVAL)

# ==========================================
# WEB SERVER
# ==========================================
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Bot is active and trading on Shark Exchange!")
    def log_message(self, format, *args): pass

def main():
    bot_thread = threading.Thread(target=bot_loop)
    bot_thread.daemon = True
    bot_thread.start()
    port = int(os.environ.get('PORT', 10000))
    server_address = ('0.0.0.0', port)
    httpd = HTTPServer(server_address, SimpleHandler)
    httpd.serve_forever()

if __name__ == "__main__":
    main()
