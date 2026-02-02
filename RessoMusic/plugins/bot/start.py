import time
import random
import asyncio

from pyrogram import filters
from pyrogram.enums import ChatType
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from youtubesearchpython.__future__ import VideosSearch

import config
from RessoMusic import app
from RessoMusic.core.mongo import db # Importing Database Client
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
# The User ID allowed to use /setstart and /editgrpstart
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
    if not data:
        return None
    return data["text"]

async def set_private_start_text(text):
    await startdb.update_one(
        {"type": "private_start"}, 
        {"$set": {"text": text}}, 
        upsert=True
    )

async def get_group_start_text():
    data = await startdb.find_one({"type": "group_start"})
    if not data:
        return None
    return data["text"]

async def set_group_start_text(text):
    await startdb.update_one(
        {"type": "group_start"}, 
        {"$set": {"text": text}}, 
        upsert=True
    )

# ========================= ADMIN COMMANDS =========================

@app.on_message(filters.command(["setstart"]) & filters.user(CUSTOM_START_ADMIN))
async def set_start_message_handler(client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text(
            "<b>Please provide the text to set.</b>\n\n"
            "<b>Variables you can use:</b>\n"
            "{0} - User Mention\n"
            "{1} - Bot Mention\n"
            "{2} - Uptime\n"
            "{3} - Disk\n"
            "{4} - CPU\n"
            "{5} - RAM\n\n"
            "<b>Example:</b> <code>/setstart Hello {0}, I am {1}. My Uptime is {2}</code>"
        )
    
    text = message.text.split(None, 1)[1]
    await set_private_start_text(text)
    await message.reply_text("<b>✅ Private Start Message updated successfully.</b>")


@app.on_message(filters.command(["editgrpstart"]) & filters.user(CUSTOM_START_ADMIN))
async def set_group_start_message_handler(client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text(
            "<b>Please provide the text to set for groups.</b>\n\n"
            "<b>Variables you can use:</b>\n"
            "{0} - Bot Mention\n"
            "{1} - Uptime\n\n"
            "<b>Example:</b> <code>/editgrpstart Alive in {0}. Uptime: {1}</code>"
        )
    
    text = message.text.split(None, 1)[1]
    await set_group_start_text(text)
    await message.reply_text("<b>✅ Group Start Message updated successfully.</b>")


# ========================= PRIVATE START =========================
@app.on_message(filters.command(["start"]) & filters.private & ~BANNED_USERS)
@LanguageStart
async def start_pm(client, message: Message, _):

    loading_1 = await message.reply_text(random.choice(GREET))
    await add_served_user(message.from_user.id)

    await asyncio.sleep(0.1)
    await loading_1.edit_text("<b>ᴅɪηɢ ᴅᴏηɢ.❤️‍🔥</b>")
    await asyncio.sleep(0.1)
    await loading_1.edit_text("<b>ᴅɪηɢ ᴅᴏηɢ..❤️‍🔥</b>")
    await asyncio.sleep(0.1)
    await loading_1.edit_text("<b>ᴅɪηɢ ᴅᴏηɢ...❤️‍🔥</b>")
    await asyncio.sleep(0.1)
    await loading_1.edit_text("<b>ᴅɪηɢ ᴅᴏηɢ....❤️‍🔥</b>")
    await asyncio.sleep(0.1)
    await loading_1.edit_text("<b>ᴅɪηɢ ᴅᴏηɢ.....❤️‍🔥</b>")
    await asyncio.sleep(0.1)
    await loading_1.edit_text("<b>ᴅɪηɢ ᴅᴏηɢ......❤️‍🔥</b>")
    await asyncio.sleep(0.1)
    await loading_1.delete()

    await add_served_user(message.from_user.id)

    if len(message.text.split()) > 1:
        name = message.text.split(None, 1)[1]

        if name[0:4] == "help":
            keyboard = help_pannel(_)
            return await message.reply_photo(
                random.choice(YUMI_PICS),
                has_spoiler=True,
                caption=_["help_1"].format(config.SUPPORT_GROUP),
                protect_content=True,
                reply_markup=keyboard,
            )

        if name[0:3] == "sud":
            await sudoers_list(client=client, message=message, _=_)
            if await is_on_off(2):
                return await app.send_message(
                    chat_id=config.LOG_GROUP_ID,
                    text=f"{message.from_user.mention} ᴊᴜsᴛ sᴛᴀʀᴛᴇᴅ ᴛʜᴇ ʙᴏᴛ.\n\n<b>ᴜsᴇʀ ɪᴅ :</b> <code>{message.from_user.id}</code>\n<b>ᴜsᴇʀɴᴀᴍᴇ :</b> @{message.from_user.username}",
                )
            return

        if name[0:3] == "inf":
            m = await message.reply_text("🔎")
            query = (str(name)).replace("info_", "", 1)
            query = f"https://www.youtube.com/watch?v={query}"
            results = VideosSearch(query, limit=1)
            for result in (await results.next())["result"]:
                title = result["title"]
                duration = result["duration"]
                views = result["viewCount"]["short"]
                thumbnail = result["thumbnails"][0]["url"].split("?")[0]
                channellink = result["channel"]["link"]
                channel = result["channel"]["name"]
                link = result["link"]
                published = result["publishedTime"]

            searched_text = _["start_6"].format(
                title, duration, views, published, channellink, channel, app.mention
            )

            key = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(text=_["S_B_8"], url=link),
                        InlineKeyboardButton(text=_["S_B_9"], url=config.SUPPORT_GROUP),
                    ],
                ]
            )

            await m.delete()
            await app.send_photo(
                chat_id=message.chat.id,
                photo=thumbnail,
                caption=searched_text,
                reply_markup=key,
            )

            if await is_on_off(2):
                return await app.send_message(
                    chat_id=config.LOG_GROUP_ID,
                    text=f"{message.from_user.mention} ᴊᴜsᴛ sᴛᴀʀᴛᴇᴅ ᴛʜᴇ ʙᴏᴛ ᴛᴏ ᴄʜᴇᴄᴋ <b>ᴛʀᴀᴄᴋ ɪɴғᴏʀᴍᴀᴛɪᴏɴ</b>.\n\n<b>ᴜsᴇʀ ɪᴅ :</b> <code>{message.from_user.id}</code>\n<b>ᴜsᴇʀɴᴀᴍᴇ :</b> @{message.from_user.username}",
                )

    else:
        out = private_panel(_)
        UP, CPU, RAM, DISK = await bot_sys_stats()
        
        # Check for custom start text in DB
        custom_text = await get_private_start_text()
        
        if custom_text:
            try:
                # Attempt to format with the 6 variables
                final_caption = custom_text.format(
                    message.from_user.mention, # {0}
                    app.mention,               # {1}
                    UP,                        # {2}
                    DISK,                      # {3}
                    CPU,                       # {4}
                    RAM                        # {5}
                )
            except Exception:
                # Fallback if custom text format is invalid
                final_caption = _["start_2"].format(
                    message.from_user.mention, app.mention, UP, DISK, CPU, RAM
                )
        else:
            # Default behavior
            final_caption = _["start_2"].format(
                message.from_user.mention, app.mention, UP, DISK, CPU, RAM
            )

        await message.reply_photo(
            random.choice(YUMI_PICS),
            has_spoiler=True,
            caption=final_caption,
            reply_markup=InlineKeyboardMarkup(out),
        )

        if await is_on_off(2):
            return await app.send_message(
                chat_id=config.LOG_GROUP_ID,
                text=f"{message.from_user.mention} ᴊᴜsᴛ sᴛᴀʀᴛᴇᴅ ᴛʜᴇ ʙᴏᴛ.\n\n<b>ᴜsᴇʀ ɪᴅ :</b> <code>{message.from_user.id}</code>\n<b>ᴜsᴇʀɴᴀᴍᴇ :</b> @{message.from_user.username}",
            )


