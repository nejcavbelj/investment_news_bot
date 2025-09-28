import yfinance as yf

def get_stock_data_yf(symbol):
    data = {
        "symbol": symbol,
        "price": "N/A",
        "pct_1d": "N/A",
        "pct_5d": "N/A",
        "pct_1m": "N/A",
        "shortName": symbol,
        "summary": "",
    }
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        data["shortName"] = info.get("shortName", symbol)
        data["summary"] = (info.get("longBusinessSummary") or "")[:400]
        hist = ticker.history(period="1mo")
        if not hist.empty:
            closes = hist["Close"].tolist()
            last = float(closes[-1])
            prev = float(closes[-2]) if len(closes) > 1 else last
            week = float(closes[-6]) if len(closes) > 5 else closes[0]
            month = closes[0]
            pct = lambda a, b: round(((a - b) / b) * 100, 2) if b else "N/A"
            data["price"] = round(last, 2)
            data["pct_1d"] = pct(last, prev)
            data["pct_5d"] = pct(last, week)
            data["pct_1m"] = pct(last, month)
    except Exception:
        pass
    return data