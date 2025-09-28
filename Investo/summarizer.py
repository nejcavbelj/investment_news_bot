import openai
from api.finnhub import get_global_news

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