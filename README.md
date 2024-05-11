# EzMudae
Module for Discord.py that parses messages and handling claim/roll resets from the Mudae bot. Will only work, if you've enabled visble kakera value on your rolls. 

Documentation is [here](https://git.orz.cx/EzMudae/), every function is extensively documented. Join [my discord server](https://discord.gg/kw6PCBaW5y) for help. This repo is for someone experienced with python programming and discord.py. If you aren't, and just need a (user/self)bot to cheat with, check out [my other repo](https://github.com/Znunu/Mudae-Cheat).

### Install
Copy the ezmudae.py file into your project folder

### Getting the name, series and kakera value from a waifu
```python
# Imports the only code in EzMudae, the Mudae class
from EzMudae import Mudae

bot     #A discord.py client
mudae   #Discord.py member representing the mudae bot

async def on_message(message)

      # Creates a new Mudae object
      mudae_wrap = Mudae(bot, mudae)

      # Parses the message and returns the waifu object
      waifu = mudae_wrap.waifu_from(message)

      # If the message was a random message or not from mudae, the returned value will be none
      if (waifu):
            waifu.name   #Name of the waifu
            waifu.series #Series of the waifu
            waifu.kakera #Kakera value
```

### Sending a message on roll reset
```python
channel      #The discord.py channel where we will send a message
bot          #A discord.py client
mudae        #Discord.py member representing the mudae bot
roll_period  #The time period, in minutes, between roll resets.
claim_period #The time period, in minutes, between claim resets.
roll_left    #The time period, in minutes, from now until the next roll reset.
claim_left   #The time period, in minutes, from now until the next claim reset.


# Imports the only code in EzMudae, the Mudae class
from EzMudae import Mudae

# Creates a timing list
timing = Mudae.get_timing(roll_period, claim_period, roll_left, claim_left)

# Creates a new Mudae object
mudae_wrap = Mudae(bot, mudae, timing)

# Sleeps until the next roll reset
await Mudae.wait_roll()

# Sends a message
await channel.send("Rolls have reset!")

```
The timing list only needs to be created once. I recommend adding a command to your bot, that makes this list, and then storing it in a database/file. The list is just 4 integers, so it can easily be written to a file.

### Homemade anti-snipe
```Python
mudae_wrap #A Mudae object
blind_role #A special role that prevents the member from seing the mudae channel

async def anti_snipe(message):
        
    # Creates the waifu
    waifu = self.mudae_wrap.waifu_from(message)

    # IF The waifu exist AND its a roll AND it's unclaimed THEN GO ON
    if waifu and waifu.type == mudae_wrap.Waifu.Type.roll and not waifu.is_claimed:

        # Fills the suitor (members who wished the waifu) attribute
        await waifu.fetch_extra()

        # IF there is a creator AND there are suitors AND creator is not a suitor THEN GO ON
        if waifu.creator and len(waifu.suitors) != 0 and waifu.creator not in waifu.suitors

            # Blind the creator for 10s
            await waifu.creator.add_roles(blind_role)
            await asyncio.sleep(10)
            await waifu.creator.remove_roles(blind_role)
```

### Send a special message, whenever someone claims a waifu
```Python
mudae_wrap #A Mudae object

async def on_message(message)

      # Parses the message and returns the waifu object
      waifu = mudae_wrap.waifu_from(message)

      # Makes sure the waifu isn't none, in case the message was from someone else
      if (waifu):
           
           # Waits 60s for the waifu to be claimed
           owner = await waifu.await_claim()
           
           # Checks if the waifu was claimed
           if (owner):
                
                #Sends a special message
                await message.channel.send(f"{owner.mention} don't forget to treat {waifu.name} well!")

```

### Claim waifu in wishlist
```Python
mudae_wrap #A Mudae object

async def on_message(message)
      
      # My wishes
      wishlist = ("saber", "suzuha", "hatsune miku")
      
      # Check if the waifu is in a wishlist
      waifu = mudae_wrap.from_wish(message, wishlist)
      
      # If it is, claim it
      if (waifu):
            await waifu.add_reaction("❤️")
