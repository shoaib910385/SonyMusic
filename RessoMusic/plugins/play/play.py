
# Now let me write the complete rewritten files
import random
import string
import aiohttp

from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InputMediaPhoto, Message
from pytgcalls.exceptions import NoActiveGroupCall

import config
from RessoMusic import Apple, Resso, SoundCloud, Spotify, Telegram, YouTube, app
from RessoMusic.core.call import AMBOTOP
from RessoMusic.core.mongo import mongodb
from RessoMusic.utils import seconds_to_min, time_to_seconds
from RessoMusic.utils.channelplay import get_channeplayCB
from RessoMusic.utils.decorators.language import languageCB
from RessoMusic.utils.decorators.play import PlayWrapper
from RessoMusic.utils.formatters import formats
from RessoMusic.utils.inline import (
    botplaylist_markup,
    livestream_markup,
    playlist_markup,
    slider_markup,
    track_markup,
)
from RessoMusic.utils.logger import play_logs
from RessoMusic.utils.stream.stream import stream
from config import BANNED_USERS, lyrical

# ─── CONFIGURATION ────────────────────────────────────────────────────────────
ADMIN_ID = 7659846392
DRX_API_BASE = "https://apidrx-music.vercel.app/api"

# MongoDB collection for admin-added songs
addsongdb = mongodb.added_songs


# ─── DRX API HELPERS ──────────────────────────────────────────────────────────

async def drx_search_songs(query: str):
    """Search songs via DRX API. Returns list of results or None."""
    url = f"{DRX_API_BASE}/search/songs"
    params = {"query": query}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                if data.get("success") and data.get("data", {}).get("results"):
                    return data["data"]["results"]
                return None
    except Exception:
        return None


def get_best_download_url(download_urls: list):
    """Pick the best quality URL between 96kbps and 320kbps."""
    quality_map = {}
    for item in download_urls:
        q = item["quality"]
        if q.endswith("kbps"):
            kbps = int(q.replace("kbps", ""))
            quality_map[kbps] = item["url"]
    # Prefer 160kbps, then 320kbps, then 96kbps, then 48kbps
    for preferred in [160, 320, 96, 48, 12]:
        if preferred in quality_map:
            return quality_map[preferred]
    # fallback: return first available
    if download_urls:
        return download_urls[0]["url"]
    return None


def get_500x500_image(images: list):
    """Get the 500x500 image URL from the image list."""
    for img in images:
        if img["quality"] == "500x500":
            return img["url"]
    # fallback
    if images:
        return images[-1]["url"]
    return config.PLAYLIST_IMG_URL


def seconds_to_min_str(seconds: int):
    """Convert seconds to MM:SS format."""
    mins = seconds // 60
    secs = seconds % 60
    return f"{mins}:{secs:02d}"


# ─── ADDSONG DB HELPERS ───────────────────────────────────────────────────────

async def get_added_song(query: str):
    """Get an admin-added song by query (case-insensitive)."""
    data = await addsongdb.find_one({"query": query.lower().strip()})
    return data


async def save_added_song(query: str, url: str, title: str = None, duration: str = "00:00"):
    """Save an admin-added song to DB."""
    await addsongdb.update_one(
        {"query": query.lower().strip()},
        {"$set": {"url": url, "title": title or query, "duration": duration}},
        upsert=True,
    )


async def delete_added_song(query: str):
    """Delete an admin-added song from DB."""
    await addsongdb.delete_one({"query": query.lower().strip()})


async def list_added_songs():
    """List all admin-added songs."""
    cursor = addsongdb.find({})
    return await cursor.to_list(length=1000)


# ─── ADDSONG COMMAND ────────────────────────────────────────────────────────────

@app.on_message(filters.command("addsong") & filters.user(ADMIN_ID))
async def addsong_command(client, message: Message):
    """
    /addsong <query>
    Admin adds a custom song URL for a query.
    Bot will ask for the song URL in the next step.
    """
    if len(message.command) < 2:
        return await message.reply_text(
            "**Usage:**\\n"
            "`/addsong <query>`\n\n"
            "Example: `/addsong tum hi ho`\n\n"
            "Then reply with the song URL to save it."
        )
    query = message.text.split(None, 1)[1].strip()
    
    # Check if already exists
    existing = await get_added_song(query)
    if existing:
        return await message.reply_text(
            f"⚠️ A song already exists for **{query}**\n"
            f"URL: `{existing['url']}`\n\n"
            "Reply with a new URL to update, or use `/delsong {query}` to remove first."
        )
    
    # Store pending state
    pending_key = f"addsong_pending:{message.from_user.id}"
    await mongodb.pending_states.update_one(
        {"key": pending_key},
        {"$set": {"key": pending_key, "query": query, "chat_id": message.chat.id}},
        upsert=True,
    )
    
    await message.reply_text(
        f"🎵 **Add Song Mode**\n"
        f"Query: `{query}`\n\n"
        "Now reply to this message with the **song URL** you want to save.\n"
        "Or reply with `cancel` to abort."
    )


