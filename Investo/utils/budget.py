from telegram import Bot

def send_budget_reminder(chat_id, bot_token, remaining_percent):
    bot = Bot(token=bot_token)
    message = f"Reminder: You only have {remaining_percent:.1f}% of your OpenAI token budget left!"
    bot.send_message(chat_id=chat_id, text=message)

    #This will send a notification EVERY TIME any message is received (for example, every time a ticker is inserted in chat) if the balance is below 10%.