import os
import json
import logging
from pyrogram import Client, filters
from pyrogram.types import Message
# Import ChatType for filtering groups and supergroups correctly
from pyrogram.enums import ChatType 
from tqdm import tqdm 

# --- Configuration and Setup ---

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Environment variables
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0)) # Must be an integer
APK_CHANNEL = os.getenv("APK_CHANNEL")

# File to store APK metadata persistently
APK_CACHE_FILE = 'apks.json'
APK_FILES = {} # Global cache for APK files: {filename_key: {file_id: str, original_name: str}}

# Trigger keywords (case-insensitive matching)
TRIGGER_KEYWORDS = ["download", "下载", "send file", "get apk"]


def load_apks():
    """Loads APK data from the JSON cache file."""
    global APK_FILES
    if os.path.exists(APK_CACHE_FILE):
        with open(APK_CACHE_FILE, 'r', encoding='utf-8') as f:
            try:
                APK_FILES = json.load(f)
                logger.info(f"Loaded {len(APK_FILES)} APK entries from cache.")
            except json.JSONDecodeError:
                logger.error("Error decoding JSON from cache file. Starting with empty cache.")
                APK_FILES = {}
    else:
        logger.info("APK cache file not found. Starting with empty cache.")

def save_apks():
    """Saves APK data to the JSON cache file."""
    with open(APK_CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(APK_FILES, f, indent=4, ensure_ascii=False)
        logger.info(f"Saved {len(APK_FILES)} APK entries to cache.")

def get_file_key(file_name: str) -> str:
    """Creates a clean, searchable key from the original file name."""
    # Example: 'My_App-v1.2.3.apk' -> 'my-app-v1-2-3'
    return file_name.lower().replace('.apk', '').replace('.', '-').replace('_', '-').strip()

# Initialize the cache before starting
load_apks()

# Initialize the Pyrogram Bot Client
if not all([API_ID, API_HASH, BOT_TOKEN, ADMIN_ID, APK_CHANNEL]):
    logger.error("One or more required environment variables are missing (API_ID, API_HASH, BOT_TOKEN, ADMIN_ID, APK_CHANNEL).")
    exit()

# The name 'apk_bot' is required for session file persistence on Railway
app = Client(
    "apk_bot", 
    api_id=API_ID, 
    api_hash=API_HASH, 
    bot_token=BOT_TOKEN
)


# --- Admin Command Handlers ---

# Use filters.chat_type(ChatType.PRIVATE) for consistency
@app.on_message(filters.command("scan_apks") & filters.chat_type(ChatType.PRIVATE))
async def scan_apks_command(client: Client, message: Message):
    """Admin command to scan the public channel for new APK files and store their IDs."""
    if message.from_user.id != ADMIN_ID:
        await message.reply_text("🚫 Access Denied. Only the bot admin can run this command.")
        return

    if not APK_CHANNEL:
        await message.reply_text("❌ Error: APK_CHANNEL environment variable is not set.")
        return

    initial_message = await message.reply_text(f"🔍 Starting scan of channel `{APK_CHANNEL}`. This may take a while for large channels...")
    
    new_files_count = 0
    total_scanned = 0
    
    try:
        # Use Pyrogram's get_chat_history iterator
        async for msg in client.get_chat_history(APK_CHANNEL):
            total_scanned += 1
            
            if msg.document and msg.document.file_name and msg.document.file_name.lower().endswith('.apk'):
                file_name = msg.document.file_name
                file_id = msg.document.file_id
                name_key = get_file_key(file_name)
                
                if name_key not in APK_FILES:
                    APK_FILES[name_key] = {
                        'file_id': file_id,
                        'original_name': file_name,
                        # Store common substrings for matching
                        'match_terms': [name_key] + [part for part in name_key.split('-') if len(part) > 2]
                    }
                    new_files_count += 1
                    
        save_apks()

        await initial_message.edit_text(
            f"✅ **Scan Complete!**\n"
            f"Total messages scanned: **{total_scanned}**\n"
            f"New APKs found and cached: **{new_files_count}**\n"
            f"Total files in cache: **{len(APK_FILES)}**\n\n"
            f"Use `/list_apks` to see the keys."
        )

    except Exception as e:
        logger.error(f"Error during channel scan: {e}")
        await initial_message.edit_text(f"❌ An error occurred during the scan: `{e}`. Ensure the bot is an admin in the channel.")


@app.on_message(filters.command("list_apks") & filters.chat_type(ChatType.PRIVATE))
async def list_apks_command(client: Client, message: Message):
    """Lists the currently cached APKs."""
    if message.from_user.id != ADMIN_ID:
        await message.reply_text("🚫 Access Denied. Only the bot admin can run this command.")
        return
        
    if not APK_FILES:
        await message.reply_text("The APK cache is currently empty. Run `/scan_apks` to populate it.")
        return

    message_text = f"📦 **Cached APKs ({len(APK_FILES)} total):**\n"
    for i, (key, data) in enumerate(APK_FILES.items(), 1):
        # Truncate original name if too long for display
        display_name = data['original_name'] if len(data['original_name']) < 30 else data['original_name'][:27] + '...'
        message_text += f"{i}. `/{key}` (`{display_name}`)\n"
    
    message_text += "\nUse the file name or a matching keyword to trigger the download."
    await message.reply_text(message_text, parse_mode='Markdown')

# --- Core Auto-Reply Logic Handler ---

# FIX: Use filters.chat_type() to replace the deprecated filters.supergroup
@app.on_message(filters.text & filters.chat_type([ChatType.GROUP, ChatType.SUPERGROUP]))
async def auto_reply_handler(client: Client, message: Message):
    """Listens for trigger messages in groups and replies with the corresponding APK."""
    
    text = message.text
    if not text:
        return
    
    clean_text = text.lower().strip()
    match_found = False
    
    # Check for simple trigger keywords (e.g., 'Download', '下载')
    is_keyword_triggered = any(keyword in clean_text for keyword in TRIGGER_KEYWORDS)
    
    target_apk_data = None

    if is_keyword_triggered:
        # If a general keyword is found, try to find a specific file name mention
        for key, data in APK_FILES.items():
            # Check if the text contains any part of the file's matching terms
            if any(term in clean_text for term in data['match_terms']):
                target_apk_data = data
                break
    else:
        # Check for direct file name match if no keyword was used (e.g., user just typed "app-v1-2")
        for key, data in APK_FILES.items():
            if key in clean_text:
                target_apk_data = data
                break

    if target_apk_data:
        logger.info(f"Match found. Sending file for '{target_apk_data['original_name']}' in chat {message.chat.id}.")
        await message.reply_document(
            document=target_apk_data['file_id'],
            caption=f"✅ Here is the file: **{target_apk_data['original_name']}**",
            parse_mode='Markdown',
            quote=True # Reply to the original message
        )
        match_found = True
        
    # If a keyword was used but no specific file was matched, list all files for user help.
    if is_keyword_triggered and not match_found and APK_FILES:
        message_list = ["I found a download request, but I couldn't identify the specific file you want. Available files are:"]
        # Limit the list length to keep the reply concise
        for i, data in enumerate(list(APK_FILES.values())[:10]):
            message_list.append(f"- {data['original_name']}")
            if i == 9 and len(APK_FILES) > 10:
                message_list.append(f"... and {len(APK_FILES) - 10} more.")
        
        await message.reply_text('\n'.join(message_list), quote=True)


# --- Startup and Entry Point ---

@app.on_message(filters.command("start") & filters.chat_type(ChatType.PRIVATE))
async def start_command(client: Client, message: Message):
    """Sends a welcome message with instructions."""
    instructions = (
        "🤖 **Pyrogram APK Auto-Reply Bot Online**\n\n"
        "**Admin Instructions (Private Chat Only):**\n"
        "1. Run `/scan_apks` to read the entire history of the channel (`@kachrapetihai`) and cache all APK files.\n"
        "2. Run `/list_apks` to see the currently stored files and their matching keys.\n\n"
        "**Group Instructions (for automated replies):**\n"
        "1. Add me to your group.\n"
        "2. When a user sends a message containing a file name (e.g., 'send app-v1-2') or a keyword and file name (e.g., 'Download the app-v1-2 file'), I will automatically reply with the APK."
    )
    await message.reply_text(instructions, parse_mode='Markdown')


# Start the bot application
if __name__ == "__main__":
    logger.info("Starting Pyrogram bot...")
    app.run()

