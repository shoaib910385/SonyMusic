from RessoMusic.core.bot import AMBOTOP
from RessoMusic.core.dir import dirr
from RessoMusic.core.git import git
from RessoMusic.core.userbot import Userbot
from RessoMusic.misc import dbb, heroku

from .logging import LOGGER

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
