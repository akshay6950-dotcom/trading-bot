import time
import requests
import numpy as np
from datetime import datetime

# ==========================================
# CONFIGURATION & PARAMETERS
# ==========================================
SYMBOLS = [
    'BTC-USDT',
    'ETH-USDT',
    'SOL-USDT',
    'XAU-USDT',  # Gold
    'PAXG-USDT'  # Gold Alternative
]

# Updated Position Quantities as per requested ratio
POSITION_SIZES = {
    'BTC-USDT': 0.035,
    'ETH-USDT': 50.0,
    'SOL-USDT': 10.0,
    'XAU-USDT': 0.5,
    'PAXG-USDT': 0.5
}

LEVERAGE = 5  # Fixed 5x Margin
CHECK_INTERVAL = 15  # Scan every 15 seconds

price_history = {symbol: [] for symbol in SYMBOLS}
active_trades = {symbol: False for symbol in SYMBOLS}

# ==========================================
# TECHNICAL INDICATORS
# ==========================================
def calculate_ema(prices, period):
    if len(prices) < period:
        return None
    weights = np.exp(np.linspace(-1., 0., period))
    weights /= weights.sum()
    return float(np.convolve(prices, weights, mode='full')[:len(prices)][-1])

def calculate_rsi(prices, period=14):
    if len(prices) < period + 1:
        return 50
    deltas = np.diff(prices)
    seed = deltas[:period+1]
    up = seed[seed >= 0].sum()/period
    down = -seed[seed < 0].sum()/period
    if down == 0:
        return 100
    rs = up/down
    return float(100 - (100 / (1 + rs)))

def calculate_bollinger_bands(prices, period=20):
    if len(prices) < period:
        return None, None
    sma = np.mean(prices[-period:])
    std = np.std(prices[-period:])
    upper = sma + (2 * std)
    lower = sma - (2 * std)
    return float(upper), float(lower)

# ==========================================
# FETCH PRICE & EXECUTE
# ==========================================
def fetch_ticker_price(symbol):
    try:
        clean_symbol = symbol.replace('-', '')
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={clean_symbol}"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return float(response.json()['price'])
        
        if 'SOL' in symbol:
            res = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd", timeout=5).json()
            return float(res['solana']['usd'])
        return None
    except Exception:
        return None

def execute_trade(symbol, side, price, reason):
    qty = POSITION_SIZES.get(symbol, 0.01)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🚀 SIGNAL TRIGGERED ({reason}) | {symbol} | Side: {side} | Qty: {qty} | Margin: {LEVERAGE}x | Price: {price}")
    active_trades[symbol] = True

# ==========================================
# MULTI-STRATEGY ENGINE
# ==========================================
def analyze_market_and_trade(symbol, current_price):
    history = price_history[symbol]
    history.append(current_price)
    
    if len(history) > 50:
        history.pop(0)

    if len(history) < 10:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] [{symbol}] Price: {current_price} | Building Indicator Data ({len(history)}/10)...")
        return

    ema_fast = calculate_ema(history, 5)
    ema_slow = calculate_ema(history, 10)
    rsi = calculate_rsi(history, 14)
    upper_bb, lower_bb = calculate_bollinger_bands(history, 15)

    print(f"[{datetime.now().strftime('%H:%M:%S')}] [{symbol}] Price: {current_price} | RSI: {round(rsi,1)} | Fast EMA: {round(ema_fast,1) if ema_fast else 'N/A'}")

    # Strategy Triggers
    if rsi < 35:
        execute_trade(symbol, 'BUY', current_price, 'RSI Oversold Breakout')
        return
    elif rsi > 65:
        execute_trade(symbol, 'SELL', current_price, 'RSI Overbought Breakout')
        return

    if ema_fast and ema_slow:
        if ema_fast > ema_slow and history[-2] <= ema_slow:
            execute_trade(symbol, 'BUY', current_price, 'EMA Golden Cross')
            return
        elif ema_fast < ema_slow and history[-2] >= ema_slow:
            execute_trade(symbol, 'SELL', current_price, 'EMA Death Cross')
            return

    if upper_bb and lower_bb:
        if current_price < lower_bb:
            execute_trade(symbol, 'BUY', current_price, 'Bollinger Lower Band Rebound')
            return
        elif current_price > upper_bb:
            execute_trade(symbol, 'SELL', current_price, 'Bollinger Upper Band Rejection')
            return

# ==========================================
# MAIN LOOP
# ==========================================
def main():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] High-Frequency Engine Active (5x Leverage & Updated Lot Sizes)...")
    
    while True:
        for symbol in SYMBOLS:
            price = fetch_ticker_price(symbol)
            if price is not None:
                analyze_market_and_trade(symbol, price)
            else:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] [{symbol}] Price: Retrying stream...")
        
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
