import discord
from discord import app_commands
import json
import asyncio
import logging
from datetime import datetime
import os

if not os.path.exists('logs'): os.mkdir('logs')

logger = logging.getLogger('discord bot error log')

class LogHandler(logging.FileHandler):

    send_tasks = set()
    discord_output = None

    def __init__(self):
        super().__init__(filename='logs/' + str(datetime.now()).replace(':', '-') + '.log', encoding='utf-8', mode='w')

    def emit(self, record):
        super().emit(record)
        if LogHandler.discord_output and record.levelno == logging.ERROR:
            coroutine = LogHandler.discord_output.send('<@674819147963564054>\n```\n' + self.format(record) + '\n```')
            task = asyncio.get_running_loop().create_task(coroutine)
            LogHandler.send_tasks.add(task)
            task.add_done_callback(lambda t : LogHandler.send_tasks.remove(t))


token = None
with open('config.json') as file:
    token = json.loads(file.read())['token']

client = discord.Client(intents=discord.Intents.all(), activity=discord.Activity(type=discord.ActivityType.watching, name="1984"))
tree = app_commands.CommandTree(client)
default_color = 0x1f8b4c
neutral_color = 0x22212c

def commafy(number):
    return '{:,}'.format(number)

def is_admin(server : discord.Guild, user : discord.User):
    return server.id == 931838136223412235 and user.id in (
        674819147963564054,
        759086512586358794,
        705360840345518121,
        836328029130850304,
        743205276206760028
    )

run_on_ready = []
run_on_ready_tasks = []

@client.event
async def on_ready():

    LogHandler.discord_output = await client.fetch_channel(1283474550599974932)

    print('syncing tree...')
    await tree.sync()

    print('bot ready')
    for f in run_on_ready:
        run_on_ready_tasks.append(asyncio.get_running_loop().create_task(f))
