from pyrogram.types import InlineKeyboardButton

import config
from RessoMusic import app


def start_panel(_):
    buttons = [
        [
            InlineKeyboardButton(
                text=_["S_B_1"], url=f"https://t.me/{app.username}?startgroup=true"
            ),
            InlineKeyboardButton(text=_["S_B_2"], url=config.SUPPORT_GROUP),
        ],
    ]
    return buttons


def private_panel(_):
    buttons = [
        [
            InlineKeyboardButton(
                "˹ᴛᴧᴘ ᴛᴏ sєє ϻᴧɢɪᴄ˼",
                url=f"https://t.me/{app.username}?startgroup=true",
            )
        ],
        [InlineKeyboardButton("˹ʜєʟᴘ˼", callback_data="settings_back_helper"),
        InlineKeyboardButton("˹ᴄʜᴧɴɴєʟ˼", url="https://t.me/itzdhruv1060"),
            #InlineKeyboardButton(text=_["S_B_7"], url=config.UPSTREAM_REPO),
        ],
        [InlineKeyboardButton("˹ ϻʏ ϻᴧsᴛєʀ ˼ 👑", url=f"https://t.me/itzdhruv")

        ],
        
    ]
    return buttons


