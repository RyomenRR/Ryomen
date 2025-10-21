from pyrogram import Client, filters

# ---- CONFIG ----
API_ID = int("YOUR_API_ID")
API_HASH = "YOUR_API_HASH"
BOT_TOKEN = "YOUR_BOT_TOKEN"
APK_CHANNEL = "@your_channel_username"  # channel where APKs are stored

app = Client("apk_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Helper: get latest APK message
async def get_latest_apk():
    async for message in app.get_chat_history(APK_CHANNEL, limit=100):
        if message.document and message.document.file_name.endswith(".apk"):
            return message
    return None

# Helper: find APK by name
async def get_apk_by_name(keyword):
    keyword = keyword.lower()
    async for message in app.get_chat_history(APK_CHANNEL, limit=100):
        if message.document and keyword in message.document.file_name.lower():
            return message
    return None

# Listen to all messages in groups
@app.on_message(filters.group)
async def respond(client, message):
    text = message.text
    if not text:
        return

    # Trigger: download or 下载
    if text.lower() in ["download", "下载"]:
        apk_msg = await get_latest_apk()
        if apk_msg:
            await apk_msg.forward(message.chat.id)
        else:
            await message.reply_text("No APKs found in channel.")

    # Trigger: keyword (Alpha/Beta)
    else:
        apk_msg = await get_apk_by_name(text)
        if apk_msg:
            await apk_msg.forward(message.chat.id)

# Run the bot
app.run()