@app.on_message(filters.reply & filters.user(ADMIN_ID))
async def addsong_url_handler(client, message: Message):
    """Handle URL reply for /addsong command."""
    if not message.reply_to_message:
        return
    
    pending_key = f"addsong_pending:{message.from_user.id}"
    pending = await mongodb.pending_states.find_one({"key": pending_key})
    if not pending:
        return
    
    # Clean up pending state
    await mongodb.pending_states.delete_one({"key": pending_key})
    
    if message.text.lower().strip() == "cancel":
        return await message.reply_text("❌ Add song cancelled.")
    
    url = message.text.strip()
    query = pending["query"]
    
    await save_added_song(query, url, title=query)
    await message.reply_text(
        f"✅ **Song Added!**\n"
        f"Query: `{query}`\n"
        f"URL: `{url}`\n\n"
        "Whenever someone searches for this query, this URL will be played directly."
    )


@app.on_message(filters.command("delsong") & filters.user(ADMIN_ID))
async def delsong_command(client, message: Message):
    """Delete an admin-added song."""
    if len(message.command) < 2:
        return await message.reply_text("**Usage:** `/delsong <query>`")
    query = message.text.split(None, 1)[1].strip()
    existing = await get_added_song(query)
    if not existing:
        return await message.reply_text(f"❌ No song found for query: `{query}`")
    await delete_added_song(query)
    await message.reply_text(f"✅ Deleted song for query: `{query}`")


@app.on_message(filters.command("listsongs") & filters.user(ADMIN_ID))
async def listsongs_command(client, message: Message):
    """List all admin-added songs."""
    songs = await list_added_songs()
    if not songs:
        return await message.reply_text("📭 No admin-added songs found.")
    
    text = "📋 **Admin Added Songs:**\\n\\n"
    for i, song in enumerate(songs, 1):
        text += f"{i}. `{song['query']}` → `{song.get('url', 'N/A')[:50]}...`\\n"
    await message.reply_text(text)


# ─── DRX STREAM HELPER ─────────────────────────────────────────────────────────

async def stream_drx_song(
    _,
    mystic,
    user_id,
    song_data,
    chat_id,
    user_name,
    original_chat_id,
    video=None,
    forceplay=None,
):
    """
    Stream a song from DRX API data.
    song_data is a dict from DRX API result.
    """
    title = song_data["name"]
    duration_sec = song_data.get("duration", 0)
    duration_min = seconds_to_min_str(duration_sec)
    thumbnail = get_500x500_image(song_data.get("image", []))
    audio_url = get_best_download_url(song_data.get("downloadUrl", []))
    
    if not audio_url:
        raise Exception("No download URL found for this song.")
    
    # Build details dict for the stream function
    details = {
        "title": title,
        "link": song_data.get("url", ""),
        "path": audio_url,  # Direct stream URL
        "dur": duration_sec,
        "thumb": thumbnail,
        "vidid": song_data.get("id", ""),
    }
    
    if await is_active_chat(chat_id):
        # Add to queue
        await put_queue(
            chat_id,
            original_chat_id,
            audio_url,
            title,
            duration_min,
            user_name,
            song_data.get("id", ""),
            user_id,
            "video" if video else "audio",
        )
        position = len(db.get(chat_id)) - 1
        await app.send_message(
            original_chat_id,
            text=_["queue_4"].format(position, title[:27], duration_min, user_name),
            reply_markup=InlineKeyboardMarkup(aq_markup(_, chat_id)),
        )
    else:
        if not forceplay:
            db[chat_id] = []
        
        status = True if video else None
        await AMBOTOP.join_call(chat_id, original_chat_id, audio_url, video=status, image=thumbnail)
        await put_queue(
            chat_id,
            original_chat_id,
            audio_url,
            title,
            duration_min,
            user_name,
            song_data.get("id", ""),
            user_id,
            "video" if video else "audio",
            forceplay=forceplay,
        )
        
        link = song_data.get("url", config.SUPPORT_CHAT)
        cap = await get_caption(_, link, title[:23], duration_min, user_name)
        button = stream_markup(_, chat_id)
        
        run = await app.send_message(
            original_chat_id,
            text=cap,
            link_preview_options=LinkPreviewOptions(is_disabled=False, show_above_text=True),
            reply_markup=InlineKeyboardMarkup(button),
        )
        db[chat_id][0]["mystic"] = run
        db[chat_id][0]["markup"] = "stream"


