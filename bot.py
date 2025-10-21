import os
from pyrogram import Client, filters
from pyrogram.types import Message

# --- ENV VARIABLES ---
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_USERNAME = os.environ.get("CHANNEL_USERNAME")  # your private channel username or ID

# --- START CLIENT ---
app = Client(
    "apk_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# --- HELPER: fetch all APKs from channel ---
async def get_channel_apks():
    apk_messages = []
    async for msg in app.get_chat_history(CHANNEL_USERNAME):
        # only messages with documents ending with .apk
        if msg.document and msg.document.file_name.lower().endswith(".apk"):
            apk_messages.append(msg)
    return apk_messages

# --- HELPER: find latest APK ---
def latest_apk(apk_messages):
    if not apk_messages:
        return None
    # last uploaded APK considered latest
    return apk_messages[-1]

# --- MESSAGE HANDLER ---
@app.on_message(filters.group)
async def handle_messages(client: Client, message: Message):
    text = message.text
    if not text:
        return

    text_lower = text.lower().strip()

    # respond to download or 下载
    if text_lower in ["download", "下载"]:
        apks = await get_channel_apks()
        latest_msg = latest_apk(apks)
        if latest_msg:
            await latest_msg.copy(chat_id=message.chat.id)
        else:
            await message.reply_text("No APKs found in channel.")
        return

    # respond to APK name mentions
    apks = await get_channel_apks()
    for apk_msg in apks:
        if apk_msg.document:
            name = apk_msg.document.file_name.lower().replace(" ", "")
            msg_text = text_lower.replace(" ", "")
            if msg_text in name:
                await apk_msg.copy(chat_id=message.chat.id)
                return

# --- START BOT ---
print("✅ APK Bot started!")
app.run()
