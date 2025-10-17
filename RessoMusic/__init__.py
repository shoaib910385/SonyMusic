import asyncio
from RessoMusic.core.bot import AMBOTOP
from RessoMusic.core.dir import dirr
from RessoMusic.core.git import git
from RessoMusic.core.userbot import Userbot
from RessoMusic.misc import dbb, heroku

from .logging import LOGGER

# Ensure there's an event loop set for the main thread (fixes
# RuntimeError: There is no current event loop in thread 'MainThread')
try:
    # Python 3.7+: get_running_loop raises if no loop is running
    asyncio.get_running_loop()
except RuntimeError:
    # No running loop — create and set one for this thread
    asyncio.set_event_loop(asyncio.new_event_loop())

dirr()
git()
dbb()
heroku()

app = AMBOTOP()
userbot = Userbot()


from .platforms import *

Apple = AppleAPI()
Carbon = CarbonAPI()
SoundCloud = SoundAPI()
Spotify = SpotifyAPI()
Resso = RessoAPI()
Telegram = TeleAPI()
YouTube = YouTubeAPI()


