import time
import logging
import threading
import os
from flask import Flask
import ccxt
import pandas as pd
import pandas_ta as ta

# Logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - INFO - %(message)s')

active_trade = None  
ENTRY_QUANTITY = 21.0

# --- API KEYS ---
API_KEY = 'b450a76a2cf0724b0e2dddd69cd7675a' 
API_SECRET = 'c8e6ef153aefea2dda2b36c0b3fad153'

# Connect to Exchange 
try:
    exchange = ccxt.delta({
        'apiKey': API_KEY,
        'secret': API_SECRET,
        'enableRateLimit': True,
    })
    logging.info("Exchange API Connected Successfully!")
except Exception as e:
    logging.error(f"Exchange connection error: {e}")

def fetch_market_data():
    """Fetches LIVE data and calculates indicators."""
    try:
        # SOL/USDT ka 15-minute timeframe ka real data fetch kar rahe hain
        bars = exchange.fetch_ohlcv('SOL/USDT', timeframe='15m', limit=250)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # Calculate Indicators (EMA, MACD, RSI) dynamically
        df.ta.ema(length=200, append=True)
        df.ta.macd(fast=12, slow=26, signal=9, append=True)
        df.ta.rsi(length=14, append=True)

        latest = df.iloc[-1]
        
        current_price = float(latest['close'])
        ema_200 = float(latest['EMA_200'])
        macd_line = float(latest['MACD_12_26_9'])
        signal_line = float(latest['MACDs_12_26_9'])
        rsi = float(latest['RSI_14'])
        
        return current_price, ema_200, macd_line, signal_line, rsi
    except Exception as e:
        logging.error(f"Data fetch error: {e}")
        return None, None, None, None, None

def check_triple_confirmation(current_price, ema_200, macd_line, signal_line, rsi):
    cond1 = current_price > ema_200
    cond2 = macd_line > signal_line
    cond3 = 50 <= rsi <= 65
    return cond1 and cond2 and cond3

def manage_active_trade(current_price):
    global active_trade
    if not active_trade: return

    target = active_trade['target']
    
    if current_price > active_trade['highest_price']:
        active_trade['highest_price'] = current_price
        new_tsl = current_price * 0.985
        if new_tsl > active_trade['sl']:
            active_trade['sl'] = new_tsl
            logging.info(f"TSL up to: {active_trade['sl']:.2f}")

    if current_price <= active_trade['sl']:
        logging.info(f"SL/TSL Hit! Close at: {current_price}")
        active_trade = None  
    elif current_price >= target:
        logging.info(f"Target Hit! Close at: {current_price}")
        active_trade = None  

def run_trading_bot():
    global active_trade
    logging.info("Live Market Bot Started...")

    while True:
        try:
            price, ema, macd, signal, rsi = fetch_market_data()
            if price is None:
                time.sleep(10)
                continue
                
            logging.info(f"LIVE SCAN - Price: {price:.2f} | RSI: {rsi:.2f} | 200 EMA: {ema:.2f}")

            if active_trade is not None:
                manage_active_trade(price)
            else:
                if check_triple_confirmation(price, ema, macd, signal, rsi):
                    logging.info("LIVE SIGNAL DETECTED! Placing Buy Order...")
                    
                    active_trade = {
                        'entry_price': price,
                        'quantity': ENTRY_QUANTITY,
                        'sl': price * 0.985,
                        'target': price * 1.03,
                        'highest_price': price
                    }
                    logging.info(f"Trade Live: {active_trade}")

            time.sleep(30)
        except Exception as e:
            time.sleep(10)

app = Flask(__name__)
@app.route('/')
def keep_alive():
    return "Real API Trading Bot is Live!"

if __name__ == "__main__":
    bot_thread = threading.Thread(target=run_trading_bot)
    bot_thread.daemon = True
    bot_thread.start()
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
