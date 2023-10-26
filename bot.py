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

bot = commands.Bot(token=TOKEN,command_prefix='&',intents=discord.Intents.all())
client = discord.Client(intents=discord.Intents.all())
tree = app_commands.CommandTree(client)

# idk if anything actually uses these but i'm too lazy to check rn
embed_color = 0x00AA00
dead_color = 0x2B2D31

moderators = {}
moderators[931838136223412235] = [
    674819147963564054,
    364135729737105409,
    1101110219737682030,
    743205276206760028,
    528880782320730112
    ]

msg_callbacks = []
msg_callbacks_lock = Lock()

def add_msg_callback(callback, channel = None):
    if channel is None:
        msg_callbacks.append(callback)
    else:
        msg_callbacks.append([channel,callback])

def rm_msg_callback(callback):
    with msg_callbacks_lock:
        length = len(msg_callbacks)
        for i in range(length):
            item = msg_callbacks[i]
            if item == callback or (type(item) == list and item[1] == callback):
                msg_callbacks.pop(i)
                return

def importCommand(command):
    global module
    exec(f'global {command}', globals())
    exec(f'import {command}', globals())
    exec(f'module = {command}', globals())
    module.embed_color = embed_color
    module.dead_color = dead_color
    module.add_msg_callback = add_msg_callback
    module.rm_msg_callback = rm_msg_callback
    global tree
    tree.add_command(module.callback)

# OLD MESSAGE ARRAY FORMAT (deprecated) :
# [  message id, message content, message epoch, sender id, channel id  ]
class LoggedMessage():
    @staticmethod
    async def create(msg):
        self = LoggedMessage()
        if type(msg) == list: # for compatibility with old logs
            self.id = msg[0]
            self.content = msg[1]
            self.time = msg[2]
            self.author = discord.utils.get(client.users, id = msg[3])
            self.channel = discord.utils.get(
                (channel for guild in client.guilds for channel in guild.channels),
                id = msg[4]
            )
        elif type(msg) == LoggedMessage: # copy constructor
            self.id = msg.id
            self.content = msg.content
            self.time = msg.time
            self.author = msg.author
            self.channel = msg.channel
        else: # LoggedMessage from discord.py message
            self.id = msg.id
            self.content = msg.content
            self.time = int(msg.created_at.timestamp())
            self.author = msg.author
            self.channel = msg.channel
        return self
        
    def __list__(self):
        return [self.id, self.content, self.time, self.author.id, self.channel.id]

#importCommand('frequency')
#importCommand('top_messagers')
#importCommand('wordbomb')
#importCommand('profanity')
#importCommand('quote')
importCommand('guess')
#importCommand('trivia')
#importCommand('rankings')

@client.event
async def on_message(message):
    callbacks = []
    with msg_callbacks_lock:
        length = len(msg_callbacks)
        for i in range(length):
            callbacks.append(msg_callbacks[i])
    for callback in callbacks:
        if type(callback) == list:
            if callback[0] == message.channel:
                await callback[1](message)
        else:
            await callback(message)

async def init_messages():
    all_messages = {}
    for fname in (fname for fname in os.listdir("messages") if fname.count('.') > 0 and fname[fname.index('.'):] == ".json"):
        msg_collection = None
        with open("messages/" + fname) as file:
            msg_collection = json.loads(file.read())
        guild_id = int(fname[:fname.index('.')])
        all_messages[guild_id] = [await LoggedMessage.create(msg_arr) for msg_arr in msg_collection]
    msgs = sorted(all_messages[931838136223412235], key = lambda msg : msg.time)
    output = BytesIO()
    for msg in msgs:
        output.write(msg.time.to_bytes(10))
        output.write(msg.id.to_bytes(10))
        try:
            output.write(msg.author.id.to_bytes(10))
        except:
            output.write(bytes(10))
        output.write(msg.content.encode())
        output.write(b'\0')
    output.seek(0)
    with open("log.mdat.gzip", "wb") as file:
        file.write(gzip.compress(output.read()))
    print("\ninit_messages done")

def init_messages_start():
    asyncio.run(init_messages())

@client.event
async def on_ready():
    #Thread(target = init_messages_start).start()
    await tree.sync()
    print("Tree Synced")

client.run(TOKEN)
