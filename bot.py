def get_market_intelligence(self):
        """Fetch Order Book and Klines safely with wrapper handling"""
        try:
            # 1. Fetch Order Book Depth
            depth_res = requests.get(f"{BASE_URL}{DEPTH_ENDPOINT}?symbol={SYMBOL}&limit=10")
            res_json = depth_res.json()
            depth_data = res_json.get('data', res_json) if isinstance(res_json, dict) else {}
            
            bids = depth_data.get('bids', [])
            asks = depth_data.get('asks', [])
            
            bid_vol = sum([float(b[1]) for b in bids]) if bids else 0
            ask_vol = sum([float(a[1]) for a in asks]) if asks else 0
            
            # 2. Fetch Recent Volume (Klines)
            kline_res = requests.get(f"{BASE_URL}{KLINE_ENDPOINT}?symbol={SYMBOL}&interval=1m&limit=5")
            k_json = kline_res.json()
            klines = k_json.get('data', k_json) if isinstance(k_json, dict) else []
            
            current_price = float(klines[-1][4]) if klines and len(klines) > 0 else 81000.0
            
            if klines and len(klines) >= 5:
                avg_vol = sum([float(k[5]) for k in klines[:-1]]) / len(klines[:-1])
                current_vol = float(klines[-1][5])
            else:
                avg_vol, current_vol = 1.0, 1.0

            return current_price, bid_vol, ask_vol, avg_vol, current_vol

        except Exception as e:
            print(f"[{time.strftime('%I:%M:%S %p')}] ⚠️ Market Data Error (Retrying...): {str(e)}")
            return 0, 0, 0, 0, 0
