import time
import random
import asyncio

from pyrogram import filters
from pyrogram.enums import ChatType
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from youtubesearchpython.__future__ import VideosSearch

import config
from RessoMusic import app
from RessoMusic.core.mongo import mongodb as db 
from RessoMusic.misc import _boot_
from RessoMusic.plugins.sudo.sudoers import sudoers_list
from RessoMusic.utils.database import (
    add_served_chat,
    add_served_user,
    blacklisted_chats,
    get_lang,
    is_banned_user,
    is_on_off,
)
from RessoMusic.utils import bot_sys_stats
from RessoMusic.utils.decorators.language import LanguageStart
from RessoMusic.utils.formatters import get_readable_time
from RessoMusic.utils.inline import help_pannel, private_panel, start_panel
from config import BANNED_USERS
from strings import get_string
from RessoMusic.misc import SUDOERS

# ========================= CONFIGURATION =========================
CUSTOM_START_ADMIN = 7659846392 

YUMI_PICS = [
    "https://files.catbox.moe/x832ly.jpg",
    "https://files.catbox.moe/y2to84.jpg",
    "https://files.catbox.moe/qmdqx8.jpg",
]

GREET = ["💞", "🥂", "🔍", "🧪", "🥂", "⚡️", "🔥"]

# ========================= DATABASE FUNCTIONS =========================
startdb = db.start_messages

async def get_private_start_text():
    data = await startdb.find_one({"type": "private_start"})
    return data["text"] if data else None

async def set_private_start_text(text):
    await startdb.update_one({"type": "private_start"}, {"$set": {"text": text}}, upsert=True)

async def get_group_start_text():
    data = await startdb.find_one({"type": "group_start"})
    return data["text"] if data else None

async def set_group_start_text(text):
    await startdb.update_one({"type": "group_start"}, {"$set": {"text": text}}, upsert=True)

# ========================= ADMIN COMMANDS =========================

@app.on_message(filters.command(["setstart"]) & filters.user(CUSTOM_START_ADMIN))
async def set_start_message_handler(client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text("<b>Usage:</b> /setstart [Your formatted message]")
    
    # We use .html to capture <blockquote>, <b>, etc. exactly as sent
    raw_text = message.text.html.split(None, 1)[1]
    await set_private_start_text(raw_text)
    await message.reply_text("<b>✅ Private Start updated! Formatting preserved.</b>")

@app.on_message(filters.command(["editgrpstart"]) & filters.user(CUSTOM_START_ADMIN))
async def set_group_start_message_handler(client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text("<b>Usage:</b> /editgrpstart [Your formatted message]")
    
    raw_text = message.text.html.split(None, 1)[1]
    await set_group_start_text(raw_text)
    await message.reply_text("<b>✅ Group Start updated! Formatting preserved.</b>")

# ========================= PRIVATE START =========================
@app.on_message(filters.command(["start"]) & filters.private & ~BANNED_USERS)
@LanguageStart
async def start_pm(client, message: Message, _):
    await add_served_user(message.from_user.id)
    
    # Loading animation
    loading_1 = await message.reply_text(random.choice(GREET))
    for i in range(1, 7):
        await asyncio.sleep(0.1)
        await loading_1.edit_text(f"<b>ᴅɪηɢ ᴅᴏηɢ{'.' * i}❤️‍🔥</b>")
    await loading_1.delete()

    if len(message.text.split()) > 1:
        name = message.text.split(None, 1)[1]
        if name[0:4] == "help":
            return await message.reply_photo(random.choice(YUMI_PICS), has_spoiler=True, caption=_["help_1"].format(config.SUPPORT_GROUP), reply_markup=help_pannel(_))
        
        if name[0:3] == "sud":
            await sudoers_list(client=client, message=message, _=_)
            return

        if name[0:3] == "inf":
            m = await message.reply_text("🔎")
            query = f"https://www.youtube.com/watch?v={(str(name)).replace('info_', '', 1)}"
            results = VideosSearch(query, limit=1)
            for result in (await results.next())["result"]:
                title, duration, views, thumbnail = result["title"], result["duration"], result["viewCount"]["short"], result["thumbnails"][0]["url"].split("?")[0]
                channellink, channel, link, published = result["channel"]["link"], result["channel"]["name"], result["link"], result["publishedTime"]
            
            await m.delete()
            await app.send_photo(chat_id=message.chat.id, photo=thumbnail, caption=_["start_6"].format(title, duration, views, published, channellink, channel, app.mention),
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(text=_["S_B_8"], url=link), InlineKeyboardButton(text=_["S_B_9"], url=config.SUPPORT_GROUP)]]))
            return

    else:
        UP, CPU, RAM, DISK = await bot_sys_stats()
        custom_text = await get_private_start_text()
        
        if custom_text:
            # We use .format on the raw HTML string
            caption = custom_text.format(message.from_user.mention, app.mention, UP, DISK, CPU, RAM)
        else:
            caption = _["start_2"].format(message.from_user.mention, app.mention, UP, DISK, CPU, RAM)

        await message.reply_photo(
            random.choice(YUMI_PICS),
            has_spoiler=True,
            caption=caption,
            reply_markup=InlineKeyboardMarkup(private_panel(_)),
        )

# ========================= GROUP START =========================
@app.on_message(filters.command(["start"]) & filters.group & ~BANNED_USERS)
@LanguageStart
async def start_gp(client, message: Message, _):
    uptime = int(time.time() - _boot_)
    custom_text = await get_group_start_text()
    
    if custom_text:
        caption = custom_text.format(app.mention, get_readable_time(uptime))
    else:
        caption = _["start_1"].format(app.mention, get_readable_time(uptime))

    await message.reply_photo(
        random.choice(YUMI_PICS),
        has_spoiler=True,
        caption=caption,
        reply_markup=InlineKeyboardMarkup(start_panel(_)),
    )
    await add_served_chat(message.chat.id)

# ========================= WELCOME HANDLERS =========================
@app.on_message(filters.new_chat_members, group=2)
async def welcome(client, message: Message):
    for member in message.new_chat_members:
        try:
            buttons = InlineKeyboardMarkup([[InlineKeyboardButton(text=member.first_name, user_id=member.id)]])
            if (isinstance(config.OWNER_ID, int) and member.id == config.OWNER_ID) or (isinstance(config.OWNER_ID, list) and member.id in config.OWNER_ID):
                msg = await message.reply_text(f"#BOT_OWNER\n\n 𝐖𝐄𝐋𝐂𝐎𝐌𝐄 𝐁𝐎𝐒𝐒 💗\n\n{member.mention} 𝙊𝙬𝙣𝙚𝙧 𝙊𝙛 {app.mention} just joined.", reply_markup=buttons)
                await asyncio.sleep(180)
                return await msg.delete()
        except: pass

@app.on_message(filters.new_chat_members, group=-1)
async def bot_added(client, message: Message):
    for member in message.new_chat_members:
        if member.id == app.id:
            if message.chat.id in await blacklisted_chats():
                await message.reply_text("Chat Blacklisted.")
                return await app.leave_chat(message.chat.id)
            
            language = await get_lang(message.chat.id)
            _ = get_string(language)
            await message.reply_photo(random.choice(YUMI_PICS), caption=_["start_3"].format(message.from_user.first_name, app.mention, message.chat.title, app.mention), reply_markup=InlineKeyboardMarkup(start_panel(_)))
            await add_served_chat(message.chat.id)
