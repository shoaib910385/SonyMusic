import aiohttp
import io
import os
import asyncio
import traceback
from pyrogram.enums import ButtonStyle
from pyrogram import filters
from pyrogram.enums import ParseMode
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from PIL import Image, ImageDraw, ImageFont
from RessoMusic import app

# Automatically detect the folder where the script is located
current_dir = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_PATH = os.path.join(current_dir, "balance_base.png")
FONT_PATH = os.path.join(current_dir, "Poppins-Bold.ttf")

MARKETPLACE_BUTTON = InlineKeyboardMarkup(
    [[InlineKeyboardButton("◍ Join Channel ◍", url="https://t.me/itzdhruv1060", icon_custom_emoji_id=5409194306365829029, style=ButtonStyle.PRIMARY)]]
)

async def delete_after_delay(messages: list, delay: int = 300):
    """Deletes messages after a specified delay in seconds."""
    await asyncio.sleep(delay)
    for msg in messages:
        try:
            await msg.delete()
        except:
            pass

async def get_balance_logic(client, message: Message, target_input: str, is_username: bool):
    # Determine display name and API target
    if not is_username:
        api_target = target_input
        display_name = f"{target_input[:6]}...{target_input[-4:]}"
    else:
        dns_target = f"{target_input}.t.me"
        display_name = f"@{target_input}"

    msg = await message.reply_text(f"<emoji id=5778421276024509124>◍</emoji> Fetching balance for {display_name}...")

    try:
        async with aiohttp.ClientSession() as session:
            # --- DNS RESOLUTION ---
            if is_username:
                async with session.get(f"https://tonapi.io/v2/dns/{dns_target}") as resp_dns:
                    dns_data = await resp_dns.json()
                
                if "error" in dns_data:
                    await msg.edit_text("❌ **Error:** Could not resolve username on TON DNS.")
                    asyncio.create_task(delete_after_delay([msg, message]))
                    return

                try:
                    if "item" in dns_data and "owner" in dns_data["item"]:
                        api_target = dns_data["item"]["owner"]["address"]
                    elif "wallet" in dns_data and "address" in dns_data["wallet"]:
                        api_target = dns_data["wallet"]["address"]
                    else:
                        await msg.edit_text("❌ **Error:** No wallet linked to this username.")
                        asyncio.create_task(delete_after_delay([msg, message]))
                        return
                except KeyError:
                    await msg.edit_text("❌ **Error:** Could not parse DNS data.")
                    asyncio.create_task(delete_after_delay([msg, message]))
                    return

            # --- FETCH ACCOUNT INFO ---
            async with session.get(f"https://tonapi.io/v2/accounts/{api_target}") as resp_acc:
                acc_data = await resp_acc.json()
                
            if "error" in acc_data:
                err_msg = acc_data.get("error", "")
                await msg.edit_text(f"❌ **API Error:** ")
                asyncio.create_task(delete_after_delay([msg, message]))
                return

            # Fetch Rates
            async with session.get("https://tonapi.io/v2/rates?tokens=ton&currencies=usd,inr") as resp_rates:
                rates_data = await resp_rates.json()

        # Parse Data
        nano_balance = int(acc_data.get("balance", 0))
        ton_balance = nano_balance / 1e9
        usd_rate = float(rates_data["rates"]["TON"]["prices"]["USD"])
        inr_rate = float(rates_data["rates"]["TON"]["prices"]["INR"])

        usd_str = f"${(ton_balance * usd_rate):,.2f}"
        inr_str = f"₹{(ton_balance * inr_rate):,.2f}"
        ton_str = f"{ton_balance:,.2f}"

        # --- IMAGE GENERATION ---
        if not os.path.exists(TEMPLATE_PATH):
            return await msg.edit_text("❌ **Template image missing!**")

        img = Image.open(TEMPLATE_PATH)
        draw = ImageDraw.Draw(img)
        try:
            font_title = ImageFont.truetype(FONT_PATH, 190)
            font_values = ImageFont.truetype(FONT_PATH, 170)
        except:
            return await msg.edit_text("❌ **Font file error!**")

        WHITE, DARK_GREY = (255, 255, 255), (90, 90, 90)
        img_width, _ = img.size
        draw.text((img_width / 2, 170), f"{display_name}'s Balance", font=font_title, fill=WHITE, anchor="mt")
        
        right_align_x = img_width - 376
        draw.text((right_align_x, 800), ton_str, font=font_values, fill=DARK_GREY, anchor="rm")
        draw.text((right_align_x, 1190), usd_str, font=font_values, fill=DARK_GREY, anchor="rm")
        draw.text((right_align_x, 1600), inr_str, font=font_values, fill=DARK_GREY, anchor="rm")

        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)
        
        caption = (
            f"<b>{display_name} 's balance <emoji id=5778421276024509124>◍</emoji></b>\n"
            f"<blockquote expandable><b>TON:</b> {ton_str} <emoji id=6030549140633555631>◍</emoji>\n"
            f"<b>USD:</b> {usd_str} <emoji id=6028584717081645421>◍</emoji>\n"
            f"<b>INR:</b> {inr_str} <emoji id=5042334757040423886>◍</emoji></blockquote>\n"
        )

        final_msg = await message.reply_photo(
            photo=img_byte_arr, 
            has_spoiler=True, 
            caption=caption, 
            parse_mode=ParseMode.HTML,
            reply_markup=MARKETPLACE_BUTTON
        )
        await msg.delete()
        
        # Schedule deletion for command and bot result
        asyncio.create_task(delete_after_delay([message, final_msg]))

    except Exception:
        traceback.print_exc()
        await msg.edit_text("❌ Critical Error")
        asyncio.create_task(delete_after_delay([msg, message]))

@app.on_message(filters.command("balance"))
async def bal_command(client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text("❌ Please provide NFT username or TON address.\nExample: `/balance @juli`")

    raw_input = message.command[1].lower()
    target = raw_input.replace("https://", "").replace("http://", "").replace("t.me/", "").replace("@", "").strip("/")

    if len(target) > 20 and not target.endswith(".t.me") and not target.endswith(".ton"):
        await get_balance_logic(client, message, target, False)
    else:
        clean_username = target.replace(".t.me", "").replace(".ton", "")
        await get_balance_logic(client, message, clean_username, True)

@app.on_message(filters.command("myton"))
async def myton_command(client, message: Message):
    if not message.from_user or not message.from_user.username:
        return await message.reply_text("❌ You need to set a Telegram username to use this command.")
    
    await get_balance_logic(client, message, message.from_user.username.lower(), True)
