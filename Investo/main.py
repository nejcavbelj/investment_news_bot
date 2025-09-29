from config import load_config, startup_warnings
from api.yahoo import get_top_volume_tickers, get_most_mentioned_tickers
from api.finnhub import set_api_key, get_company_news, get_global_news
from api.stocktwits import get_crowd_sentiment
from api.yfinance import get_stock_data_yf
from utils.tickers import clean_tickers
from summarizer import summarize_stocks
from telegram_handler import start_bot
from utils.token_persistence import load_token_data


def get_stock_package(symbol):
    d = get_stock_data_yf(symbol)
    d["news"] = get_company_news(symbol)
    d["crowd"] = get_crowd_sentiment(symbol)
    return d

def main():
    config = load_config()
    set_api_key(config['FINNHUB_API_KEY'])

    # Load tokens and budget from file
    tokens_used, primary_budget = load_token_data()

    start_bot(
        config, startup_warnings, get_stock_package,
        get_top_volume_tickers, get_most_mentioned_tickers,
        clean_tickers, summarize_stocks,
        tokens_used=tokens_used,
        primary_budget=primary_budget
    )

if __name__ == "__main__":
    main()