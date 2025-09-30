import asyncio, os, re, httpx, aiofiles.os
from io import BytesIO 
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps
from aiofiles.os import path as aiopath
from youtubesearchpython.__future__ import VideosSearch

from ..logging import LOGGER

def load_fonts():
    try:
        return {
            "cfont": ImageFont.truetype("RessoMusic/assets/cfont.ttf", 24),
            "tfont": ImageFont.truetype("RessoMusic/assets/font.ttf", 30),
        }
    except Exception as e:
        LOGGER.error("Font loading error: %s, using default fonts", e)
        return {
            "cfont": ImageFont.load_default(),
            "tfont": ImageFont.load_default(),
        }

FONTS = load_fonts()


FALLBACK_IMAGE_PATH = "RessoMusic/assets/controller.png"

YOUTUBE_IMG_URL = "https://i.ytimg.com/vi/default.jpg"

async def resize_youtube_thumbnail(img: Image.Image) -> Image.Image:
    target_width, target_height = 1280, 720
    aspect_ratio = img.width / img.height
    target_ratio = target_width / target_height

    if aspect_ratio > target_ratio:
        new_height = target_height
        new_width = int(new_height * aspect_ratio)
    else:
        new_width = target_width
        new_height = int(new_width / aspect_ratio)

    img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
    left = (new_width - target_width) // 2
    top = (new_height - target_height) // 2
    right = left + target_width
    bottom = top + target_height

    img = img.crop((left, top, right, bottom))
    enhanced = ImageEnhance.Sharpness(img).enhance(1.5)
    img.close()
    return enhanced

async def fetch_image(url: str) -> Image.Image:
    async with httpx.AsyncClient() as client:
        try:
            if not url:
                raise ValueError("No thumbnail URL provided")
            response = await client.get(url, timeout=5)
            response.raise_for_status()
            img = Image.open(BytesIO(response.content)).convert("RGBA")
            if url.startswith("https://i.ytimg.com"):
                img = await resize_youtube_thumbnail(img)
            else:
                img.close()
                img = Image.new("RGBA", (1280, 720), (255, 255, 255, 255))
            return img
        except Exception as e:
            LOGGER.error("Image loading error for URL %s: %s", url, e)
            try:
                response = await client.get(YOUTUBE_IMG_URL, timeout=5)
                response.raise_for_status()
                img = Image.open(BytesIO(response.content)).convert("RGBA")
                img = await resize_youtube_thumbnail(img)
                return img
            except Exception as e:
                LOGGER.error("YouTube fallback image error: %s", e)
                try:
                    async with aiofiles.open(FALLBACK_IMAGE_PATH, mode="rb") as f:
                        img = Image.open(BytesIO(await f.read())).convert("RGBA")
                    img = await resize_youtube_thumbnail(img)
                    return img
                except Exception as e:
                    LOGGER.error("Local fallback image error: %s", e)
                    return Image.new("RGBA", (1280, 720), (255, 255, 255, 255))

def clean_text(text: str, limit: int = 25) -> str:
    if not text:
        return "Unknown"
    text = text.strip()
    return f"{text[:limit - 3]}..." if len(text) > limit else text

async def add_controls(img: Image.Image) -> Image.Image:
    img = img.filter(ImageFilter.GaussianBlur(radius=10))
    box = (305, 125, 975, 595)
    region = img.crop(box)
    try:
        controls = Image.open("RessoMusic/assets/controls.png").convert("RGBA")
        controls = controls.resize((1200, 320), Image.Resampling.LANCZOS)
        controls = ImageEnhance.Sharpness(controls).enhance(5.0)
        controls = ImageEnhance.Contrast(controls).enhance(1.0)
        controls = controls.resize((600, 160), Image.Resampling.LANCZOS)
        controls_x = 305 + (670 - 600) // 2 
        controls_y = 415  
    except Exception as e:
        LOGGER.error("Controls image loading error: %s", e)
        controls = Image.new("RGBA", (600, 160), (0, 0, 0, 0))
        controls_x, controls_y = 335, 415


    dark_region = ImageEnhance.Brightness(region).enhance(0.5)
    mask = Image.new("L", dark_region.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (0, 0, box[2] - box[0], box[3] - box[1]), radius=20, fill=255
    )

    img.paste(dark_region, box, mask)
    img.paste(controls, (controls_x, controls_y), controls)
    
    region.close()
    controls.close()
    return img

def make_rounded_rectangle(image: Image.Image, size: tuple = (184, 184)) -> Image.Image:
    width, height = image.size
    side_length = min(width, height)
    crop = image.crop(
        (
            (width - side_length) // 2,
            (height - side_length) // 2,
            (width + side_length) // 2,
            (height + side_length) // 2,
        )
    )
    resize = crop.resize(size, Image.Resampling.LANCZOS)
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, *size), radius=20, fill=255)

    rounded = ImageOps.fit(resize, size)
    rounded.putalpha(mask)
    crop.close()
    resize.close()
    return rounded

async def get_thumb(videoid: str) -> str:
    if not videoid or not re.match(r"^[a-zA-Z0-9_-]{11}$", videoid):
        LOGGER.error("Invalid YouTube video ID: %s", videoid)
        return ""

    save_dir = f"database/photos/{videoid}.png"

    try:
        save_dir_parent = "database/photos"
        if not await aiopath.exists(save_dir_parent):
            await asyncio.to_thread(os.makedirs, save_dir_parent)
    except Exception as e:
        LOGGER.error("Failed to create directory %s: %s", save_dir_parent, e)
        return ""

    try:
        url = f"https://www.youtube.com/watch?v={videoid}"
        results = VideosSearch(url, limit=1)
        result = (await results.next())["result"][0]
        title = clean_text(result.get("title", "Unknown Title"), limit=25)
        artist = clean_text(result.get("channel", {}).get("name", "Unknown Artist"), limit=28)
        thumbnail_url = result.get("thumbnails", [{}])[0].get("url", "").split("?")[0]
    except Exception as e:
        LOGGER.error("YouTube metadata fetch error for video %s: %s", videoid, e)
        title, artist = "Unknown Title", "Unknown Artist"
        thumbnail_url = YOUTUBE_IMG_URL

    thumb = await fetch_image(thumbnail_url)
    bg = await add_controls(thumb)
    image = make_rounded_rectangle(thumb, size=(184, 184))

    paste_x, paste_y = 325, 155 
    bg.paste(image, (paste_x, paste_y), image)

    
    draw = ImageDraw.Draw(bg)
    draw.text((540, 155), title, (255, 255, 255), font=FONTS["tfont"])  
    draw.text((540, 200), artist, (255, 255, 255), font=FONTS["cfont"]) 


    bg = ImageEnhance.Contrast(bg).enhance(1.1)
    bg = ImageEnhance.Color(bg).enhance(1.2)


    try:
        await asyncio.to_thread(bg.save, save_dir, format="PNG", quality=95, optimize=True)
        if await aiopath.exists(save_dir):
            thumb.close()
            image.close()
            bg.close()
            return save_dir
        LOGGER.error("Failed to save thumbnail at %s", save_dir)
    except Exception as e:
        LOGGER.error("Thumbnail save error for %s: %s", save_dir, e)

    thumb.close()
    image.close()
    bg.close()
    return ""
