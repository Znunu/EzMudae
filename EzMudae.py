from __future__ import annotations
import enum
import asyncio
import time
import argparse
import re

import parse

BIT_SIZE = 16
MUDA = 432610292342587392
EMOJI_FEMALE = "<:female:452463537508450304>"
EMOJI_MALE = "<:male:452470164529872899>"
EMOJI_KAKERA = "<:kakera:469835869059153940>"


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


    class Gender(enum.Enum):
        """
        Represents the different genders of waifus.
        Enums
        -----
        female: 0
            The waifu is female.
        male: 1
            The waifu is male.
        """

        female = enum.auto()
        male = enum.auto()

    def __init__(self, mudae, user, message):
        self.mudae = mudae
        self.message = message
        self.user = user
        self.suitors = []  # Needs to be fetched with fetch_extra
        self.name = None  # Name of the waifu, appears in the title of im and w
        self.series = None  # Series the waifu belongs to, appears in the description of im and w
        self.kakera = None  # Kakera value. Always appears in the description of w and optional in im
        self.claims = None  # Claims rank, appears in the description of w
        self.likes = None  # Likes rank, appears in the description of w
        self.owner = None  # Optionally appears in the footer of im and w
        self.image = None  # URL of the image, appears in im and w
        self.creator = None  # Needs to be fetched with fetch_extra
        self.gender = None  # Appears only in the description of im
        self.type = None

        # Message is missing parts to match against and can't be a match
        if message.author != self.mudae or not len(message.embeds) == 1 or message.embeds[0].image is None:
            raise TypeError("Message passed to the Waifu constructor it not a valid mudae message")

        embed = message.embeds[0]
        desc = embed.description
        lines = desc.split("\n")
        self.name = embed.author.name
        self.image = embed.image.url

        first_line = lines[0]
        if EMOJI_MALE in first_line:
            self.gender = self.Gender.male
            first_line = first_line.replace(EMOJI_MALE, "")
        elif EMOJI_FEMALE in first_line:
            self.gender = self.Gender.female
            first_line = first_line.replace(EMOJI_FEMALE, "")
        self.series = first_line.strip()

        if "React with any emoji to claim!" in lines:
            self.type = self.Type.roll
        else:
            self.type = self.Type.info

        for line in lines:
            if EMOJI_KAKERA in line:
                self.kakera = parse.search("**{}**", line)[0]
            elif "Claim Rank" in line:
                self.claims = parse.search("Claim Rank: #{:d}", line)[0]
            elif "Like Rank" in line:
                self.likes = parse.search("Like Rank: #{:d}", line)[0]

        footer = embed.footer.text
        if footer is not None:
            match = parse.search("Belongs to {} ~~", footer)
            if match is not None:
                self.owner = match[0].strip()
                self.is_claimed = True
            else:
                self.is_claimed = False

    async def fetch_extra(self):
        """
        Fills the suitor and creator attributes, by reading messages sent before and after the waifu.
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
        Currently two types of messages are supported, rolls and infos. Rolls are usually created with the $w command, and infoes with the $im command.
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

        return Waifu(self.mudae, self.user, message)

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
    all_vals = (roll_mod, claim_mod, roll_rem, claim_rem)
    for value in reversed(all_vals):
        timings <<= BIT_SIZE
        timings += value
    return timings


def _split_timing(timing: int) -> tuple[int,...]:
    mask = (1 << BIT_SIZE) - 1
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
