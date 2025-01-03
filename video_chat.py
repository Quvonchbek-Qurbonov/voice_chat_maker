import random
import json
import os

from telethon import TelegramClient
from telethon.tl.functions.phone import CreateGroupCallRequest, JoinGroupCallRequest, DiscardGroupCallRequest
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.types import InputPeerChannel, DataJSON
from dotenv import load_dotenv

load_dotenv()
api_id = os.getenv("API_ID")
api_hash = os.getenv("API_HASH")
client = TelegramClient('my_account', api_id, api_hash)


async def start_voice_chat(chat_id):
    try:
        channel = await client.get_entity(chat_id)
        input_peer = InputPeerChannel(channel.id, channel.access_hash)
        updates = await client(CreateGroupCallRequest(
            peer=input_peer,
            random_id=random.randint(100000, 999999)
        ))

        for update in updates.updates:
            if hasattr(update, 'call'):
                return update.call

        print("Could not find call in updates")
        return None
    except Exception as e:
        print(f"Error in start_voice_chat: {str(e.__class__.__name__)}: {str(e)}")
        return None


async def join_voice_chat(chat_id, as_owner=True):
    try:
        channel = await client.get_entity(chat_id)
        me = await client.get_me()
        full_channel = await client(GetFullChannelRequest(channel=channel))

        if not full_channel.full_chat.call:
            print("No active voice chat found. Starting new one...")
            call = await start_voice_chat(chat_id)
            if not call:
                return "Failed to start voice chat"
            full_channel = await client(GetFullChannelRequest(channel=channel))

        join_as = channel if as_owner else me

        await client(JoinGroupCallRequest(
            call=full_channel.full_chat.call,
            join_as=join_as,
            params=DataJSON(data=json.dumps({
                "ufrag": "custom_ufrag",
                "pwd": "custom_pwd",
                "fingerprints": [{"fingerprint": "custom_fingerprint"}],
                "ssrc": 1
            })),
            muted=True
        ))
        return "Joined voice chat successfully as " + ("owner" if as_owner else "member")
    except Exception as e:
        return f"Error joining voice chat: {str(e)}"


async def end_voice_chat(chat_id):
    try:
        channel = await client.get_entity(chat_id)
        full_channel = await client(GetFullChannelRequest(channel=channel))

        if not full_channel.full_chat.call:
            return "No active voice chat found"

        await client(DiscardGroupCallRequest(
            call=full_channel.full_chat.call
        ))
        return "Voice chat ended successfully"
    except Exception as e:
        return f"Error ending voice chat: {str(e)}"
