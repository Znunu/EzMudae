from __future__ import annotations
import enum
import asyncio
import time
import argparse
import re

BIT_SIZE = 16
MUDA = 432610292342587392

class Waifu:
    """
    Represents a waifu from mudae.

    A lot of the attributes will often be null since they either:
        a. Are not applicable
        b. Can't be read from the waifu message
        c. Need to be fetched with the methods
    Attributes
    ----------
    mudae: discord.User
        The mudae bot that created this waifu.
    user: discord.Client
        The client that's using this waifu.
    message: discord.Message
        The waifu message the waifu came from.
    owner: discord.Member
        The member whose harem the waifu belongs to.
    creator: discord.Member
        The member that rolled this waifu.
    suitors: list[discord.Member]
        A list of members who wished the waifu.
    name: str
        The name of the waifu.
    series: str
        The series the waifu belongs to.
    kakera: int
        The kakera value of the waifu.
    key: int
        The key level of the waifu.
    claims: int
        The claims rank of the waifu.
    likes: int
        The likes rank of the waifu
    type: Waifu.Type
        The type of the waifu.
    image: str
        URL of the image, that the waifu message had, when the object was created.
    image_count: int
        How many images the waifu has available in total.
    image_index: int
        Image index of the image attribute with respect to the avaliable images.
    image_extra: int
        How many extra images have been added to the waifu.
    is_claimed: bool
        If the waifu has been claimed yet.
    is_roll: bool
        If the waifu is a roll.
    is_girl: bool
        If the waifu is female or both female and male.
    Methods
    -------
    async fetch_extra()
        Fills the suitor and creator attributes.
    async await_claim()
        Waits for a member to claim this waifu, then returns with that member.
    """

    class Type(enum.Enum):
        """
        Represents the different types of waifus.
        Enums
        -----
        roll: 0
            The waifu was rolled e.g. created with $w.
        info: 1
            The waifu came from the info command e.g. created with $im.
        """

        roll = enum.auto()
        info = enum.auto()

    def __init__(self, mudae, user, message):
        self.mudae = mudae
        self.message = message
        self.user = user
        self.suitors = []
        self.name = None
        self.series = None
        self.kakera = None
        self.key = None
        self.claims = None
        self.likes = None
        self.owner = None
        self.image = None
        self.creator = None
        self.image_count = None
        self.image_index = None
        self.image_extra = None
        self.type = None
        # self.ka_react = None
        # self.is_claimed, self.is_girl and self.is_roll won't be initialized to avoid them being accidentally interpreted as False

        # Message is missing parts to match against and can't be a match
        if message.author != self.mudae or not len(message.embeds) == 1 or message.embeds[0].image.url == message.embeds[0].Empty:
            raise TypeError("Message passed to the Waifu constructor it not a valid mudae message")

        embed = message.embeds[0]
        desc = embed.description + "\n"
        self.name = embed.author.name
        self.image = embed.image.url

        def match_n_replace(pattern: str, string: str):
            match = re.search(pattern, desc, re.DOTALL)
            if match:
                string = string.replace(match.group(0), "", 1)
                match = match.group(1).replace("\n", " ").strip()
            return match, string

        # Extract series
        # language=RegExp
        self.series, desc = match_n_replace(r"^([^<\n]*)\n?", desc)

        # Extract kakera
        # language=RegExp
        self.kakera, desc = match_n_replace(r"\*\*(\d+?)\*\*<.*>\n", desc)
        self.kakera = int(self.kakera)

        if self.series:
            self.type = self.Type.roll
            self.is_roll = True

        # Try to match to infos:
        match = re.search(r"""^(.*)                #From the start of the string, series captured
                               \ <:(.+?):\d+?>.*?     #First emoji, gender captured
                               \*\*(\d*)              #Kakera Value captured
                               [^(]*                  #Consume until "claim", but stop if hit bracket, to allow key to be captured
                               (?:\((\d*)\))?.*       #Optionally capture key value
                               Claims:\ \#(\d*).*?    #Claims captured
                               Likes:\ \#(\d*)        #Likes captured
                               """, desc, re.DOTALL | re.VERBOSE)
        if match:
            self.series = match.group(1).replace("\n", " ")
            if match.group(2) == "female":
                self.is_girl = True
            else:
                self.is_girl = False
            self.kakera = int(match.group(3))
            if match.group(4):
                self.key = int(match.group(4))
            else:
                self.key = 0
            self.claims = int(match.group(5))
            self.likes = int(match.group(6))
            self.type = self.Type.info
            self.is_roll = False

        # Did it match?
        if not self.series:
            raise TypeError("Message passed to the Waifu constructor it not a valid mudae message")

        # Try to match footer:
        if not embed.footer.text:
            self.is_claimed = False
        else:
            match = re.search(r"""(?:Belongs\ to\ (.+?))? #Optionally capture owner
                                   (?:\ ~~\ )?               #Optionally match separator
                                   (?:                       #----> Optionally capture image data
                                       (\d+?)                    #Capture first index
                                       \ /\ (\d+)                #Capture second index
                                       (?:\ \[(\d+?)\])?         #Optionally capture third index
                                   )?$                       #<----- end of string
                                   """, embed.footer.text, re.VERBOSE | re.DOTALL)
            if match.group(1):
                self.owner = message.guild.get_member_named(match.group(1))
                self.is_claimed = True
            else:
                self.is_claimed = False
            if match.group(2):
                self.image_index = int(match.group(2))
            if match.group(3):
                self.image_count = int(match.group(3))
            if match.group(4):
                self.image_extra = int(match.group(4))
            else:
                self.image_extra = 0

    async def fetch_extra(self):
        """
        Fills the suitor and creator attributes.
        The suitor and creator attributes are by default empty and null respectively. To get the real values, this method must be called.
        The method will only work for waifus of type roll and only if the waifu was just rolled.
        """

        state = 0
        async for message in self.message.channel.history(limit=10):
            if state == 0:
                if message.id == self.message.id:
                    state = 1
            elif state == 1:
                state += 1
                if message.author != self.mudae:
                    self.creator = message.author
                    break
                elif "wished" in message.content.lower():
                    self.suitors = message.mentions
            elif state == 5:
                break
            else:
                state += 1
                if message.author != self.mudae:
                    self.creator = message.author
                    break

        # await asyncio.sleep(1)
        # UNTESTED ------------------->
        """
        self.message = await self.message.channel.fetch_message(self.message_id)
        if self.is_claimed and self.is_roll:
            for react in self.message.reactions:
                name = react.emoji.name
                if "kakera" in name:
                    name = name.replace("kakera", "")
                    if name == "":
                        name = "K"
                    self.ka_react = name
                    break
        """

    async def await_claim(self):
        """
        Waits for a member to claim this waifu, then returns with that member.
        If the waifu has already been claimed, the owner is returned immediately.
        If the waifu doesn't have an owner, the function will wait for up to 60s for someone to claim.
        Returns none if after 60s no one has claimed.
        Returns
        -------
        Waifu
            The waifu has an owner or one is found.
        None
            No owner could be found, the waifu wasn't claimed within 60s.
        """

        if self.is_claimed:
            return self.owner

        def check(message):
            return message.author == self.mudae and self.name in message.content and "are now married" in message.content.lower()

        try:
            message = await self.user.wait_for("message", timeout=60, check=check)
            user_name = message.content.split("**")[1]
            self.owner = message.guild.get_member_named(user_name)
            self.is_claimed = True
            return self.owner

        except asyncio.TimeoutError:
            return None


    def __str__(self):
        return self.name


