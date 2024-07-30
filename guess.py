import discord
from discord import app_commands
import asyncio
import os
import time
import json
import random
from pydub import AudioSegment
import math
from io import BytesIO
import bot
import events


guess_callback = app_commands.Group(name="guess", description="Guessing games!")


bot.tree.add_command(guess_callback)


@guess_callback.command(name="music", description="Guess the origins of short audio clips.")
@app_commands.describe(
    boosters="If guessing MK8 audio, whether or not to include tracks from the Booster Course Pass."
)
@app_commands.choices(
    category=[
        app_commands.Choice(name="Super Mario Kart (1992)", value="smk"),
        app_commands.Choice(name="Mario Kart 64", value="mk64"),
        app_commands.Choice(name="Mario Kart DS", value="mkds"),
        app_commands.Choice(name="Mario Kart Wii", value="mkw"),
        app_commands.Choice(name="Mario Kart 7", value="mk7"),
        app_commands.Choice(name="Mario Kart 8", value="mk8"),
        app_commands.Choice(name="Geometry Dash", value="geometrydash")
    ],
    boosters=[
        app_commands.Choice(name="Yes", value=1),
        app_commands.Choice(name="No", value=0)
    ]
)
async def guess_music(ctx, category: str, boosters: int = 0):
    if category == "mk8" and boosters:
        category += "bc"
    await GuessMusic(ctx, category).start()


@guess_callback.command(name="pictionary", description="Guess anything from Geometry Dash levels to world flags.")
@app_commands.describe(category="type of image to guess at")
@app_commands.choices(category=[
    app_commands.Choice(name="Geometry Dash levels", value="geometrydash"),
    app_commands.Choice(name="country flags", value="flags")
])
async def pictionary(ctx, category: str):
    await Pictionary(ctx, category).start()


class Guess:
    instances = set()

    @staticmethod
    def is_channel_free(channel):
        return channel.id not in Guess.instances

    def __init__(self, ctx, guess_type, category):

        self.ctx = ctx
        self.guess_type = guess_type
        self.category = category

    async def start(self):

        if not Guess.is_channel_free(self.ctx.channel):
            await self.ctx.response.send_message("There is already a game present in this channel!", ephemeral=True)
            return False
        Guess.instances.add(self.ctx.channel.id)

        self.timer = None
        self.begin_embed = None
        self.begin_time = None

        dir_name = f"guess/{self.guess_type}/{self.category}/options"
        options = [os.path.join(dp, f).replace('\\', '/') for dp, _, fn in os.walk(os.path.expanduser(dir_name))
                   for f in fn]
        choice = options[random.randint(0, len(options) - 1)]
        self.file_path = choice
        choice = choice[choice.rindex("/options/") + len("/options/") : choice.index('.')]

        self.info = None
        with open(f"guess/{self.guess_type}/{self.category}/info.json") as file:
            self.info = json.loads(file.read())
        self.term = self.info["term"]

        if 'meta' in self.info and choice in self.info['meta']:
            meta = self.info['meta'][choice]
            if 'author' in meta: self.author = meta['author']

        if 'answers' in self.info and choice in self.info['answers']:
            self.answers = self.info['answers'][choice]
        else:
            self.answers = choice
        if type(self.answers) is not list: self.answers = [self.answers]
        self.answers = [a.lower().strip() for a in self.answers]
        print(self.answers)

        return True

    def clean(self):
        events.rm_listener('on_message', self.callback)
        if self.ctx.channel.id in Guess.instances:
            Guess.instances.remove(self.ctx.channel.id)
    
    def kill_myself(self):
        del self

    async def callback(self, msg):
        if msg.author.bot or (msg.content.strip().lower() not in self.answers) or Guess.is_channel_free(self.ctx.channel):
            return
        self.timer.cancel()
        self.clean()
        time_taken = round(time.time() - self.begin_time, 1)
        self.begin_embed.description = f"**Answer guessed correctly by <@{msg.author.id}> after {time_taken} seconds!**"
        self.begin_embed.color = 0x00FF00
        await self.ctx.edit_original_response(embed=self.begin_embed)
        self.kill_myself()


class Pictionary(Guess):

    def __init__(self, ctx, category):
        super().__init__(ctx, "pictionary", category)

    async def start(self):
        if not await super().start():
            return
        embed_title = f"What {self.term} is this?"
        self.begin_embed = discord.Embed(
            title=embed_title,
            description='*You have 20 seconds to answer!*',
            color=0x36393F
        )
        if self.author and type(self.author) is str and len(self.author) > 0: self.begin_embed.set_footer(text=f'Illustrator: {self.author}')
        self.begin_embed.set_image(url="attachment://mystery.png")
        try:
            print(self.file_path)
            await self.ctx.response.send_message(
                embed=self.begin_embed,
                file=discord.File(
                    self.file_path,
                    filename="mystery.png"
                )
            )
        except discord.HTTPException:
            self.clean()
            return
        self.begin_time = time.time()
        self.timer = asyncio.current_task()
        events.add_listener("on_message", self.callback, channel = self.ctx.channel)
        await asyncio.sleep(20)
        self.clean()
        self.begin_embed.description = "**Nobody guessed correctly within the time limit!**"
        self.begin_embed.colour = 0xFF0000
        await self.ctx.edit_original_response(embed=self.begin_embed)
        self.kill_myself()


class GuessMusic(Guess):

    def __init__(self, ctx, category):
        super().__init__(ctx, "music", category)

    async def start(self):
        if not await super().start():
            return
        song = AudioSegment.from_mp3(self.file_path)
        segment = self.info["segment"] * 1000 if "segment" in self.info else 10000
        pos = int(math.floor(random.random() * (len(song) - segment)))
        music_io = BytesIO()
        song[pos: pos + segment].export(music_io, format="mp3")
        self.begin_embed = discord.Embed(
            title=f"What {self.term} does this song belong to?",
            description="*You have 20 seconds to answer!*",
            color=0x2F3136
        )
        try:
            await self.ctx.channel.send(file=discord.File(music_io, filename="mystery.mp3"))
            await self.ctx.response.send_message(embed=self.begin_embed)
        except discord.HTTPException:
            self.clean()
            return
        self.begin_time = time.time()
        self.timer = asyncio.current_task()
        events.add_listener("on_message", self.callback, channel = self.ctx.channel)
        await asyncio.sleep(20)
        self.clean()
        self.begin_embed.description = "**Nobody guessed any of the answers within the time limit!**"
        self.begin_embed.colour = 0xFF0000
        await self.ctx.edit_original_response(embed=self.begin_embed)
        self.kill_myself()