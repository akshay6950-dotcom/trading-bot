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
        target_symbol = 'SOLUSDT' 
        
        try:
            bars = exchange.fetch_ohlcv(target_symbol, timeframe='15m', limit=250)
        except Exception as api_error:
            bars = []

        if not bars or len(bars) == 0:
            logging.error(f"Exchange ne {target_symbol} ke liye koi data nahi bheja!")
            return None, None, None, None, None, None

        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # Calculate Indicators (EMA, MACD, RSI, Bollinger Bands)
        df.ta.ema(length=50, append=True)
        df.ta.ema(length=200, append=True)
        df.ta.macd(fast=12, slow=26, signal=9, append=True)
        df.ta.rsi(length=14, append=True)
        df.ta.bbands(length=20, std=2, append=True)

        latest = df.iloc[-1]
        
        current_price = float(latest['close'])
        ema_50 = float(latest['EMA_50'])
        ema_200 = float(latest['EMA_200'])
        macd_line = float(latest['MACD_12_26_9'])
        signal_line = float(latest['MACDs_12_26_9'])
        rsi = float(latest['RSI_14'])
        
        return current_price, ema_50, ema_200, macd_line, signal_line, rsi
    except Exception as e:
        logging.error(f"Data fetch error: {e}")
        return None, None, None, None, None, None

# --- MULTIPLE HIGH-ACCURACY STRATEGIES ---
def check_strategies(price, ema_50, ema_200, macd_line, signal_line, rsi):
    """Inme se koi bhi ek strategy pehle match hogi toh trade mil jayegi."""
    
    # Strategy 1: Trend & Momentum Crossover (EMA 50 > 200 + MACD Bullish + RSI healthy)
    strat_1 = (price > ema_50) and (ema_50 > ema_200) and (macd_line > signal_line) and (45 <= rsi <= 70)
    
    # Strategy 2: Strong RSI Bounce (RSI oversold se recover ho raha ho aur MACD upar ho)
    strat_2 = (rsi < 40) and (macd_line > signal_line) and (price > ema_200)
    
    # Strategy 3: Quick Scalp Momentum (Fast MACD crossover with decent RSI)
    strat_3 = (macd_line > signal_line) and (50 <= rsi <= 75) and (price > ema_50)

    if strat_1:
        return "Strategy 1 (Trend & Momentum)"
    elif strat_2:
        return "Strategy 2 (RSI Dip Recovery)"
    elif strat_3:
        return "Strategy 3 (Quick Scalp Momentum)"
    
    return None

def manage_active_trade(current_price):
    global active_trade
    if not active_trade: return

    target = active_trade['target']
    
    if current_price > active_trade['highest_price']:
        active_trade['highest_price'] = current_price
        new_tsl = current_price * 0.985  # 1.5% Trailing Stop Loss
        if new_tsl > active_trade['sl']:
            active_trade['sl'] = new_tsl
            logging.info(f"TSL updated to: {active_trade['sl']:.2f}")

    if current_price <= active_trade['sl']:
        logging.info(f"SL/TSL Hit! Trade Closed at: {current_price}")
        active_trade = None  # Lock khul gaya, ab doosri trade lee ja sakegi
    elif current_price >= target:
        logging.info(f"Target Hit! Trade Closed at: {current_price}")
        active_trade = None  # Lock khul gaya

def run_trading_bot():
    global active_trade
    logging.info("Multi-Strategy Trading Bot Started...")

    while True:
        try:
            price, ema_50, ema_200, macd, signal, rsi = fetch_market_data()
            if price is None:
                time.sleep(10)
                continue
                
            logging.info(f"SCAN - Price: {price:.2f} | RSI: {rsi:.2f} | Active Trade: {active_trade is not None}")

            # Rule: Jab tak active trade chal rahi hai, doosri entry nahi hogi
            if active_trade is not None:
                manage_active_trade(price)
            else:
                matched_strategy = check_strategies(price, ema_50, ema_200, macd, signal, rsi)
                
                if matched_strategy:
                    logging.info(f"SIGNAL MATCHED via {matched_strategy}! Opening Trade...")
                    
                    active_trade = {
                        'strategy': matched_strategy,
                        'entry_price': price,
                        'quantity': ENTRY_QUANTITY,
                        'sl': price * 0.985,      # 1.5% Initial Stop Loss
                        'target': price * 1.03,   # 3% Target
                        'highest_price': price
                    }
                    logging.info(f"Trade Executed: {active_trade}")

            time.sleep(30)
        except Exception as e:
            logging.error(f"Bot loop error: {e}")
            time.sleep(10)

app = Flask(__name__)
@app.route('/')
def keep_alive():
    return "Multi-Strategy Trading Bot is Live!"

if __name__ == "__main__":
    bot_thread = threading.Thread(target=run_trading_bot)
    bot_thread.daemon = True
    bot_thread.start()
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