# ========================= GROUP START =========================
@app.on_message(filters.command(["start"]) & filters.group & ~BANNED_USERS)
@LanguageStart
async def start_gp(client, message: Message, _):
    out = start_panel(_)
    uptime = int(time.time() - _boot_)
    
    # Check for custom group text in DB
    custom_text = await get_group_start_text()
    
    if custom_text:
        try:
            final_caption = custom_text.format(
                app.mention,               # {0}
                get_readable_time(uptime)  # {1}
            )
        except Exception:
             final_caption = _["start_1"].format(app.mention, get_readable_time(uptime))
    else:
        final_caption = _["start_1"].format(app.mention, get_readable_time(uptime))

    await message.reply_photo(
        random.choice(YUMI_PICS),
        has_spoiler=True,
        caption=final_caption,
        reply_markup=InlineKeyboardMarkup(out),
    )
    return await add_served_chat(message.chat.id)


# ========================= WELCOME HANDLERS =========================
welcome_group = 2
@app.on_message(filters.new_chat_members, group=welcome_group)
async def welcome(client, message: Message):
    try:
        chat_id = message.chat.id
        for member in message.new_chat_members:
            buttons = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            text=member.first_name,
                            user_id=member.id
                        )
                    ]
                ]
            )

            if isinstance(config.OWNER_ID, int):
                if member.id == config.OWNER_ID:
                    owner = f"#BOT_OWNER\n\n 𝐖𝐄𝐋𝐂𝐎𝐌𝐄 𝐁𝐎𝐒𝐒 💗\n\n{member.mention} 𝙊𝙬𝙣𝙚𝙧 𝗢𝗳 {app.mention} 𝙟𝙪𝙨𝙩 𝙟𝙤𝙞𝙣𝙚𝙙 𝙩𝙝𝗲 𝗴𝗿𝗼𝘂𝗽 <code>{message.chat.title}</code>.\n\nSupport Me Here👇🏻🤭💕"
                    sent_message = await message.reply_text(owner, reply_markup=buttons)
                    await asyncio.sleep(180)
                    await sent_message.delete()
                    return

            elif isinstance(config.OWNER_ID, (list, set)):
                if member.id in config.OWNER_ID:
                    owner = f"#BOT_OWNER\n\n 𝐖𝐄𝐋𝐂𝐎𝐌𝐄 𝐁𝐎𝐒𝐒 💗\n\n{member.mention} 𝗢𝘄𝗻𝗲𝗿 𝗢𝗳 {app.mention} 𝙟𝙪𝙨𝙩 𝙟𝙤𝙞𝙣𝙚𝙙 𝙩𝙝𝗲 𝗴𝗿𝗼𝘂𝗽 <code>{message.chat.title}</code>."
                    sent_message = await message.reply_text(owner, reply_markup=buttons)
                    await asyncio.sleep(180)
                    await sent_message.delete()
                    return

            if isinstance(SUDOERS, int):
                if member.id == SUDOERS:
                    AMBOT = f"#Sudo_User\n\n 𝐖𝐄𝐋𝐂𝐎𝐌𝐄 💗\n\n{app.mention} SUDO USER {member.mention} just joined the group <code>{message.chat.title}</code>."
                    sent_message = await message.reply_text(AMBOT, reply_markup=buttons)
                    await asyncio.sleep(180)
                    await sent_message.delete()
                    return

            elif isinstance(SUDOERS, (list, set)):
                if member.id in SUDOERS:
                    AMBOT = f"#Sudo_User\n\n 𝐖𝐄𝐋𝐂𝐎𝐌𝐄 💗\n\n{app.mention} SUDO USER {member.mention} just joined the group <code>{message.chat.title}</code>."
                    sent_message = await message.reply_text(AMBOT, reply_markup=buttons)
                    await asyncio.sleep(180)
                    await sent_message.delete()
                    return

        return
    except Exception as e:
        print(f"Error in welcome handler: {e}")
        return


