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
neutral_color = 0x2b2d31

def commafy(number):
    return '{:,}'.format(number)

run_on_ready = []
run_on_ready_tasks = []

@client.event
async def on_ready():

    LogHandler.discord_output = discord.Webhook.from_url(
        'https://discord.com/api/webhooks/1283474938895798344/BILRE-D-8y7FF6sx3XQd4CQsldZ95wKcJL2k-uyw0t7VwshyZe34HydyLOJe4Sq6tDIq',
        client=client
    )

    print('syncing tree...')
    await tree.sync()

    print('bot ready')
    #await tree.sync()
    #print('tree synced')
    for f in run_on_ready:
        run_on_ready_tasks.append(asyncio.get_running_loop().create_task(f))
