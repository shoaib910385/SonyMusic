import os
from random import randint
from typing import Union

from pyrogram.types import InlineKeyboardMarkup

import config
from RessoMusic import Carbon, YouTube, app
from RessoMusic.core.call import AMBOTOP
from RessoMusic.misc import db
from RessoMusic.utils.database import add_active_video_chat, is_active_chat
from RessoMusic.utils.exceptions import AssistantErr
from RessoMusic.utils.inline import aq_markup, close_markup, stream_markup
from RessoMusic.utils.pastebin import AMBOTOPBin
from RessoMusic.utils.stream.queue import put_queue, put_queue_index
from RessoMusic.utils.thumbnails import gen_thumb


async def stream(
    _,
    mystic,
    user_id,
    result,
    chat_id,
    user_name,
    original_chat_id,
    video: Union[bool, str] = None,
    streamtype: Union[bool, str] = None,
    spotify: Union[bool, str] = None,
    forceplay: Union[bool, str] = None,
):
    if not result:
        return

    # Stop current stream if forceplay used
    if forceplay:
        try:
            await AMBOTOP.force_stop_stream(chat_id)
        except Exception:
            # don't crash if force_stop fails
            pass

    # -------- PLAYLIST ----------
    if streamtype == "playlist":
        msg = f"{_['play_19']}\n\n"
        count = 0
        position = 0
        for search in result:
            if int(count) == config.PLAYLIST_FETCH_LIMIT:
                continue
            try:
                (
                    title,
                    duration_min,
                    duration_sec,
                    thumbnail,
                    vidid,
                ) = await YouTube.details(search, False if spotify else True)
            except Exception:
                continue

            if str(duration_min) == "None":
                continue
            if duration_sec > config.DURATION_LIMIT:
                continue

            # If already active, just queue
            if await is_active_chat(chat_id):
                await put_queue(
                    chat_id,
                    original_chat_id,
                    f"vid_{vidid}",
                    title,
                    duration_min,
                    user_name,
                    vidid,
                    user_id,
                    "video" if video else "audio",
                )
                position = len(db.get(chat_id)) - 1
                count += 1
                msg += f"{count}. {title[:70]}\n"
                msg += f"{_['play_20']} {position}\n\n"
            else:
                # start streaming the first track
                if not forceplay:
                    db[chat_id] = []
                status = True if video else None
                try:
                    file_path, direct = await YouTube.download(
                        vidid, mystic, videoid=True, video=status
                    )
                except Exception:
                    raise AssistantErr(_["play_14"])
                try:
                    await AMBOTOP.join_call(
                        chat_id,
                        original_chat_id,
                        file_path,
                        video=status,
                        image=thumbnail,
                    )
                except Exception as e:
                    # if join_call fails, propagate as AssistantErr
                    raise AssistantErr(_["general_2"].format(type(e).__name__))

                await put_queue(
                    chat_id,
                    original_chat_id,
                    file_path if direct else f"vid_{vidid}",
                    title,
                    duration_min,
                    user_name,
                    vidid,
                    user_id,
                    "video" if video else "audio",
                    forceplay=forceplay,
                )

                # generate thumbnail (safe)
                try:
                    img = await gen_thumb(vidid)
                except Exception:
                    img = thumbnail if thumbnail else config.STREAM_IMG_URL

                button = stream_markup(_, chat_id)
                try:
                    run = await app.send_photo(
                        original_chat_id,
                        photo=img,
                        has_spoiler=True,
                        caption=_["stream_1"].format(
                            f"https://t.me/{app.username}?start=info_{vidid}",
                            title[:23],
                            duration_min,
                            user_name,
                        ),
                        reply_markup=InlineKeyboardMarkup(button),
                    )
                    db[chat_id][0]["mystic"] = run
                    db[chat_id][0]["markup"] = "stream"
                except Exception:
                    # continue even if sending photo fails
                    pass

        if count == 0:
            return
        else:
            # try to upload playlist text to pastebin and generate carbon, but don't fail if it errors
            try:
                link = await AMBOTOPBin(msg)
            except Exception:
                link = "N/A"
            lines = msg.count("\n")
            if lines >= 17:
                car = os.linesep.join(msg.split(os.linesep)[:17])
            else:
                car = msg
            try:
                carbon = await Carbon.generate(car, randint(100, 10000000))
            except Exception:
                carbon = None

            upl = close_markup(_)
            try:
                if carbon:
                    return await app.send_photo(
                        original_chat_id,
                        photo=carbon,
                        caption=_["play_21"].format(position, link),
                        reply_markup=upl,
                    )
                else:
                    return await app.send_message(
                        original_chat_id,
                        text=_["play_21"].format(position, link),
                        reply_markup=upl,
                    )
            except Exception:
                return

    # -------- YOUTUBE (single track) ----------
    elif streamtype == "youtube":
        link = result.get("link")
        vidid = result.get("vidid")
        title = (result.get("title") or "").title()
        duration_min = result.get("duration_min")
        thumbnail = result.get("thumb")
        status = True if video else None

        # enforce queue size limit if desired
        current_queue = db.get(chat_id)
        if current_queue is not None and len(current_queue) >= 10:
            try:
                await app.send_message(original_chat_id, "You can't add more than 10 songs to the queue.")
            except Exception:
                pass
            return

        try:
            file_path, direct = await YouTube.download(
                vidid, mystic, videoid=True, video=status
            )
        except Exception:
            raise AssistantErr(_["play_14"])

        if await is_active_chat(chat_id):
            await put_queue(
                chat_id,
                original_chat_id,
                file_path if direct else f"vid_{vidid}",
                title,
                duration_min,
                user_name,
                vidid,
                user_id,
                "video" if video else "audio",
            )
            position = len(db.get(chat_id)) - 1
            button = aq_markup(_, chat_id)
            try:
                await app.send_message(
                    chat_id=original_chat_id,
                    text=_["queue_4"].format(position, title[:27], duration_min, user_name),
                    reply_markup=InlineKeyboardMarkup(button),
                )
            except Exception:
                pass
        else:
            if not forceplay:
                db[chat_id] = []
            try:
                await AMBOTOP.join_call(
                    chat_id,
                    original_chat_id,
                    file_path,
                    video=status,
                    image=thumbnail,
                )
            except Exception as e:
                raise AssistantErr(_["general_2"].format(type(e).__name__))

            await put_queue(
                chat_id,
                original_chat_id,
                file_path if direct else f"vid_{vidid}",
                title,
                duration_min,
                user_name,
                vidid,
                user_id,
                "video" if video else "audio",
                forceplay=forceplay,
            )

            # thumbnail generation fallback
            try:
                img = await gen_thumb(vidid)
            except Exception:
                img = thumbnail if thumbnail else config.STREAM_IMG_URL

            button = stream_markup(_, chat_id)
            try:
                run = await app.send_photo(
                    original_chat_id,
                    photo=img,
                    caption=_["stream_1"].format(
                        f"https://t.me/{app.username}?start=info_{vidid}",
                        title[:23],
                        duration_min,
                        user_name,
                    ),
                    reply_markup=InlineKeyboardMarkup(button),
                )
                db[chat_id][0]["mystic"] = run
                db[chat_id][0]["markup"] = "stream"
            except Exception:
                # continue even if sending fails
                pass

    # -------- SOUNDCLOUD ----------
    elif streamtype == "soundcloud":
        file_path = result.get("filepath")
        title = result.get("title")
        duration_min = result.get("duration_min")
        if await is_active_chat(chat_id):
            await put_queue(
                chat_id,
                original_chat_id,
                file_path,
                title,
                duration_min,
                user_name,
                streamtype,
                user_id,
                "audio",
            )
            position = len(db.get(chat_id)) - 1
            button = aq_markup(_, chat_id)
            try:
                await app.send_message(
                    chat_id=original_chat_id,
                    text=_["queue_4"].format(position, title[:27], duration_min, user_name),
                    reply_markup=InlineKeyboardMarkup(button),
                )
            except Exception:
                pass
        else:
            if not forceplay:
                db[chat_id] = []
            try:
                await AMBOTOP.join_call(chat_id, original_chat_id, file_path, video=None)
            except Exception as e:
                raise AssistantErr(_["general_2"].format(type(e).__name__))

            await put_queue(
                chat_id,
                original_chat_id,
                file_path,
                title,
                duration_min,
                user_name,
                streamtype,
                user_id,
                "audio",
                forceplay=forceplay,
            )
            button = stream_markup(_, chat_id)
            try:
                run = await app.send_photo(
                    original_chat_id,
                    photo=config.SOUNCLOUD_IMG_URL,
                    caption=_["stream_1"].format(
                        config.SUPPORT_GROUP, title[:23], duration_min, user_name
                    ),
                    reply_markup=InlineKeyboardMarkup(button),
                )
                db[chat_id][0]["mystic"] = run
                db[chat_id][0]["markup"] = "tg"
            except Exception:
                pass

    # -------- TELEGRAM (uploaded file) ----------
    elif streamtype == "telegram":
        file_path = result.get("path")
        link = result.get("link")
        title = (result.get("title") or "").title()
        duration_min = result.get("dur")
        status = True if video else None

        if await is_active_chat(chat_id):
            await put_queue(
                chat_id,
                original_chat_id,
                file_path,
                title,
                duration_min,
                user_name,
                streamtype,
                user_id,
                "video" if video else "audio",
            )
            position = len(db.get(chat_id)) - 1
            button = aq_markup(_, chat_id)
            try:
                await app.send_message(
                    chat_id=original_chat_id,
                    text=_["queue_4"].format(position, title[:27], duration_min, user_name),
                    reply_markup=InlineKeyboardMarkup(button),
                )
            except Exception:
                pass
        else:
            if not forceplay:
                db[chat_id] = []
            try:
                await AMBOTOP.join_call(chat_id, original_chat_id, file_path, video=status)
            except Exception as e:
                raise AssistantErr(_["general_2"].format(type(e).__name__))

            await put_queue(
                chat_id,
                original_chat_id,
                file_path,
                title,
                duration_min,
                user_name,
                streamtype,
                user_id,
                "video" if video else "audio",
                forceplay=forceplay,
            )
            if video:
                try:
                    await add_active_video_chat(chat_id)
                except Exception:
                    pass
            button = stream_markup(_, chat_id)
            try:
                run = await app.send_photo(
                    original_chat_id,
                    photo=config.TELEGRAM_VIDEO_URL if video else config.TELEGRAM_AUDIO_URL,
                    caption=_["stream_1"].format(link, title[:23], duration_min, user_name),
                    reply_markup=InlineKeyboardMarkup(button),
                )
                db[chat_id][0]["mystic"] = run
                db[chat_id][0]["markup"] = "tg"
            except Exception:
                pass

    # -------- LIVE ----------
    elif streamtype == "live":
        link = result.get("link")
        vidid = result.get("vidid")
        title = (result.get("title") or "").title()
        thumbnail = result.get("thumb")
        duration_min = "Live Track"
        status = True if video else None

        if await is_active_chat(chat_id):
            await put_queue(
                chat_id,
                original_chat_id,
                f"live_{vidid}",
                title,
                duration_min,
                user_name,
                vidid,
                user_id,
                "video" if video else "audio",
            )
            position = len(db.get(chat_id)) - 1
            button = aq_markup(_, chat_id)
            try:
                await app.send_message(
                    chat_id=original_chat_id,
                    text=_["queue_4"].format(position, title[:27], duration_min, user_name),
                    reply_markup=InlineKeyboardMarkup(button),
                )
            except Exception:
                pass
        else:
            if not forceplay:
                db[chat_id] = []
            n, file_path = await YouTube.video(link)
            if n == 0:
                raise AssistantErr(_["str_3"])
            try:
                await AMBOTOP.join_call(
                    chat_id,
                    original_chat_id,
                    file_path,
                    video=status,
                    image=thumbnail if thumbnail else None,
                )
            except Exception as e:
                raise AssistantErr(_["general_2"].format(type(e).__name__))

            await put_queue(
                chat_id,
                original_chat_id,
                f"live_{vidid}",
                title,
                duration_min,
                user_name,
                vidid,
                user_id,
                "video" if video else "audio",
                forceplay=forceplay,
            )

            try:
                img = await gen_thumb(vidid)
            except Exception:
                img = thumbnail if thumbnail else config.STREAM_IMG_URL

            button = stream_markup(_, chat_id)
            try:
                run = await app.send_photo(
                    original_chat_id,
                    photo=img,
                    has_spoiler=True,
                    caption=_["stream_1"].format(
                        f"https://t.me/{app.username}?start=info_{vidid}",
                        title[:23],
                        duration_min,
                        user_name,
                    ),
                    reply_markup=InlineKeyboardMarkup(button),
                )
                db[chat_id][0]["mystic"] = run
                db[chat_id][0]["markup"] = "tg"
            except Exception:
                pass

    # -------- INDEX / M3U8 ----------
    elif streamtype == "index":
        link = result
        title = "ɪɴᴅᴇx ᴏʀ ᴍ3ᴜ8 ʟɪɴᴋ"
        duration_min = "00:00"
        if await is_active_chat(chat_id):
            await put_queue_index(
                chat_id,
                original_chat_id,
                "index_url",
                title,
                duration_min,
                user_name,
                link,
                "video" if video else "audio",
            )
            position = len(db.get(chat_id)) - 1
            button = aq_markup(_, chat_id)
            try:
                await mystic.edit_text(
                    text=_["queue_4"].format(position, title[:27], duration_min, user_name),
                    reply_markup=InlineKeyboardMarkup(button),
                )
            except Exception:
                # ignore edit failures
                pass
        else:
            if not forceplay:
                db[chat_id] = []
            try:
                await AMBOTOP.join_call(
                    chat_id,
                    original_chat_id,
                    link,
                    video=True if video else None,
                )
            except Exception as e:
                raise AssistantErr(_["general_2"].format(type(e).__name__))

            await put_queue_index(
                chat_id,
                original_chat_id,
                "index_url",
                title,
                duration_min,
                user_name,
                link,
                "video" if video else "audio",
                forceplay=forceplay,
            )
            button = stream_markup(_, chat_id)
            try:
                run = await app.send_photo(
                    original_chat_id,
                    photo=config.STREAM_IMG_URL,
                    has_spoiler=True,
                    caption=_["stream_2"].format(user_name),
                    reply_markup=InlineKeyboardMarkup(button),
                )
                db[chat_id][0]["mystic"] = run
                db[chat_id][0]["markup"] = "tg"
            except Exception:
                pass
            try:
                await mystic.delete()
            except Exception:
                pass
