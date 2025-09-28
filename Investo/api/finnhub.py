import requests
from datetime import datetime, timedelta

FINNHUB_API_KEY = None
HTTP_TIMEOUT = 12

def set_api_key(key):
    global FINNHUB_API_KEY
    FINNHUB_API_KEY = key

def finnhub_get(path, params):
    if not FINNHUB_API_KEY:
        return None
    try:
        url = f"https://finnhub.io/api/v1/{path}"
        p = dict(params or {})
        p["token"] = FINNHUB_API_KEY
        r = requests.get(url, params=p, timeout=HTTP_TIMEOUT)
        if r.ok:
            return r.json()
    except Exception:
        return None
    return None

def get_company_news(symbol, days=7, max_items=5):
    end = datetime.now().date()
    start = end - timedelta(days=days)
    js = finnhub_get("company-news", {"symbol": symbol, "from": str(start), "to": str(end)})
    if not js: return []
    seen = set()
    out = []
    for item in sorted(js, key=lambda x: x.get("datetime", 0), reverse=True):
        h = item.get("headline", "").strip()
        if not h or h in seen: continue
        seen.add(h)
        out.append(h[:150])
        if len(out) >= max_items: break
    return out

def get_global_news(max_items=6):
    js = finnhub_get("news", {"category": "general"})
    if not js: return []
    seen, out = set(), []
    for item in js:
        h = item.get("headline", "").strip()
        if not h or h in seen: continue
        seen.add(h)
        out.append(h[:150])
        if len(out) >= max_items: break
    return out