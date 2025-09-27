import os
import re
import time
import requests
import yfinance as yf
from bs4 import BeautifulSoup
from collections import Counter
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from pathlib import Path

import openai
from telegram import Update
from telegram.ext import Application, ContextTypes, MessageHandler, filters

# ----------------------
# Load .env config
# ----------------------
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

openai.api_key = os.getenv("OPENAI_API_KEY")
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT")

# ----------------------
# Config
# ----------------------
TOP_N_TRENDING = 10   # we rank then pick top 5
HTTP_TIMEOUT = 12

HEADERS = {"User-Agent": "Mozilla/5.0 (InvestmentBot/1.0)"}
startup_warnings = []

# ----------------------
# API Key Check
# ----------------------
def check_keys():
    if not openai.api_key:
        startup_warnings.append("❌ Missing OPENAI_API_KEY")
    if not TOKEN:
        startup_warnings.append("❌ Missing TELEGRAM_BOT_TOKEN")
    if not CHAT_ID:
        startup_warnings.append("⚠️ Missing TELEGRAM_CHAT_ID (bot may run but not auto-send)")
    if not FINNHUB_API_KEY:
        startup_warnings.append("⚠️ Missing FINNHUB_API_KEY (no news/insiders/sentiment)")
    if not (REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET and REDDIT_USER_AGENT):
        startup_warnings.append("ℹ️ Reddit API not configured → will fallback to StockTwits")

check_keys()

# ----------------------
# Yahoo Finance Trending / Most Active
# ----------------------
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

# ----------------------
# yfinance: prices + fundamentals
# ----------------------
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

# ----------------------
# Finnhub helpers
# ----------------------
def finnhub_get(path, params):
    if not FINNHUB_API_KEY:
        return None
    try:
        url = f"https://finnhub.io/api/v1/{path}"
        p = dict(params or {})
        p["token"] = FINNHUB_API_KEY
        r = requests.get(url, params=p, timeout=HTTP_TIMEOUT)
        if r.status_code == 401:
            startup_warnings.append(f"❌ Finnhub key invalid for {path}")
            return None
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

# ----------------------
# StockTwits sentiment fallback
# ----------------------
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

# ----------------------
# Build stock package
# ----------------------
def get_stock_package(symbol):
    d = get_stock_data_yf(symbol)
    d["news"] = get_company_news(symbol)
    d["crowd"] = get_crowd_sentiment(symbol)
    return d

# ----------------------
# AI Summarization
# ----------------------
def summarize_stocks(data_list, title, mode="summary"):
    if mode == "ticker":
        max_tokens = 300
        per_stock = "Use up to 300 tokens total for this single stock."
    else:
        max_tokens = 600
        per_stock = (
            "For summary: analyze 5 best tickers with ~100 tokens each, "
            "then finish with ~100 tokens global news wrap."
        )

    prompt = (
        f"{title}\n\n"
        "Investor profile: Interested in both short-term trades (days/weeks) and "
        "long-term investments. Medium-high risk tolerance.\n\n"
        "Instructions:\n"
        "- Provide concise but informative analysis.\n"
        "- Avoid duplication.\n"
        "- Prioritize items with higher frequency/mentions.\n"
        f"- {per_stock}\n\n"
        "### Data:\n"
    )

    for d in data_list:
        crowd = d.get("crowd", {})
        news = d.get("news", [])
        prompt += (
            f"- {d['shortName']} ({d['symbol']}): Price {d['price']}, "
            f"1d {d['pct_1d']}%, 5d {d['pct_5d']}%, 1m {d['pct_1m']}%\n"
            f"  Crowd sentiment: mentions={crowd.get('mentions')}, "
            f"bull={crowd.get('bull')}, bear={crowd.get('bear')}\n"
            f"  News: " + "; ".join(news if news else ["No major news"]) + "\n"
        )

    if mode == "summary":
        global_news = get_global_news()
        prompt += "\n### Global Market News:\n" + "; ".join(global_news)

    try:
        resp = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6,
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"AI summary failed: {e}"

# ----------------------
# Telegram Handler
# ----------------------
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip().upper()
    if not text: return

    # show warnings if any
    if startup_warnings:
        await update.message.reply_text("\n".join(startup_warnings))
        startup_warnings.clear()

    if text == "SUMMARY":
        volume = get_top_volume_tickers(TOP_N_TRENDING)
        mentions = get_most_mentioned_tickers(TOP_N_TRENDING)
        combined = list(dict.fromkeys(volume + mentions))
        # Rank: big moves or many mentions
        pkgs = [get_stock_package(s) for s in combined]
        pkgs.sort(key=lambda x: (
            abs(x.get("pct_1d") if isinstance(x.get("pct_1d"), (int,float)) else 0),
            x.get("crowd", {}).get("mentions", 0)
        ), reverse=True)
        top5 = pkgs[:5]
        summary = summarize_stocks(top5, "Overall Market Summary", mode="summary")
        await update.message.reply_text(summary)
        return

    # Otherwise treat as ticker(s)
    tickers = re.findall(r"\b[A-Z]{1,10}\b", text)
    if not tickers:
        await update.message.reply_text("❌ No valid tickers found.")
        return

    for t in tickers:
        pkg = get_stock_package(t)
        summary = summarize_stocks([pkg], f"Analysis for {t}", mode="ticker")
        await update.message.reply_text(summary)

# ----------------------
# Run Bot
# ----------------------
def main():
    from telegram.request import HTTPXRequest

    request = HTTPXRequest(http_version="1.1")  # force HTTP/1.1
    app = Application.builder().token(TOKEN).request(request).build()

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    print("Bot ready. Type 'SUMMARY' or a ticker like 'TSLA'.")
    app.run_polling()

if __name__ == "__main__":
    main()
