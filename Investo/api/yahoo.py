import requests
import re
from bs4 import BeautifulSoup
from collections import Counter

HEADERS = {"User-Agent": "Mozilla/5.0 (InvestmentBot/1.0)"}
HTTP_TIMEOUT = 12

def get_top_volume_tickers(count=5):
    url = "https://finance.yahoo.com/most-active"
    try:
        r = requests.get(url, headers=HEADERS, timeout=HTTP_TIMEOUT)
        soup = BeautifulSoup(r.text, "html.parser")
        tickers = []
        table = soup.find("table")
        if table:
            rows = table.find_all("tr")[1:]
            for row in rows[: count * 4]:
                tds = row.find_all("td")
                if len(tds) > 0:
                    t = tds[0].text.strip()
                    if t and re.fullmatch(r"[A-Z.\-]{1,10}", t):
                        tickers.append(t)
        return list(dict.fromkeys(tickers))[:count]
    except Exception:
        return []

def get_most_mentioned_tickers(count=5):
    url = "https://finance.yahoo.com/"
    try:
        r = requests.get(url, headers=HEADERS, timeout=HTTP_TIMEOUT)
        soup = BeautifulSoup(r.text, "html.parser")
        headlines = [h.get_text(" ", strip=True) for h in soup.find_all(["h2", "h3", "a"])]
        candidates = re.findall(r"\b[A-Z]{1,5}\b", " ".join(headlines))
        counter = Counter(candidates)
        tickers = [t for t, _ in counter.most_common(count * 6)]
        return list(dict.fromkeys(tickers))[:count]
    except Exception:
        return []