import openai
from api.finnhub import get_global_news
from utils.token_persistence import save_token_data

def summarize_stocks(data_list, title, mode="summary", context=None):
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
        summary = resp.choices[0].message.content.strip()

        # --- Track tokens used and persist ---
        if context is not None and hasattr(resp, "usage"):
            tokens_used = getattr(resp.usage, "total_tokens", 0)
            context.bot_data["tokens_used"] = context.bot_data.get("tokens_used", 0) + tokens_used
            save_token_data(
                context.bot_data["tokens_used"],
                context.bot_data.get("primary_budget", 1000)
            )

        return summary

    except Exception as e:
        return f"AI summary failed: {e}"