import re

def is_valid_ticker(ticker: str) -> bool:
    return bool(re.fullmatch(r"[A-Z]{1,5}", ticker)) and ticker not in {"CEO", "ETF", "US", "I"}

def clean_tickers(tickers):
    return [t for t in tickers if is_valid_ticker(t)]