# ─── MAIN PLAY COMMAND ────────────────────────────────────────────────────────

@app.on_message(
    filters.command(
        ["play", "vplay", "cplay", "cvplay", "playforce", "vplayforce", "cplayforce", "cvplayforce"],
        prefixes=["/", "!", "%", ",", "", ".", "@", "#"],
    )
    & filters.group
    & ~BANNED_USERS
)
@PlayWrapper
async def play_commnd(
    client,
    message: Message,
    _,
    chat_id,
    video,
    channel,
    playmode,
    url,
    fplay,
):
    mystic = await message.reply_text(
        _["play_2"].format(channel) if channel else _["play_1"]
    )
    plist_id = None
    slider = None
    plist_type = None
    spotify = None
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    audio_telegram = (
        (message.reply_to_message.audio or message.reply_to_message.voice)
        if message.reply_to_message
        else None
    )

    video_telegram = (
        (message.reply_to_message.video or message.reply_to_message.document)
        if message.reply_to_message
        else None
    )
    
    # ─── TELEGRAM AUDIO REPLY ───────────────────────────────────────────────
    if audio_telegram:
        if audio_telegram.file_size > 104857600:
            return await mystic.edit_text(_["play_5"])
        duration_min = seconds_to_min(audio_telegram.duration)
        if (audio_telegram.duration) > config.DURATION_LIMIT:
            return await mystic.edit_text(
                _["play_6"].format(config.DURATION_LIMIT_MIN, app.mention)
            )
        file_path = await Telegram.get_filepath(audio=audio_telegram)
        if await Telegram.download(_, message, mystic, file_path):
            message_link = await Telegram.get_link(message)
            file_name = await Telegram.get_filename(audio_telegram, audio=True)
            dur = await Telegram.get_duration(audio_telegram, file_path)
            details = {
                "title": file_name,
                "link": message_link,
                "path": file_path,
                "dur": dur,
            }

            try:
                await stream(
                    _,
                    mystic,
                    user_id,
                    details,
                    chat_id,
                    user_name,
                    message.chat.id,
                    streamtype="telegram",
                    forceplay=fplay,
                )
            except Exception as e:
                ex_type = type(e).__name__
                err = e if ex_type == "AssistantErr" else _["general_2"].format(ex_type)
                return await mystic.edit_text(err)
            return await mystic.delete()
        return
    
    # ─── TELEGRAM VIDEO REPLY ───────────────────────────────────────────────
    elif video_telegram:
        if message.reply_to_message.document:
            try:
                ext = video_telegram.file_name.split(".")[-1]
                if ext.lower() not in formats:
                    return await mystic.edit_text(
                        _["play_7"].format(f"{' | '.join(formats)}")
                    )
            except:
                return await mystic.edit_text(
                    _["play_7"].format(f"{' | '.join(formats)}")
                )
        if video_telegram.file_size > config.TG_VIDEO_FILESIZE_LIMIT:
            return await mystic.edit_text(_["play_8"])
        file_path = await Telegram.get_filepath(video=video_telegram)
        if await Telegram.download(_, message, mystic, file_path):
            message_link = await Telegram.get_link(message)
            file_name = await Telegram.get_filename(video_telegram)
            dur = await Telegram.get_duration(video_telegram, file_path)
            details = {
                "title": file_name,
                "link": message_link,
                "path": file_path,
                "dur": dur,
            }
            try:
                await stream(
                    _,
                    mystic,
                    user_id,
                    details,
                    chat_id,
                    user_name,
                    message.chat.id,
                    video=True,
                    streamtype="telegram",
                    forceplay=fplay,
                )
            except Exception as e:
                ex_type = type(e).__name__
                err = e if ex_type == "AssistantErr" else _["general_2"].format(ex_type)
                return await mystic.edit_text(err)
            return await mystic.delete()
        return
    
    # ─── URL PROVIDED ─────────────────────────────────────────────────────────
    elif url:
        # Check for YouTube URL
        if await YouTube.exists(url):
            if "playlist" in url:
                try:
                    details = await YouTube.playlist(
                        url,
                        config.PLAYLIST_FETCH_LIMIT,
                        message.from_user.id,
                    )
                except Exception as e:
                    print(e)
                    return await mystic.edit_text(_["play_3"])
                streamtype = "playlist"
                plist_type = "yt"
                if "&" in url:
                    plist_id = (url.split("=")[1]).split("&")[0]
                else:
                    plist_id = url.split("=")[1]
                img = config.PLAYLIST_IMG_URL
                has_spoiler = True
                cap = _["play_10"]
            elif "https://youtu.be" in url:
                videoid = url.split("/")[-1].split("?")[0]
                details, track_id = await YouTube.track(f"https://www.youtube.com/watch?v={videoid}")
                streamtype = "youtube"
                img = details["thumb"]
                cap = _["play_11"].format(
                    details["title"],
                    details["duration_min"],
                )
            else:
                try:
                    details, track_id = await YouTube.track(url)
                except Exception as e:
                    print(e)
                    return await mystic.edit_text(_["play_3"])
                streamtype = "youtube"
                img = details["thumb"]
                has_spoiler = True
                cap = _["play_11"].format(
                    details["title"],
                    details["duration_min"],
                )
        elif await Spotify.valid(url):
            spotify = True
            if not config.SPOTIFY_CLIENT_ID and not config.SPOTIFY_CLIENT_SECRET:
                return await mystic.edit_text(
                    "» sᴘᴏᴛɪғʏ ɪs ɴᴏᴛ sᴜᴘᴘᴏʀᴛᴇᴅ ʏᴇᴛ.\\n\\nᴘʟᴇᴀsᴇ ᴛʀʏ ᴀɢᴀɪɴ ʟᴀᴛᴇʀ."
                )
            if "track" in url:
                try:
                    details, track_id = await Spotify.track(url)
                except:
                    return await mystic.edit_text(_["play_3"])
                streamtype = "youtube"
                img = details["thumb"]
                has_spoiler = True
                cap = _["play_10"].format(details["title"], details["duration_min"])
            elif "playlist" in url:
                try:
                    details, plist_id = await Spotify.playlist(url)
                except Exception:
                    return await mystic.edit_text(_["play_3"])
                streamtype = "playlist"
                plist_type = "spplay"
                img = config.SPOTIFY_PLAYLIST_IMG_URL
                cap = _["play_11"].format(app.mention, message.from_user.mention)
            elif "album" in url:
                try:
                    details, plist_id = await Spotify.album(url)
                except:
                    return await mystic.edit_text(_["play_3"])
                streamtype = "playlist"
                plist_type = "spalbum"
                img = config.SPOTIFY_ALBUM_IMG_URL
                cap = _["play_11"].format(app.mention, message.from_user.mention)
            elif "artist" in url:
                try:
                    details, plist_id = await Spotify.artist(url)
                except:
                    return await mystic.edit_text(_["play_3"])
                streamtype = "playlist"
                plist_type = "spartist"
                img = config.SPOTIFY_ARTIST_IMG_URL
                cap = _["play_11"].format(message.from_user.first_name)
            else:
                return await mystic.edit_text(_["play_15"])
        elif await Apple.valid(url):
            if "album" in url:
                try:
                    details, track_id = await Apple.track(url)
                except:
                    return await mystic.edit_text(_["play_3"])
                streamtype = "youtube"
                img = details["thumb"]
                has_spoiler = True
                cap = _["play_10"].format(details["title"], details["duration_min"])
            elif "playlist" in url:
                spotify = True
                try:
                    details, plist_id = await Apple.playlist(url)
                except:
                    return await mystic.edit_text(_["play_3"])
                streamtype = "playlist"
                plist_type = "apple"
                cap = _["play_12"].format(app.mention, message.from_user.mention)
                img = url
            else:
                return await mystic.edit_text(_["play_3"])
        elif await Resso.valid(url):
            try:
                details, track_id = await Resso.track(url)
            except:
                return await mystic.edit_text(_["play_3"])
            streamtype = "youtube"
            img = details["thumb"]
            has_spoiler = True
            cap = _["play_10"].format(details["title"], details["duration_min"])
        elif await SoundCloud.valid(url):
            try:
                details, track_path = await SoundCloud.download(url)
            except:
                return await mystic.edit_text(_["play_3"])
            duration_sec = details["duration_sec"]
            if duration_sec > config.DURATION_LIMIT:
                return await mystic.edit_text(
                    _["play_6"].format(
                        config.DURATION_LIMIT_MIN,
                        app.mention,
                    )
                )
            try:
                await stream(
                    _,
                    mystic,
                    user_id,
                    details,
                    chat_id,
                    user_name,
                    message.chat.id,
                    streamtype="soundcloud",
                    forceplay=fplay,
                )
            except Exception as e:
                ex_type = type(e).__name__
                err = e if ex_type == "AssistantErr" else _["general_2"].format(ex_type)
                return await mystic.edit_text(err)
            return await mystic.delete()
        else:
            # Generic URL / M3U8 / Index link
            try:
                await AMBOTOP.stream_call(url)
            except NoActiveGroupCall:
                await mystic.edit_text(_["black_9"])
                return await app.send_message(
                    chat_id=config.LOGGER_ID,
                    text=_["play_17"],
                )
            except Exception as e:
                return await mystic.edit_text(_["general_2"].format(type(e).__name__))
            await mystic.edit_text(_["str_2"])
            try:
                await stream(
                    _,
                    mystic,
                    message.from_user.id,
                    url,
                    chat_id,
                    message.from_user.first_name,
                    message.chat.id,
                    video=video,
                    streamtype="index",
                    forceplay=fplay,
                )
            except Exception as e:
                ex_type = type(e).__name__
                err = e if ex_type == "AssistantErr" else _["general_2"].format(ex_type)
                return await mystic.edit_text(err)
            return await play_logs(message, streamtype="M3u8 or Index Link")
    
    # ─── QUERY SEARCH (DRX API) ─────────────────────────────────────────────
    else:
        if len(message.command) < 2:
            buttons = botplaylist_markup(_)
            return await mystic.edit_text(
                _["play_18"],
                reply_markup=InlineKeyboardMarkup(buttons),
            )
        
        query = message.text.split(None, 1)[1]
        if "-v" in query:
            query = query.replace("-v", "")
        
        # ─── CHECK ADMIN-ADDED SONGS FIRST ──────────────────────────────────
        added_song = await get_added_song(query)
        if added_song:
            # Play the admin-added URL directly
            try:
                await mystic.edit_text(f"🎵 **Playing admin-added song...**\\n`{added_song['query']}`")
                details = {
                    "title": added_song.get("title", added_song["query"]),
                    "link": added_song["url"],
                    "path": added_song["url"],
                    "dur": 0,
                }
                await stream(
                    _,
                    mystic,
                    user_id,
                    details,
                    chat_id,
                    user_name,
                    message.chat.id,
                    video=video,
                    streamtype="index",
                    forceplay=fplay,
                )
            except Exception as e:
                ex_type = type(e).__name__
                err = e if ex_type == "AssistantErr" else _["general_2"].format(ex_type)
                return await mystic.edit_text(err)
            await mystic.delete()
            return await play_logs(message, streamtype="Admin Added Song")
        
        # ─── DRX API SEARCH ─────────────────────────────────────────────────
        slider = True
        drx_results = await drx_search_songs(query)
        
        if drx_results and len(drx_results) > 0:
            # Use the first result from DRX API
            song = drx_results[0]
            streamtype = "drx"
            
            # Build details compatible with stream function
            duration_sec = song.get("duration", 0)
            duration_min = seconds_to_min_str(duration_sec)
            thumbnail = get_500x500_image(song.get("image", []))
            audio_url = get_best_download_url(song.get("downloadUrl", []))
            
            if not audio_url:
                # Fallback to YouTube if DRX has no download URL
                try:
                    details, track_id = await YouTube.track(query)
                except:
                    return await mystic.edit_text(_["play_3"])
                streamtype = "youtube"
            else:
                # Use DRX data
                details = {
                    "title": song["name"],
                    "duration_min": duration_min,
                    "thumb": thumbnail,
                    "vidid": song.get("id", ""),
                    "filepath": audio_url,
                }
                
                if str(playmode) == "Direct":
                    # Stream directly
                    try:
                        await stream(
                            _,
                            mystic,
                            user_id,
                            details,
                            chat_id,
                            user_name,
                            message.chat.id,
                            video=video,
                            streamtype="drx",
                            forceplay=fplay,
                        )
                    except Exception as e:
                        ex_type = type(e).__name__
                        err = e if ex_type == "AssistantErr" else _["general_2"].format(ex_type)
                        return await mystic.edit_text(err)
                    await mystic.delete()
                    return await play_logs(message, streamtype="DRX API")
                else:
                    # Show track selection with slider
                    buttons = slider_markup(
                        _,
                        song.get("id", ""),
                        message.from_user.id,
                        query,
                        0,
                        "c" if channel else "g",
                        "f" if fplay else "d",
                    )
                    await mystic.delete()
                    await message.reply_photo(
                        photo=thumbnail,
                        has_spoiler=True,
                        caption=_["play_10"].format(
                            song["name"].title(),
                            duration_min,
                        ),
                        reply_markup=InlineKeyboardMarkup(buttons),
                    )
                    return await play_logs(message, streamtype="Searched on DRX")
        else:
            # Fallback to YouTube if DRX returns nothing
            try:
                details, track_id = await YouTube.track(query)
            except:
                return await mystic.edit_text(_["play_3"])
            streamtype = "youtube"
    
    # ─── DIRECT PLAY MODE ────────────────────────────────────────────────────
    if str(playmode) == "Direct":
        if not plist_type:
            if details.get("duration_min"):
                duration_sec = time_to_seconds(details["duration_min"])
                if duration_sec > config.DURATION_LIMIT:
                    return await mystic.edit_text(
                        _["play_6"].format(config.DURATION_LIMIT_MIN, app.mention)
                    )
            else:
                buttons = livestream_markup(
                    _,
                    track_id if 'track_id' in locals() else "",
                    user_id,
                    "v" if video else "a",
                    "c" if channel else "g",
                    "f" if fplay else "d",
                )
                return await mystic.edit_text(
                    _["play_13"],
                    reply_markup=InlineKeyboardMarkup(buttons),
                )
        try:
            await stream(
                _,
                mystic,
                user_id,
                details,
                chat_id,
                user_name,
                message.chat.id,
                video=video,
                streamtype=streamtype,
                spotify=spotify,
                forceplay=fplay,
            )
        except Exception as e:
            ex_type = type(e).__name__
            err = e if ex_type == "AssistantErr" else _["general_2"].format(ex_type)
            return await mystic.edit_text(err)
        await mystic.delete()
        return await play_logs(message, streamtype=streamtype)
    else:
        if plist_type:
            ran_hash = "".join(
                random.choices(string.ascii_uppercase + string.digits, k=10)
            )
            lyrical[ran_hash] = plist_id
            buttons = playlist_markup(
                _,
                ran_hash,
                message.from_user.id,
                plist_type,
                "c" if channel else "g",
                "f" if fplay else "d",
            )
            await mystic.delete()
            await message.reply_photo(
                photo=img,
                caption=cap,
                reply_markup=InlineKeyboardMarkup(buttons),
            )
            return await play_logs(message, streamtype=f"Playlist : {plist_type}")
        else:
            if slider:
                buttons = slider_markup(
                    _,
                    track_id if 'track_id' in locals() else "",
                    message.from_user.id,
                    query,
                    0,
                    "c" if channel else "g",
                    "f" if fplay else "d",
                )
                await mystic.delete()
                await message.reply_photo(
                    photo=details.get("thumb", details.get("image", config.PLAYLIST_IMG_URL)),
                    has_spoiler=True,
                    caption=_["play_10"].format(
                        details.get("title", "Unknown").title(),
                        details.get("duration_min", "00:00"),
                    ),
                    reply_markup=InlineKeyboardMarkup(buttons),
                )
                return await play_logs(message, streamtype=f"Searched on {'DRX' if streamtype == 'drx' else 'Youtube'}")
            else:
                buttons = track_markup(
                    _,
                    track_id if 'track_id' in locals() else "",
                    message.from_user.id,
                    "c" if channel else "g",
                    "f" if fplay else "d",
                )
                await mystic.delete()
                await message.reply_photo(
                    photo=img,
                    caption=cap,
                    reply_markup=InlineKeyboardMarkup(buttons),
                )
                return await play_logs(message, streamtype=f"URL Searched Inline")


