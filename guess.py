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
import database as db
from database import sql, sql_conn
from sqlalchemy.orm import Session

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
@app_commands.describe(category="type of image to guess at", illustrator='see images from a specific illustrator')
@app_commands.choices(category=[
    app_commands.Choice(name="Geometry Dash levels", value="geometrydash"),
    app_commands.Choice(name="country flags", value="flags")
])
async def pictionary(ctx, category : str, illustrator : str = None):
    await Pictionary(ctx, category, illustrator).start()

def increment_streak(channel : discord.TextChannel | int, user : discord.User | int, is_pictionary : bool):
    if type(channel) is not int: channel = channel.id
    if type(user) is not int: user = user.id
    with Session(db.engine) as session:
        data = session.execute(sql.select(db.streak_table).where(db.streak_table.c.CHANNEL == channel)).first()
        if data is None:
            session.execute(sql.insert(db.streak_table).values(
                CHANNEL=channel,
                PICTIONARY_USER=user if is_pictionary else 0,
                PICTIONARY=1 if is_pictionary else 0,
                MUSIC_USER=user if not is_pictionary else 0,
                MUSIC=1 if not is_pictionary else 0
            ))
            session.commit()
            return 1
        stmt = sql.update(db.streak_table).where(db.streak_table.c.CHANNEL == channel)
        streak = None
        if is_pictionary:
            if data.PICTIONARY_USER == user:
                stmt = stmt.values(PICTIONARY=data.PICTIONARY + 1)
                streak = data.PICTIONARY + 1
            else:
                stmt = stmt.values(PICTIONARY=1, PICTIONARY_USER=user)
                streak = 1
        else:
            if data.MUSIC_USER == user:
                stmt = stmt.values(MUSIC=data.MUSIC + 1)
                streak = data.MUSIC + 1
            else:
                stmt = stmt.values(MUSIC=1, MUSIC_USER=user)
                streak = 1
        session.execute(stmt)
        session.commit()
        return streak

def reset_streak(channel : discord.TextChannel | int, is_pictionary : bool):
    increment_streak(channel, 0, is_pictionary)

class Guess:
    instances = set()

    @staticmethod
    def is_channel_free(channel):
        return channel.id not in Guess.instances

    def __init__(self, ctx, guess_type, category):

        self.ctx = ctx
        self.guess_type = guess_type
        self.category = category

    async def start(self, choice_filter = None):

        if not Guess.is_channel_free(self.ctx.channel):
            return "There is already a game present in this channel!"
        Guess.instances.add(self.ctx.channel.id)

        self.timer = None
        self.begin_embed = None
        self.begin_time = None

        dir_name = f"guess/{self.guess_type}/{self.category}/options"

        self.info = None
        with open(f"guess/{self.guess_type}/{self.category}/info.json") as file:
            self.info = json.loads(file.read())
        self.term = self.info["term"]

        options = [os.path.join(dp, f).replace('\\', '/') for dp, _, fn in os.walk(os.path.expanduser(dir_name))
                   for f in fn]
        file_paths = list(options)
        options = [choice[choice.rindex("/options/") + len("/options/") : choice.index('.')] for choice in options]
        if choice_filter: options, file_paths = choice_filter(options, file_paths, self.info)
        if type(options) is str: return options # error

        choice_index = random.randint(0, len(options) - 1)
        choice = options[choice_index]
        self.file_path = file_paths[choice_index]

        if isinstance(self, Pictionary) and 'meta' in self.info and choice in self.info['meta']:
            meta = self.info['meta'][choice]
            if 'author' in meta: self.illustrator = meta['author']

        if 'answers' in self.info and choice in self.info['answers']:
            self.answers = self.info['answers'][choice]
        else:
            self.answers = choice
        if type(self.answers) is not list: self.answers = [self.answers]
        self.answers = [a.lower().strip() for a in self.answers]

        if isinstance(self, GuessMusic): print(choice, self.answers)

        return True

    def clean(self):
        events.rm_listener('on_message', self.callback)
        if self.ctx.channel.id in Guess.instances:
            Guess.instances.remove(self.ctx.channel.id)

    async def callback(self, msg):
        if msg.author.bot or (msg.content.strip().lower() not in self.answers) or Guess.is_channel_free(self.ctx.channel):
            return
        self.timer.cancel()
        self.clean()
        time_taken = round(time.time() - self.begin_time, 1)
        self.begin_embed.description = f"**Answer guessed correctly by <@{msg.author.id}> after {time_taken} seconds!**"
        self.begin_embed.color = 0x00FF00
        await self.ctx.edit_original_response(embed=self.begin_embed)

        streak = increment_streak(self.ctx.channel, msg.author, isinstance(self, Pictionary))
        title = 'You guessed correctly!'
        if streak > 1: title += f' x{streak}'
        await msg.channel.send(
            embed=discord.Embed(
                title=title,
                description='I\'m going to implement rewards here!',
                color=0x00FF00
            ),
            reference=msg,
            mention_author=False
        )


class Pictionary(Guess):

    def __init__(self, ctx, category, illustrator):
        super().__init__(ctx, "pictionary", category)
        self.illustrator = illustrator

    async def start(self):

        choice_filter = None
        if self.illustrator:
            self.illustrator = self.illustrator.lower()
            def filter_fn(options, file_paths, info):
                if 'meta' not in info: return options, file_paths
                meta = info['meta']
                pairs = [(options[i], file_paths[i]) for i in range(len(options))]
                pairs = [p for p in pairs if p[0] in meta and 'author' in meta[p[0]] and meta[p[0]]['author'].lower() == self.illustrator]
                if len(pairs) == 0: return 'No drawings were found with that illustrator.', None
                return [p[0] for p in pairs], [p[1] for p in pairs]
            choice_filter = filter_fn

        err = await super().start(choice_filter)
        if not (type(err) is bool and err):
            await self.ctx.response.send_message(err if type(err) is str else 'An error occurred.', ephemeral=True)
            return

        embed_title = f"What {self.term} is this?"
        self.begin_embed = discord.Embed(
            title=embed_title,
            description='*You have 20 seconds to answer!*',
            color=0x36393F
        )
        if self.illustrator and type(self.illustrator) is str and len(self.illustrator) > 0: self.begin_embed.set_footer(text=f'Illustrator: {self.illustrator}')
        self.begin_embed.set_image(url="attachment://mystery.png")
        try:
            # print(self.file_path)
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
        reset_streak(self.ctx.channel, True)


class GuessMusic(Guess):

    def __init__(self, ctx, category):
        super().__init__(ctx, "music", category)

    async def start(self):

        err = await super().start()
        if not (type(err) is bool and err):
            await self.ctx.response.send_message(err if type(err) is str else 'An error occurred.', ephemeral=True)
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
        reset_streak(self.ctx.channel, False)