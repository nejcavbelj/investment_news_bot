import requests

HTTP_TIMEOUT = 12

def get_crowd_sentiment(symbol, max_items=100):
    try:
        url = f"https://api.stocktwits.com/api/2/streams/symbol/{symbol}.json"
        r = requests.get(url, timeout=HTTP_TIMEOUT)
        if not r.ok: return {"mentions": 0, "bull": 0, "bear": 0}
        msgs = r.json().get("messages", [])[:max_items]
        bull = bear = 0
        for m in msgs:
            s = (m.get("entities") or {}).get("sentiment") or {}
            if s.get("basic") == "Bullish": bull += 1
            if s.get("basic") == "Bearish": bear += 1
        return {"mentions": len(msgs), "bull": bull, "bear": bear}
    except Exception:
        return {"mentions": 0, "bull": 0, "bear": 0}