class Mudae:
    """
    Represents a mudae bot. Primarily used as a factory for Waifu objects.
    Before doing anything with this class, make sure you've configured your mudae bot properly.
    Kakera value must be visible on rolls, for this class to be able to read the messages from mudae.
    If you want to check for claim or roll resets, you must provide the optional timing parameter
    ----------
    mudae: discord.User
        The mudea bot.
    user: discord.Client
        The client that's using this class.
    has_timing: bool
        If the module was created
    Methods
    -------
    waifu_from(message)
        Returns a waifu from a waifu message.
    is_wish(message, wishes, check_name, check_series)
        Checks if the waifu from a waifu message is part of a list of wishes.
    until_roll(in_seconds)
        Returns how much time there's left until the next roll reset.
    until_claim(in_seconds)
        Returns how much time there's left until the next claim reset.
    async wait_roll()
         Pauses until next roll reset.
    async wait_claim()
         Pauses until next claim reset.
    """

    def __init__(self, user, timing: int=None):
        """
        Parameters
        ----------
        user: discord.Client
            The client that's using this class.
        timing: int
            Value encoded with information on claim and roll resets. Use the get_timing method to create one.
        """

        self.user = user
        self.mudae = user.get_user(MUDA)

        if timing:
            timings = _split_timing(timing)
            self._roll_mod = timings[0]
            self._claim_mod = timings[1]
            self._roll_rem = timings[2]
            self._claim_rem = timings[3]
            self.has_timing = True
        else:
            self.has_timing = False


    def waifu_from(self, message):
        """
        Returns a waifu from a message.
        Currently two types of messages are supported, rolls and infoes. Rolls are usually created with the $w command, and infoes with the $im command.
        If the message supplied is none of the two valid types of messages, or is not valid for another reason, none is returned.
        Parameters
        ----------
        message: discord.Message
            A discord message from mudae with a waifu (a waifu message).
        Returns
        -------
        Waifu
            A waifu created from the message.
        None
            The message isn't valid.
        """

        try:
            return Waifu(self.mudae, self.user, message)
        except TypeError:
            return None

    def from_wish(self, message, wishes: list[str], check_name: bool=True, check_series: bool=False):
        """
        Checks if the waifu from a waifu message is part of a list of wishes.
        If both check_name and check_series are true, the wishes will be checked against both name and series.
        If both are false, the function will always return false.
        Parameters
        ----------
        message: discord.Message
            A discord waifu message.
        wishes: list
            A list of strings, where each string is a wish.
        check_name: bool
            Whether the wishes are wishes for specific waifus.
        check_series: bool
            Whether the wishes are wishes for specific series.
        Returns
        -------
        bool
            Whether the waifu was wished.
        """
        waifu = self.waifu_from(message)
        wishes = map(lambda wish: wish.lower(), wishes)
        if not waifu:
            return None
        if check_name and waifu.name.lower() in wishes:
            return waifu
        if check_series and waifu.series.lower() in wishes:
            return waifu
        return False

    def until_roll(self, in_seconds: bool=False):
        """
        Returns how much time there's left until the next roll reset.
        Parameters
        ----------
        in_seconds: bool
            Whether the time returned should be in seconds or minutes.
        Returns
        -------
        int
            The time left until next roll reset.
        """

        if not self.has_timing:
            raise TypeError("Missing cooldown data")
        left = self._roll_rem - (int(time.time()) % self._roll_mod)
        if left < 0:
            left += self._roll_mod
        if not in_seconds:
            left = int(left / 60)
        return left

    def until_claim(self, in_seconds: bool=False):
        """
        Returns how much time there's left until the next claim reset.
        Parameters
        ----------
        in_seconds: bool
            Whether the time returned should be in seconds or minutes.
        Returns
        -------
        int
            The time left until next claim reset.
        """

        if not self.has_timing:
            raise TypeError("Missing cooldown data")
        left = self._claim_rem - (int(time.time()) % self._claim_mod)
        if left < 0:
            left += self._claim_mod
        if not in_seconds:
            left = int(left / 60)
        return left

    async def wait_roll(self):
        """
        Pauses until next roll reset.
        """

        await asyncio.sleep(5)
        await asyncio.sleep(self.until_roll(True))

    async def wait_claim(self):
        """
        Pauses until next claim reset.
        """

        await asyncio.sleep(5)
        await asyncio.sleep(self.until_claim(True))