# ─── CALLBACK: MusicStream (for slider/track selection) ───────────────────────

@app.on_callback_query(filters.regex("MusicStream") & ~BANNED_USERS)
@languageCB
async def play_music(client, CallbackQuery, _):
    callback_data = CallbackQuery.data.strip()
    callback_request = callback_data.split(None, 1)[1]
    vidid, user_id, mode, cplay, fplay = callback_request.split("|")
    if CallbackQuery.from_user.id != int(user_id):
        try:
            return await CallbackQuery.answer(_["playcb_1"], show_alert=True)
        except:
            return
    try:
        chat_id, channel = await get_channeplayCB(_, cplay, CallbackQuery)
    except:
        return
    user_name = CallbackQuery.from_user.first_name
    try:
        await CallbackQuery.message.delete()
        await CallbackQuery.answer()
    except:
        pass
    mystic = await CallbackQuery.message.reply_text(
        _["play_2"].format(channel) if channel else _["play_1"]
    )
    
    # Try DRX API first
    drx_results = await drx_search_songs(vidid)
    if drx_results and len(drx_results) > 0:
        song = drx_results[0]
        duration_sec = song.get("duration", 0)
        duration_min = seconds_to_min_str(duration_sec)
        thumbnail = get_500x500_image(song.get("image", []))
        audio_url = get_best_download_url(song.get("downloadUrl", []))
        
        if audio_url:
            details = {
                "title": song["name"],
                "duration_min": duration_min,
                "thumb": thumbnail,
                "vidid": song.get("id", ""),
                "filepath": audio_url,
            }
            video = True if mode == "v" else None
            ffplay = True if fplay == "f" else None
            try:
                await stream(
                    _,
                    mystic,
                    CallbackQuery.from_user.id,
                    details,
                    chat_id,
                    user_name,
                    CallbackQuery.message.chat.id,
                    video,
                    streamtype="drx",
                    forceplay=ffplay,
                )
            except Exception as e:
                ex_type = type(e).__name__
                err = e if ex_type == "AssistantErr" else _["general_2"].format(ex_type)
                return await mystic.edit_text(err)
            return await mystic.delete()
    
    # Fallback to YouTube
    try:
        details, track_id = await YouTube.track(vidid, True)
    except:
        return await mystic.edit_text(_["play_3"])
    if details["duration_min"]:
        duration_sec = time_to_seconds(details["duration_min"])
        if duration_sec > config.DURATION_LIMIT:
            return await mystic.edit_text(
                _["play_6"].format(config.DURATION_LIMIT_MIN, app.mention)
            )
    else:
        buttons = livestream_markup(
            _,
            track_id,
            CallbackQuery.from_user.id,
            mode,
            "c" if cplay == "c" else "g",
            "f" if fplay else "d",
        )
        return await mystic.edit_text(
            _["play_13"],
            reply_markup=InlineKeyboardMarkup(buttons),
        )
    video = True if mode == "v" else None
    ffplay = True if fplay == "f" else None
    try:
        await stream(
            _,
            mystic,
            CallbackQuery.from_user.id,
            details,
            chat_id,
            user_name,
            CallbackQuery.message.chat.id,
            video,
            streamtype="youtube",
            forceplay=ffplay,
        )
    except Exception as e:
        ex_type = type(e).__name__
        err = e if ex_type == "AssistantErr" else _["general_2"].format(ex_type)
        return await mystic.edit_text(err)
    return await mystic.delete()


