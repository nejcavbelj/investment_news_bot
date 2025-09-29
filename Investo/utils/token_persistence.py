import json
import os

DATA_PATH = os.path.expanduser("~/investment_news_bot/token_data.json")

def load_token_data():
    if os.path.exists(DATA_PATH):
        with open(DATA_PATH, "r") as f:
            try:
                data = json.load(f)
                return data.get("tokens_used", 0), data.get("primary_budget", 1000)
            except Exception:
                return 0, 1000
    return 0, 1000

def save_token_data(tokens_used, primary_budget):
    with open(DATA_PATH, "w") as f:
        json.dump({
            "tokens_used": tokens_used,
            "primary_budget": primary_budget
        }, f)

def load_primary_budget():
    if os.path.exists(DATA_PATH):
        with open(DATA_PATH, "r") as f:
            try:
                data = json.load(f)
                return data.get("primary_budget", 1000)
            except Exception:
                return 1000
    return 1000