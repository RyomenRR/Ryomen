import os
from pyrogram import Client

# Read from Railway environment variables
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
SESSION_NAME = os.environ.get("SESSION_NAME", "bot")

app = Client(
    SESSION_NAME,
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

@app.on_message()
def echo(client, message):
    message.reply_text(f"Hello! You sent: {message.text}")

if __name__ == "__main__":
    # Start bot
    app.run()
