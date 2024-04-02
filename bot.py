import discord
from discord.ext import commands
from discord import app_commands
from threading import Lock
import os
import json
import asyncio
import gzip
from io import BytesIO

TOKEN = None
with open("token.txt") as file:
    TOKEN = file.read()


client = discord.Client(intents=discord.Intents.all())
tree = app_commands.CommandTree(client)


# importCommand('frequency')
# importCommand('top_messagers')
# importCommand('wordbomb')
# importCommand('profanity')
# importCommand('quote')
#importCommand('guess')
#tree.add_co


#import guess
#guess.client = client
#tree.add_command(guess.export.callback)

# importCommand('trivia')
# importCommand('rankings')

@client.event
async def on_ready():
    # Thread(target = init_messages_start).start()
    await tree.sync()

