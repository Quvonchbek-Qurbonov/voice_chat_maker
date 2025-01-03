import datetime
import getpass
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
from dotenv import load_dotenv
from telethon import TelegramClient, functions
from video_chat import *

load_dotenv()

phone_number = os.getenv("PHONE")
group_id = int(os.getenv("ALLOWED_GROUP_ID"))
TOKEN = os.getenv("TOKEN")
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")

# Keep track of the active group call
active_group_call = None


async def init_client():
    if not client.is_connected():
        await client.connect()
        if not await client.is_user_authorized():
            await client.send_code_request(phone_number)
            code = input('Enter the code you received: ')
            try:
                await client.sign_in(phone_number, code)
            except Exception as e:
                if "password" in str(e).lower():
                    password = getpass.getpass('Enter your 2FA password: ')
                    await client.sign_in(password=password)
    return client


async def check_group(update: Update) -> bool:
    if update.effective_chat.id != group_id:
        await update.message.reply_text("Bot is not authorized in this group.")
        return False
    return True


def is_half_hour_passed(starting_time):
    current_time = datetime.datetime.now()
    time_difference = current_time - starting_time
    return time_difference >= datetime.timedelta(minutes=30)


async def is_voice_chat_active() -> bool:
    try:
        chat = await client.get_entity(group_id)
        full_chat = await client(functions.channels.GetFullChannelRequest(
            channel=chat
        ))

        try:
            if hasattr(full_chat.full_chat, 'call') and full_chat.full_chat.call:
                group_call = await client(functions.phone.GetGroupCallRequest(
                    call=full_chat.full_chat.call,
                    limit=1
                ))
                return True
        except Exception as call_error:
            print(f"Error getting call info: {call_error}")
            return False

        return False

    except Exception as e:
        print(f"Error checking voice chat status: {e}")
        return False


async def handle_voice_chat():
    try:
        start_result = await start_voice_chat(group_id)
        join_result = await join_voice_chat(group_id)
        if not join_result:
            print("Failed to join group call")
            return False

        print("Successfully joined group call")
        starting_time = datetime.datetime.now()
        continue_voice_chat = True

        while continue_voice_chat:
            await asyncio.sleep(10)
            is_active = await is_voice_chat_active()
            if is_half_hour_passed(starting_time) or not is_active:
                continue_voice_chat = False
            else:
                await join_voice_chat(group_id)

        # Leave the group call
        print(await end_voice_chat(group_id))

        return True

    except Exception as e:
        print(f"Error in voice chat: {e}")
        return False


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_group(update):
        return

    try:
        await init_client()
        await update.message.delete()
        success = await handle_voice_chat()
        if not success:
            print("Something went wrong")
    except Exception as e:
        print(f"Error in start command: {e}")
        await update.message.reply_text("An error occurred. Please try again.")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_group(update):
        return
    help_text = """
Available commands:
/videochat - Start a voice chat
/help - Show this help message
"""
    await update.message.reply_text(help_text)


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.data == "videochat":
        try:
            await init_client()
            await client.send_message(group_id, "/videochat")
            await query.answer()
        except Exception as e:
            print(f"Error sending message as user: {e}")
            await query.answer("Failed to send message", show_alert=True)


async def add_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_group(update):
        return
    keyboard = [[InlineKeyboardButton("Start Video Chat", callback_data='videochat')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Video Chat", reply_markup=reply_markup)


async def initialize():
    await init_client()
    print("Client initialized successfully")


def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("videochat", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("addbutton", add_button))
    app.add_handler(CallbackQueryHandler(button_callback))

    print("Bot started...")
    app.run_polling(poll_interval=1)


if __name__ == '__main__':
    main()