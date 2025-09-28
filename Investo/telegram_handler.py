from telegram import Update
from telegram.ext import Application, ContextTypes, MessageHandler, filters

async def message_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    startup_warnings,
    get_top_volume_tickers,
    get_most_mentioned_tickers,
    clean_tickers,
    get_stock_package,
    summarize_stocks,
    TOP_N_TRENDING=10
):
    text = (update.message.text or "").strip().upper()
    if not text: return

    # show warnings if any
    if startup_warnings:
        await update.message.reply_text("\n".join(startup_warnings))
        startup_warnings.clear()

    if text == "SUMMARY":
        volume = clean_tickers(get_top_volume_tickers(TOP_N_TRENDING))
        mentions = clean_tickers(get_most_mentioned_tickers(TOP_N_TRENDING))
        combined = list(dict.fromkeys(volume + mentions))

        if not combined:
            await update.message.reply_text("⚠ Could not find valid tickers right now. Try again later.")
            return

        pkgs = [get_stock_package(s) for s in combined]
        pkgs.sort(key=lambda x: (
            abs(x.get("pct_1d") if isinstance(x.get("pct_1d"), (int,float)) else 0),
            x.get("crowd", {}).get("mentions", 0)
        ), reverse=True)
        top5 = pkgs[:5]
        summary = summarize_stocks(top5, "Overall Market Summary", mode="summary")
        await update.message.reply_text(summary)
        return

    tickers = [t for t in text.split() if clean_tickers([t])]
    if not tickers:
        await update.message.reply_text("❌ No valid tickers found.")
        return

    for t in tickers:
        pkg = get_stock_package(t)
        summary = summarize_stocks([pkg], f"Analysis for {t}", mode="ticker")
        await update.message.reply_text(summary)

def start_bot(
    config,
    startup_warnings,
    get_stock_package,
    get_top_volume_tickers,
    get_most_mentioned_tickers,
    clean_tickers,
    summarize_stocks
):
    from telegram.request import HTTPXRequest

    request = HTTPXRequest(http_version="1.1")
    app = Application.builder().token(config["TELEGRAM_BOT_TOKEN"]).request(request).build()

    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        lambda update, context: message_handler(
            update, context, startup_warnings, get_top_volume_tickers,
            get_most_mentioned_tickers, clean_tickers,
            get_stock_package, summarize_stocks
        )
    ))
    print("Bot ready. Type 'SUMMARY' or a ticker like 'TSLA'.")
    app.run_polling()