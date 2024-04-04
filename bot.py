import discord
from discord import app_commands
import json

token = None
with open("token.txt") as file:
    token = file.read()

client = discord.Client(intents=discord.Intents.all())
tree = app_commands.CommandTree(client)

import guess
import profanity

# importCommand('frequency')
# importCommand('top_messagers')
# importCommand('wordbomb')
# importCommand('profanity')
# importCommand('quote')
# importCommand('guess')
# tree.add_co


# import guess
# guess.client = client
# tree.add_command(guess.export.callback)

# importCommand('trivia')
# importCommand('rankings')

import log


@client.event
async def on_ready():
    # await tree.sync()
    l = log.Logger.load_from_file()
    l.make_global()
    #await l.log_all(await client.fetch_channel(931838136223412239))
