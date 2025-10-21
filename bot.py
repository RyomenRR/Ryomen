from pyrogram import Client, filters
import json, os

# ================= CONFIG FROM ENVIRONMENT =================
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
CHANNEL_ID = int(os.environ.get("CHANNEL_ID", 0))

apk_data = {}

# ================= CREATE CLIENT =================
app = Client(
    "apk_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# Load previous APK data if exists
if os.path.exists("apk_data.json"):
    with open("apk_data.json", "r") as f:
        apk_data.update(json.load(f))


# ================= CHANNEL HANDLER =================
@app.on_message(filters.channel & filters.document)
def save_apk(client, message):
    msg_id = getattr(message, "id", None)
    if msg_id is None:
        print("⚠️ Could not read message ID.")
        return

    name = message.document.file_name

    # Only save APKs
    if not name.lower().endswith(".apk"):
        print(f"⏩ Ignored non-APK: {name}")
        return

    apk_data[name] = msg_id

    with open("apk_data.json", "w") as f:
        json.dump(apk_data, f, indent=2)

    print(f"✅ Saved: {name} → {msg_id}")


# ================= GROUP HANDLER =================
@app.on_message(filters.group)
def reply_apk(client, message):
    if not message.text:
        return

    text = message.text.strip().lower()

    # Download or 下载 = send last APK
    if text in ["download", "下载"]:
        if apk_data:
            last_name = list(apk_data.keys())[-1]
            last_id = apk_data[last_name]
            try:
                client.copy_message(
                    chat_id=message.chat.id,
                    from_chat_id=CHANNEL_ID,
                    message_id=last_id
                )
                print(f"📤 Sent last APK: {last_name}")
            except Exception as e:
                print(f"❌ Failed to send last APK: {e}")
        else:
            message.reply_text("No APKs saved yet!")
        return

    # Match by app name
    for name, msg_id in apk_data.items():
        base_name = name.lower().replace(".apk", "")
        if base_name in text:
            try:
                client.copy_message(
                    chat_id=message.chat.id,
                    from_chat_id=CHANNEL_ID,
                    message_id=msg_id
                )
                print(f"📤 Sent matched APK: {name}")
                return
            except Exception as e:
                print(f"❌ Failed to send {name}: {e}")

    print(f"ℹ️ No match for: {text}")


print("🤖 Bot is running on Render...")
app.run()