@app.on_message(filters.new_chat_members, group=-1)
async def welcome(client, message: Message):
    for member in message.new_chat_members:
        try:
            language = await get_lang(message.chat.id)
            _ = get_string(language)
            if await is_banned_user(member.id):
                try:
                    await message.chat.ban_member(member.id)
                except:
                    pass

            if member.id == app.id:
                if message.chat.type != ChatType.SUPERGROUP:
                    await message.reply_text(_["start_4"])
                    return await app.leave_chat(message.chat.id)

                if message.chat.id in await blacklisted_chats():
                    await message.reply_text(
                        _["start_5"].format(
                            app.mention,
                            f"https://t.me/{app.username}?start=sudolist",
                            config.SUPPORT_GROUP,
                        ),
                        disable_web_page_preview=True,
                    )
                    return await app.leave_chat(message.chat.id)

                out = start_panel(_)
                await message.reply_photo(
                    random.choice(YUMI_PICS),
                    has_spoiler=True,
                    caption=_["start_3"].format(
                        message.from_user.first_name,
                        app.mention,
                        message.chat.title,
                        app.mention,
                    ),
                    reply_markup=InlineKeyboardMarkup(out),
                )

                await add_served_chat(message.chat.id)
                await message.stop_propagation()

        except Exception as ex:
            print(ex)
