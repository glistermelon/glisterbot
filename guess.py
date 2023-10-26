import discord
from discord.ext import commands
from discord import app_commands
import asyncio
from util import randinx
import os
import time
import json
import random
from pydub import AudioSegment
import math
from io import BytesIO

add_msg_callback = None
rm_msg_callback = None
dead_color = None

callback = app_commands.Group(name = "guess", description = "Guessing games!")

@callback.command(name = "music", description = "Guess the origins of short audio clips.")
@app_commands.describe(
    boosters="If guessing MK8 audio, whether or not to include tracks from the Booster Course Pass."
    )
@app_commands.choices(
    category = [
        app_commands.Choice(name = "Super Mario Kart (1992)", value = "smk"),
        app_commands.Choice(name = "Mario Kart 64", value = "mk64"),
        app_commands.Choice(name = "Mario Kart DS", value = "mkds"),
        app_commands.Choice(name = "Mario Kart Wii", value = "mkw"),
        app_commands.Choice(name = "Mario Kart 7", value = "mk7"),
        app_commands.Choice(name = "Mario Kart 8", value = "mk8"),
        app_commands.Choice(name = "Geometry Dash", value = "geometrydash")
    ],
    boosters = [
        app_commands.Choice(name = "Yes", value = 1),
        app_commands.Choice(name = "No", value = 0)
    ]
)
async def guess_music(ctx, category : str, boosters : int = 0):
    if category == "mk8" and boosters:
        category += "bc"
    game = GuessMusic(ctx, category)
    if not game.valid:
        await ctx.response.send_message("There is already a game present in this channel!", ephemeral = True)
        return
    await game.start()

@callback.command(name = "pictionary", description = "Guess anything from Geometry Dash levels to world flags.")
@app_commands.describe(category = "type of image to guess at")
@app_commands.choices(category = [
    app_commands.Choice(name = "Geometry Dash levels", value = "geometrydash"),
    app_commands.Choice(name = "country flags", value = "flags")
])
async def pictionary(ctx, category : str):
    game = Pictionary(ctx, category)
    if not game.valid:
        await ctx.response.send_message("There is already a game present in this channel!", ephemeral = True)
        return
    await game.start()

class Guess():
    instances = []

    def __init__(self, ctx, guess_type, category, file_ext = None):
        if ctx.channel in Guess.instances:
            self.valid = False
            return
        self.valid = True
        Guess.instances.append(ctx.channel)

        self.category = category
        self.ctx = ctx

        dir_name = f"guess/{guess_type}/{category}/options"
        options = [os.path.join(dp, f).replace('\\','/') for dp, _, fn in os.walk(os.path.expanduser(dir_name)) for f in fn]
        if file_ext is not None:
            options = [option for option in options if option[-1] != '.' and option[option.index('.') + 1:] == file_ext]
        choice = options[randinx(len(options))]
        self.file_path = choice
        choice = choice[choice.rindex("/options/") + len("/options/") : choice.index('.')]

        self.info = None
        with open(f"guess/{guess_type}/{category}/info.json") as file:
            self.info = json.loads(file.read())
        self.term = self.info["term"]

        if guess_type == "pictionary" and self.term == "flag" and random.randint(1, 100) == 1:
            Guess.instances.pop(Guess.instances.index(ctx.channel))
            self.__init__(ctx, "fags")
            return

        self.answers = None
        try:
            self.answers = self.info["answers"][choice]
            if type(self.answers) == str:
                self.answers = [self.answers]
        except:
            self.answers = [choice]
        for i in range(len(self.answers)):
            self.answers[i] = self.answers[i].lower()

    async def start(self):
        self.done = False # sync stuff
        self.task = asyncio.create_task(self._start()) 

    def clean(self):
        self.done = True
        rm_msg_callback(self.callback)
        Guess.instances.pop(Guess.instances.index(self.ctx.channel))

    async def callback(self, msg):
        if self.done or msg.author.bot or msg.content.strip().lower() not in self.answers:
            print(self.answers)
            return
        self.task.cancel()
        self.clean()
        time_taken = round(time.time() - self.begin_time, 1)
        if self.term == "fag":
            self.begin_embed.description = f"<@{msg.author.id}> guessed correctly after {time_taken} seconds... thats so hot- actually ermmmm i mean... what a fag... >~<"
        else:
            self.begin_embed.description = f"**Answer guessed correctly by <@{msg.author.id}> after {time_taken} seconds!**"
        self.begin_embed.color=0x00FF00
        await self.ctx.edit_original_response(embed = self.begin_embed)

class Pictionary(Guess):

    def __init__(self, ctx, category):
        super().__init__(ctx, "pictionary", category)

    async def _start(self):
        embed_title = f"What {self.term} is this"
        if self.term == "fag":
            embed_title += "~ >~<"
        else:
            embed_title += "?"
        self.begin_embed = discord.Embed(
            title = embed_title,
            description = "*You have 20 seconds to answer!*",
            color = dead_color
            )
        self.begin_embed.set_image(url = "attachment://mystery.png")
        await self.ctx.response.send_message(
            embed = self.begin_embed,
            file = discord.File(
                self.file_path,
                filename = "mystery.png"
            )
        )
        self.begin_time = time.time()
        add_msg_callback(self.callback, self.ctx.channel)
        await asyncio.sleep(20)
        self.clean()
        self.begin_embed.description = "**Nobody guessed correctly within the time limit!**"
        self.begin_embed.color = 0xFF0000
        await self.ctx.edit_original_response(embed = self.begin_embed)

class GuessMusic(Guess):

    def __init__(self, ctx, category):
        super().__init__(ctx, "music", category)

    async def _start(self):
        song = AudioSegment.from_mp3(self.file_path)
        segment = self.info["segment"] * 1000
        pos = int(math.floor(random.random() * (len(song) - segment)))
        music_io = BytesIO()
        song[pos : pos + segment].export(music_io, format = "mp3")
        self.begin_embed = discord.Embed(
            title = f"What { self.term } does this song belong to?",
            description = "*You have 20 seconds to answer!*",
            color = 0x2F3136
            )
        await self.ctx.channel.send(file = discord.File(music_io, filename = "mystery.mp3"))
        await self.ctx.response.send_message(embed = self.begin_embed)
        self.begin_time = time.time()
        add_msg_callback(self.callback, self.ctx.channel)
        await asyncio.sleep(20)
        self.clean()
        self.begin_embed.description = "**Nobody guessed any of the answers within the time limit!**"
        self.begin_embed.color = 0xFF0000
        await self.ctx.edit_original_response(embed = self.begin_embed)