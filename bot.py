import time
import logging

# Logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - INFO - %(message)s')

# Global Variables
active_trade = None  # Holds the details of currently open trade
ENTRY_QUANTITY = 21.0

def fetch_market_data():
    """
    Simulates fetching market indicators for SOL-USDT.
    Replace this with actual exchange API calls (e.g., Delta Exchange API).
    """
    # Example values for demonstration
    current_price = 77.25
    ema_200 = 75.00        # Long-term trend indicator
    macd_line = 1.25       # MACD Line
    signal_line = 0.85     # MACD Signal Line
    rsi = 55.0             # RSI Indicator
    return current_price, ema_200, macd_line, signal_line, rsi

def check_triple_confirmation(current_price, ema_200, macd_line, signal_line, rsi):
    """
    Triple Confirmation Strategy Logic:
    1. Trend Check: Price above 200 EMA (Uptrend)
    2. Momentum Check: MACD Line > Signal Line (Bullish Crossover)
    3. RSI Check: RSI between 50 and 65 (Healthy Strength, Not Overbought)
    """
    cond1_trend = current_price > ema_200
    cond2_macd = macd_line > signal_line
    cond3_rsi = 50 <= rsi <= 65

    if cond1_trend and cond2_macd and cond3_rsi:
        return True
    return False

def manage_active_trade(current_price):
    """
    Manages active position with SL, Target, and Trailing Stop Loss (TSL).
    """
    global active_trade
    if not active_trade:
        return

    entry_price = active_trade['entry_price']
    sl = active_trade['sl']
    target = active_trade['target']
    highest_price = active_trade['highest_price']

    # Update highest price for Trailing Stop Loss
    if current_price > highest_price:
        active_trade['highest_price'] = current_price
        # Trail Stop Loss upwards (e.g., maintain 1.5% gap below peak price)
        new_tsl = current_price * 0.985
        if new_tsl > active_trade['sl']:
            active_trade['sl'] = new_tsl
            logging.info(f"Trailing SL updated to: {active_trade['sl']:.2f}")

    # Check Exit Conditions
    if current_price <= active_trade['sl']:
        logging.info(f"Stop Loss / Trailing SL Hit! Closing Trade at: {current_price}")
        active_trade = None  # Trade closed, slot free for next trade
    elif current_price >= target:
        logging.info(f"Target Profit Reached! Closing Trade at: {current_price}")
        active_trade = None  # Trade closed, slot free for next trade

def run_trading_bot():
    global active_trade
    logging.info("Triple Confirmation Trading Bot Started...")

    while True:
        try:
            current_price, ema_200, macd_line, signal_line, rsi = fetch_market_data()
            logging.info(f"Scanning SOL-USDT | Price: {current_price} | RSI: {rsi}")

            # Strict Rule: Only 1 Trade Active at a Time
            if active_trade is not None:
                logging.info("Position active. Monitoring SL / TSL / Target...")
                manage_active_trade(current_price)
            else:
                # Check for Triple Confirmation Signal
                if check_triple_confirmation(current_price, ema_200, macd_line, signal_line, rsi):
                    logging.info("TRIPLE CONFIRMATION SIGNAL DETECTED! Opening Buy Order.")
                    
                    # Set initial SL (1.5%), Target (3%), and Peak Price Tracker
                    active_trade = {
                        'entry_price': current_price,
                        'quantity': ENTRY_QUANTITY,
                        'sl': current_price * 0.985,
                        'target': current_price * 1.03,
                        'highest_price': current_price
                    }
                    logging.info(f"Trade Executed: {active_trade}")
                else:
                    logging.info("Triple confirmation conditions not met. Holding...")

            time.sleep(30)

        except Exception as e:
            logging.error(f"Error in bot loop: {e}")
            time.sleep(10)

if __name__ == "__main__":
    run_trading_bot()