def get_timing(roll_mod: int, claim_mod: int, roll_rem: int, claim_rem: int, in_seconds=False) -> int:
    """
     A static method that returns an integer from the supplied parameters.
     The integer may be provided to the Mudae constructor to enable roll and claim cool-down functionality
     Parameters
     ----------
     roll_mod: int
         The time period, between roll resets. The default mudae value for this is 60 min.
     claim_mod: int
         The time period, between claim resets. The default mudae value for this is 120 min.
     roll_rem: int
         The time period, from now until the next roll reset.
     claim_rem: int
         The time period, from now until the next claim reset.
     in_seconds: bool
         If the time periods are given as seconds or minutes.
     """

    if not in_seconds:
        roll_mod *= 60
        claim_mod *= 60
        roll_rem *= 60
        claim_rem *= 60

    timings = 0
    roll_rem = (int(time.time()) + roll_rem) % roll_mod
    claim_rem = (int(time.time()) + claim_rem) % claim_mod
    for value in (roll_mod, claim_mod, roll_rem, claim_rem):
        timings <<= BIT_SIZE
        timings += value
    return timings


def _split_timing(timing: int) -> tuple[int]:
    mask = (1 << BIT_SIZE + 1) - 1
    nums = []
    for _ in range(4):
        nums.append(timing & mask)
        timing >>= BIT_SIZE
    return tuple(nums)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--rr", type=int, help="Time until next roll reset", required=True)
    parser.add_argument("--cr", type=int, help="Time until next claim reset", required=True)
    parser.add_argument("--rm", type=int, help="Time period between each roll reset (Defaults to 60)", default=60)
    parser.add_argument("--cm", type=int, help="Time period between each claim reset (Defaults to 180)", default=180)
    args = parser.parse_args()
    print(get_timing(args.rm, args.cm, args.rr, args.cr))
