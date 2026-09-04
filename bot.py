import time
import requests

BASE_URL = 'https://api.sharkexchange.in'
DEPTH_ENDPOINT = '/v1/market/depth'
KLINE_ENDPOINT = '/v1/market/klines'
SYMBOL = "BTCUSDT"
TRADE_QTY = 0.025
PROFIT_TARGET = 5.0  
STOP_LOSS = -2.0     

class InstitutionalWhaleBot:
    def __init__(self):
        self.is_position_open = False
        self.position_side = None
        self.entry_price = 0.0

    def execute_real_trade(self, side, is_exit=False):
        # YAHAN TERA ASLI ORDER PLACE KARNE WALA API CODE AAYEGA
        # Abhi ke liye yeh print karega taaki logs mein entry dikhe
        print(f"[{time.strftime('%I:%M:%S %p')}] 🚀 EXECUTING {side} ORDER | Qty: {TRADE_QTY}", flush=True)
        return True

    def get_market_intelligence(self):
        try:
            depth_res = requests.get(f"{BASE_URL}{DEPTH_ENDPOINT}?symbol={SYMBOL}&limit=5", timeout=3)
            res_json = depth_res.json()
            
            bids, asks = [], []
            if isinstance(res_json, dict) and res_json.get("code", 0) == 0:
                depth_data = res_json.get('data', res_json)
                bids = depth_data.get('bids', [])
                asks = depth_data.get('asks', [])
            
            bid_vol = sum([float(b[1]) for b in bids]) if bids else 10.0
            ask_vol = sum([float(a[1]) for a in asks]) if asks else 10.0
            
            kline_res = requests.get(f"{BASE_URL}{KLINE_ENDPOINT}?symbol={SYMBOL}&interval=1m&limit=5", timeout=3)
            k_json = kline_res.json()
            
            klines = []
            if isinstance(k_json, dict) and k_json.get("code", 0) == 0:
                klines = k_json.get('data', [])
            elif isinstance(k_json, list):
                klines = k_json
            
            if klines and len(klines) > 0:
                current_price = float(klines[-1][4])
                current_vol = float(klines[-1][5])
                avg_vol = sum([float(k[5]) for k in klines[:-1]]) / max(len(klines[:-1]), 1)
            else:
                current_price = 81000.0
                current_vol, avg_vol = 1.0, 1.0

            return current_price, bid_vol, ask_vol, avg_vol, current_vol

        except Exception as e:
            print(f"[{time.strftime('%I:%M:%S %p')}] API Error: {str(e)}", flush=True)
            return 81000.0, 10.0, 10.0, 1.0, 1.0

    def run_strategy(self):
        print(f"[{time.strftime('%I:%M:%S %p')}] 🚀 DIAGNOSTIC BOT ACTIVE | QTY: {TRADE_QTY}", flush=True)
        
        while True:
            try:
                price, bid_vol, ask_vol, avg_vol, cur_vol = self.get_market_intelligence()
                
                print(f"[{time.strftime('%I:%M:%S %p')}] SCAN | Price: {price} | Bids: {bid_vol:.1f} | Asks: {ask_vol:.1f} | Vol: {cur_vol:.1f}", flush=True)

                if not self.is_position_open:
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
                    print(f"[{time.strftime('%I:%M:%S %p')}] ⏳ POSITION ACTIVE [{self.position_side}] | Entry: {self.entry_price} | PnL: ${pnl}", flush=True)
                    
                    exit_side = "SELL" if self.position_side == "BUY" else "BUY"
                    if pnl >= PROFIT_TARGET or pnl <= STOP_LOSS:
                        reason = "Target Hit" if pnl >= PROFIT_TARGET else "Stop Loss Hit"
                        print(f"[{time.strftime('%I:%M:%S %p')}] 🎯 Exiting ({reason}) | PnL: ${pnl}", flush=True)
                        if self.execute_real_trade(exit_side, is_exit=True):
                            self.is_position_open = False
                            self.position_side = None
                            self.entry_price = 0.0

            except Exception as e:
                print(f"[{time.strftime('%I:%M:%S %p')}] Loop Exception: {str(e)}", flush=True)
            
            time.sleep(3)

if __name__ == "__main__":
    bot = InstitutionalWhaleBot()
    bot.run_strategy()