@app.on_callback_query(filters.regex("AMBOTOPmousAdmin") & ~BANNED_USERS)
async def AMBOTOPmous_check(client, CallbackQuery):
    try:
        await CallbackQuery.answer(
            "» ʀᴇᴠᴇʀᴛ ʙᴀᴄᴋ ᴛᴏ ᴜsᴇʀ ᴀᴄᴄᴏᴜɴᴛ :\\n\\nᴏᴘᴇɴ ʏᴏᴜʀ ɢʀᴏᴜᴘ sᴇᴛᴛɪɴɢs.\\n-> ᴀᴅᴍɪɴɪsᴛʀᴀᴛᴏʀs\\n-> ᴄʟɪᴄᴋ ᴏɴ ʏᴏᴜʀ ɴᴀᴍᴇ\\n-> ᴜɴᴄʜᴇᴄᴋ ᴀɴᴏɴʏᴍᴏᴜs ᴀᴅᴍɪɴ ᴘᴇʀᴍɪssɪᴏɴs.",
            show_alert=True,
        )
    except:
        pass


@app.on_callback_query(filters.regex("AMBOTOPPlaylists") & ~BANNED_USERS)
@languageCB
async def play_playlists_command(client, CallbackQuery, _):
    callback_data = CallbackQuery.data.strip()
    callback_request = callback_data.split(None, 1)[1]
    (
        videoid,
        user_id,
        ptype,
        mode,
        cplay,
        fplay,
    ) = callback_request.split("|")
    if CallbackQuery.from_user.id != int(user_id):
        try:
            return await CallbackQuery.answer(_["playcb_1"], show_alert=True)
        except:
            return
    try:
        chat_id, channel = await get_channeplayCB(_, cplay, CallbackQuery)
    except:
        return
    user_name = CallbackQuery.from_user.first_name
    await CallbackQuery.message.delete()
    try:
        await CallbackQuery.answer()
    except:
        pass
    mystic = await CallbackQuery.message.reply_text(
        _["play_2"].format(channel) if channel else _["play_1"]
    )
    videoid = lyrical.get(videoid)
    video = True if mode == "v" else None
    ffplay = True if fplay == "f" else None
    spotify = True
    if ptype == "yt":
        spotify = False
        try:
            result = await YouTube.playlist(
                videoid,
                config.PLAYLIST_FETCH_LIMIT,
                CallbackQuery.from_user.id,
                True,
            )
        except:
            return await mystic.edit_text(_["play_3"])
    if ptype == "spplay":
        try:
            result, spotify_id = await Spotify.playlist(videoid)
        except:
            return await mystic.edit_text(_["play_3"])
    if ptype == "spalbum":
        try:
            result, spotify_id = await Spotify.album(videoid)
        except:
            return await mystic.edit_text(_["play_3"])
    if ptype == "spartist":
        try:
            result, spotify_id = await Spotify.artist(videoid)
        except:
            return await mystic.edit_text(_["play_3"])
    if ptype == "apple":
        try:
            result, apple_id = await Apple.playlist(videoid, True)
        except:
            return await mystic.edit_text(_["play_3"])
    try:
        await stream(
            _,
            mystic,
            user_id,
            result,
            chat_id,
            user_name,
            CallbackQuery.message.chat.id,
            video,
            streamtype="playlist",
            spotify=spotify,
            forceplay=ffplay,
        )
    except Exception as e:
        ex_type = type(e).__name__
        err = e if ex_type == "AssistantErr" else _["general_2"].format(ex_type)
        return await mystic.edit_text(err)
    return await mystic.delete()


