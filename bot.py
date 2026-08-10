import time
import logging
import threading
import os
import urllib.request
import hmac
import hashlib
import json
import requests
from flask import Flask
import ccxt
import pandas as pd
import pandas_ta as ta

# Logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - INFO - %(message)s')

active_trades = {
    'SOLUSDT': None,
    'BTCUSDT': None
}

# Corrected quantities matching margin requirements and docs decimals
QUANTITIES = {
    'SOLUSDT': 5,     
    'BTCUSDT': 0.035     
}

# --- API KEYS ---
API_KEY = '0ba307c551a7b66600a0d8a7a5586c20' 
API_SECRET = '09abb3d1bf0ad3f6fe453474a220acd2'

BASE_URL = 'https://api.sharkexchange.in'

def generate_signature(api_secret, data_to_sign):
    return hmac.new(api_secret.encode('utf-8'), data_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()

def place_shark_order(symbol, side, quantity):
    try:
        endpoint = '/v1/order/place-order'
        url = BASE_URL + endpoint
        
        timestamp = str(int(time.time() * 1000))
        
        params = {
            'timestamp': timestamp,
            'placeType': 'ORDER_FORM',
            'quantity': quantity,
            'side': side.upper(),
            'symbol': symbol,
            'type': 'MARKET',
            'reduceOnly': False,
            'marginAsset': 'INR', 
            'deviceType': 'WEB',
            'userCategory': 'EXTERNAL'
        }
        
        data_string = json.dumps(params, sort_keys=True, separators=(',', ':'))
        signature = generate_signature(API_SECRET, data_string)
        
        headers = {
            'api-key': API_KEY,
            'signature': signature,
            'Content-Type': 'application/json'
        }
        
        response = requests.post(url, data=data_string, headers=headers)
        res_data = response.json()
        
        if response.status_code == 200 and (res_data.get('success') or res_data.get('result') or 'error' not in res_data):
            logging.info(f"Shark Exchange Order Placed Successfully for {symbol}!")
            return True
        else:
            logging.error(f"Shark Exchange Order Failed: {res_data}")
            return False
    except Exception as e:
        logging.error(f"Order execution exception: {e}")
        return False

def fetch_market_data(symbol):
    try:
        ex = ccxt.delta({'enableRateLimit': True})
        bars = ex.fetch_ohlcv(symbol, timeframe='15m', limit=250)
        if not bars: return None

        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df.ta.ema(length=50, append=True)
        df.ta.ema(length=200, append=True)
        df.ta.macd(fast=12, slow=26, signal=9, append=True)
        df.ta.rsi(length=14, append=True)
        df['vol_ma'] = df['volume'].rolling(window=20).mean()
        latest = df.iloc[-1]
        
        return {
            'price': float(latest['close']),
            'ema_50': float(latest['EMA_50']),
            'ema_200': float(latest['EMA_200']),
            'macd': float(latest['MACD_12_26_9']),
            'signal': float(latest['MACDs_12_26_9']),
            'rsi': float(latest['RSI_14']),
            'vol': float(latest['volume']),
            'vol_ma': float(latest['vol_ma'])
        }
    except Exception as e:
        return None

def check_strategies(symbol, data):
    price, ema_50, ema_200 = data['price'], data['ema_50'], data['ema_200']
    macd, signal, rsi = data['macd'], data['signal'], data['rsi']
    vol, vol_ma = data['vol'], data['vol_ma']

    if symbol == 'SOLUSDT':
        long_1 = (price > ema_50) and (ema_50 > ema_200) and (macd > signal) and (45 <= rsi <= 70)
        long_2 = (rsi < 40) and (macd > signal) and (price > ema_200)
        long_3 = (macd > signal) and (50 <= rsi <= 75) and (price > ema_50)
        if long_1: return "SOL Long 1", 'buy'
        elif long_2: return "SOL Long 2", 'buy'
        elif long_3: return "SOL Long 3", 'buy'
        
    elif symbol == 'BTCUSDT':
        long_1 = (price > ema_50) and (macd > signal) and (50 < rsi < 68) and (vol > vol_ma * 1.2)
        long_2 = (price > ema_50) and (ema_50 > ema_200) and (macd > signal) and (45 <= rsi <= 70)
        long_3 = (rsi < 40) and (macd > signal) and (price > ema_200)
        if long_1: return "BTC Long 1", 'buy'
        elif long_2: return "BTC Long 2", 'buy'
        elif long_3: return "BTC Long 3", 'buy'

    if symbol == 'SOLUSDT':
        short_1 = (price < ema_50) and (ema_50 < ema_200) and (macd < signal) and (30 <= rsi <= 55)
        short_2 = (rsi > 60) and (macd < signal) and (price < ema_200)
        short_3 = (macd < signal) and (25 <= rsi <= 50) and (price < ema_50)
        if short_1: return "SOL Short 1", 'sell'
        elif short_2: return "SOL Short 2", 'sell'
        elif short_3: return "SOL Short 3", 'sell'
        
    elif symbol == 'BTCUSDT':
        short_1 = (price < ema_50) and (macd < signal) and (32 < rsi < 50) and (vol > vol_ma * 1.2)
        short_2 = (price < ema_50) and (ema_50 < ema_200) and (macd < signal) and (30 <= rsi <= 55)
        short_3 = (rsi > 60) and (macd < signal) and (price < ema_200)
        if short_1: return "BTC Short 1", 'sell'
        elif short_2: return "BTC Short 2", 'sell'
        elif short_3: return "BTC Short 3", 'sell'

    return None, None

def run_trading_bot():
    global active_trades
    logging.info("Shark Exchange Margin-Optimized Bot Running...")
    symbols = ['SOLUSDT', 'BTCUSDT']

    while True:
        try:
            for symbol in symbols:
                data = fetch_market_data(symbol)
                if not data: continue
                    
                price, rsi = data['price'], data['rsi']
                logging.info(f"SCAN {symbol} - Price: {price:.2f} | RSI: {rsi:.2f}")

                if active_trades[symbol] is None:
                    strategy_name, trade_side = check_strategies(symbol, data)
                    if strategy_name and trade_side:
                        qty = QUANTITIES[symbol]
                        logging.info(f"SIGNAL: {strategy_name}! Placing Order...")
                        success = place_shark_order(symbol, trade_side, qty)
                        if success:
                            active_trades[symbol] = {'side': trade_side, 'quantity': qty}

            time.sleep(30)
        except Exception as e:
            time.sleep(10)

app = Flask(__name__)
@app.route('/')
def keep_alive():
    ip = urllib.request.urlopen('https://api.ipify.org').read().decode('utf8')
    return f"Bot is Live! IP: {ip}"

if __name__ == "__main__":
    bot_thread = threading.Thread(target=run_trading_bot)
    bot_thread.daemon = True
    bot_thread.start()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