@app.on_callback_query(filters.regex("slider") & ~BANNED_USERS)
@languageCB
async def slider_queries(client, CallbackQuery, _):
    callback_data = CallbackQuery.data.strip()
    callback_request = callback_data.split(None, 1)[1]
    (
        what,
        rtype,
        query,
        user_id,
        cplay,
        fplay,
    ) = callback_request.split("|")
    if CallbackQuery.from_user.id != int(user_id):
        try:
            return await CallbackQuery.answer(_["playcb_1"], show_alert=True)
        except:
            return
    what = str(what)
    rtype = int(rtype)
    
    # Try DRX API for slider
    drx_results = await drx_search_songs(query)
    
    if what == "F":
        if rtype == 9:
            query_type = 0
        else:
            query_type = int(rtype + 1)
        try:
            await CallbackQuery.answer(_["playcb_2"])
        except:
            pass
        
        if drx_results and query_type < len(drx_results):
            song = drx_results[query_type]
            duration_min = seconds_to_min_str(song.get("duration", 0))
            thumbnail = get_500x500_image(song.get("image", []))
            buttons = slider_markup(_, song.get("id", ""), user_id, query, query_type, cplay, fplay)
            med = InputMediaPhoto(
                media=thumbnail,
                caption=_["play_10"].format(
                    song["name"].title(),
                    duration_min,
                ),
            )
            return await CallbackQuery.edit_message_media(
                media=med, reply_markup=InlineKeyboardMarkup(buttons)
            )
        else:
            # Fallback to YouTube slider
            title, duration_min, thumbnail, vidid = await YouTube.slider(query, query_type)
            buttons = slider_markup(_, vidid, user_id, query, query_type, cplay, fplay)
            med = InputMediaPhoto(
                media=thumbnail,
                caption=_["play_10"].format(
                    title.title(),
                    duration_min,
                ),
            )
            return await CallbackQuery.edit_message_media(
                media=med, reply_markup=InlineKeyboardMarkup(buttons)
            )
    
    if what == "B":
        if rtype == 0:
            query_type = 9
        else:
            query_type = int(rtype - 1)
        try:
            await CallbackQuery.answer(_["playcb_2"])
        except:
            pass
        
        if drx_results and query_type < len(drx_results):
            song = drx_results[query_type]
            duration_min = seconds_to_min_str(song.get("duration", 0))
            thumbnail = get_500x500_image(song.get("image", []))
            buttons = slider_markup(_, song.get("id", ""), user_id, query, query_type, cplay, fplay)
            med = InputMediaPhoto(
                media=thumbnail,
                has_spoiler=True,
                caption=_["play_10"].format(
                    song["name"].title(),
                    duration_min,
                ),
            )
            return await CallbackQuery.edit_message_media(
                media=med, reply_markup=InlineKeyboardMarkup(buttons)
            )
        else:
            # Fallback to YouTube slider
            title, duration_min, thumbnail, vidid = await YouTube.slider(query, query_type)
            buttons = slider_markup(_, vidid, user_id, query, query_type, cplay, fplay)
            med = InputMediaPhoto(
                media=thumbnail,
                has_spoiler=True,
                caption=_["play_10"].format(
                    title.title(),
                    duration_min,
                ),
            )
            return await CallbackQuery.edit_message_media(
                media=med, reply_markup=InlineKeyboardMarkup(buttons)
            )
