from types import SimpleNamespace
import time
import discord
from discord.ext.commands import has_guild_permissions, command
from datetime import datetime
import math
import asyncio
import bot
from database import *
import database
import json
from sqlalchemy.orm import Session

class Timespans:

    def __init__(self):
        self.segments = []

    def add_timespan(self, begin, end):
        timespan = SimpleNamespace()
        timespan.begin = begin
        timespan.end = end
        for i in range(len(self.segments)):
            other = self.segments[i]
            if begin > other.begin:
                continue
            self.segments.insert(i, timespan)
            while len(self.segments) > i + 1 and self.segments[i + 1].begin <= timespan.end:
                self.segments.pop(i + 1)
            return
        if len(self.segments) > 0 and self.segments[-1].end >= begin:
            self.segments[-1].end = end
        else:
            self.segments.append(timespan)

    def remove_timespan(self, begin, end):
        i = 0
        cancel = True
        for i in range(len(self.segments)):
            if begin <= self.segments[i].end and end >= self.segments[i].begin:
                cancel = False
                break
        if cancel:
            return
        while i < len(self.segments):
            segment = self.segments[i]
            if begin <= segment.begin and end >= segment.end:
                self.segments.pop(i)
            elif begin > segment.begin and end < segment.end:
                new = SimpleNamespace()
                new.begin = end + 1
                new.end = segment.end
                self.segments.insert(i + 1, new)
                self.segments[i].end = begin - 1
                break
            elif begin <= segment.begin and end < segment.end:
                self.segments[i].begin = end + 1
                break
            else:  # begin > segment.begin and end >= segment.end
                self.segments[i].end = begin - 1
                i += 1

    def remove_timespans(self, timespans):
        for timespan in timespans.segments:
            self.remove_timespan(timespan.begin, timespan.end)

    def add_to_table(self, channel_id : int):
        # professional laziness
        sql_conn.execute(sql.delete(timespan_table).where(timespan_table.c.CHANNEL == channel_id))
        for span in self.segments:
            stmt = sql.insert(timespan_table).values(
                CHANNEL = channel_id,
                BEGIN = span.begin,
                END = span.end
            )
            sql_conn.execute(stmt)
        sql_conn.commit()


class LoggedMessage:

    def __init__(self, msg: discord.Message = None):
        if msg is None:
            return
        self.id = msg.id
        self.content = msg.content
        self.timestamp = msg.created_at.timestamp()
        self.author = msg.author.id
        self.jump_url = msg.jump_url
        self.mention_everyone = msg.mention_everyone
        self.mentions = [author.id for author in msg.mentions]
        self.role_mentions = [role.id for role in msg.role_mentions]
        self.channel = msg.channel.id
    
    async def add_reactions(self, msg: discord.Message):
        self.reactions = {
            reaction.emoji if type(reaction.emoji) is str else [reaction.emoji.id, reaction.emoji.name] :
            [user.id async for user in reaction.users()]
            for reaction in msg.reactions
        }

        # print(
        #    f'Logged: "{msg.content}" - {msg.author.name}, {msg.created_at.strftime("%m/%d/%Y, %H:%M:%S")} ({msg.id})')
    
    def add_to_table(self):
        with Session(database.engine) as session:
            session.execute(postgresql.insert(msg_table).values(
                DISCORD_ID = self.id,
                CONTENT = self.content,
                TIMESTAMP = self.timestamp,
                AUTHOR = self.author,
                JUMP_URL = self.jump_url,
                MENTIONS_EVERYONE = self.mention_everyone,
                CHANNEL = self.channel
            ).on_conflict_do_nothing(index_elements=['DISCORD_ID']))
            for m in self.mentions:
                session.execute(postgresql.insert(mentions_table).values(
                    MESSAGE_ID = self.id,
                    MENTIONED_USER = m
                ).on_conflict_do_nothing(constraint=mentions_constraint))
            for m in self.role_mentions:
                session.execute(postgresql.insert(role_mentions_table).values(
                    MESSAGE_ID = self.id,
                    MENTIONED_ROLE = m
                ).on_conflict_do_nothing(constraint=role_mentions_constraint))
            for m in self.reactions:
                session.execute(postgresql.insert(reactions_table).values(
                    MESSAGE_ID = self.id,
                    REACTION = m[0],
                    COUNT = m[1]
                ).on_conflict_do_nothing(constraint=reactions_constraint))
            for reaction, users in self.reactions.items():
                for user_id in users:
                    session.execute(
                        sql.insert(database.reactions_table).values(
                            MESSAGE_ID=self.id,
                            USER=user_id,
                            EMOJI_ID=reaction[0] if type(reaction) is not str else sql.null(),
                            EMOJI_NAME=reaction[1] if type(reaction.emoji) is not str else reaction
                        )
                    )
            session.commit()


class TextChannelLogger:
    save_dir = 'messages'

    def __init__(self, channel: discord.TextChannel):
        self.timespans = Timespans()
        self.messages = []
        self.channel = channel

    async def log_all(self, sleep=None) -> int:

        sql_conn.execute(postgresql.insert(channel_table).values(
            CHANNEL = self.channel.id,
            SERVER = self.channel.guild.id
        ).on_conflict_do_nothing(index_elements=['CHANNEL']))

        sql_conn.commit()

        for span in sql_conn.execute(sql.select(timespan_table).where(timespan_table.c.CHANNEL == self.channel.id)):
            self.timespans.add_timespan(span.BEGIN, span.END)

        print('Logging: #' + self.channel.name)

        log_timespans = Timespans()
        log_timespans.add_timespan(discord.utils.DISCORD_EPOCH // 1000 + 1, math.floor(time.time()))
        log_timespans.remove_timespans(self.timespans)

        # print(log_timespans.segments)

        i = 0
        messages_logged = 0
        last_check = time.time()
        for timespan in log_timespans.segments:
            async for msg in self.channel.history(
                    limit=None,
                    after=datetime.fromtimestamp(timespan.begin - 1),
                    before=datetime.fromtimestamp(timespan.end + 1),
                    oldest_first=True
            ):
                lm = LoggedMessage(msg)
                await lm.add_reactions(msg)
                lm.add_to_table()
                self.timespans.add_timespan(discord.utils.DISCORD_EPOCH // 1000 + 1,
                                            math.floor(msg.created_at.timestamp()))
                self.timespans.add_to_table(self.channel.id)
                i += 1
                messages_logged += 1
                if i == 100:
                    i = 0
                    print('\r', messages_logged, f'messages logged ({int(100 // (time.time() - last_check))} /s)',
                          end='')
                    last_check = time.time()
                    if sleep: await asyncio.sleep(sleep)
        
        return messages_logged

    def get_random_message(self):
        return None # todo


class ServerLogger:

    def __init__(self, server: discord.Guild):
        self.server = server
        self.channel_loggers = None

    async def setup(self):
        self.channel_loggers = [
            TextChannelLogger(c) for c in await self.server.fetch_channels() if type(c) is discord.TextChannel
        ]

    async def log_all(self, sleep=None) -> int:
        msg_count = 0
        for logger in self.channel_loggers:
            msg_count += await logger.log_all(sleep)
        return msg_count

logs_updating = False
@bot.tree.command(name='update-logs', description='Updates the message logs for this server. May take a long time.')
async def update_logs(ctx : discord.Interaction):

    global logs_updating
    if logs_updating:
        await ctx.response.send_message('Someone else is updating the logs right now!', ephemeral=True)
        return
    logs_updating = True

    if not (ctx.user.guild_permissions.administrator or ctx.user.id == 319397081901170689):
        await ctx.response.send_message('You need admin perms to run this command!', ephemeral=True)
        return
    
    await ctx.response.send_message('Logging messages. This may take a very long time.')
    logger = ServerLogger(ctx.guild)
    await logger.setup()
    num = await logger.log_all()
    await ctx.channel.send(f'<@{ctx.user.id}> Message logging finished! {'{:,}'.format(num)} new messages were logged.')
    await ctx.channel.send('Updating profanity index...')
    for user in (row.AUTHOR for row in sql_conn.execute(sql.text('SELECT DISTINCT ON ("AUTHOR") "AUTHOR" FROM "Messages";'))):
        update_profanity(user)
    await ctx.channel.send('Profanity index updated.')

    logs_updating = False


def get_messages(user : discord.User | int, session = None):
    if type(user) is not int: user = user.id
    if session is None: session = sql_conn
    return (r.CONTENT for r in session.execute(sql.select(msg_table.c.CONTENT).where(msg_table.c.AUTHOR == user)).all())


def update_profanity(user : discord.User | int):

    if type(user) is not int: user = user.id
    
    profanity_dict = json.loads(open('profanity.json').read())

    with Session(database.engine) as session:

        session.execute(sql.delete(database.profanity_table).where(database.profanity_table.c.USER == user))

        messages = (m.lower().strip() for m in get_messages(user, session))


        counts = {}
        for message in messages:
            skip = []
            for words in profanity_dict.values():
                for word in words:
                    i = -1
                    while True:
                        i = message.find(word, i + 1)
                        if i == -1: break
                        if i in skip: continue
                        j = i + len(word)
                        if (i == 0 or not message[i - 1].isalpha()) and (j == len(message) or (not message[j].isalpha()) or message[j] == 's'):
                            try:
                                counts[word] += 1
                            except:
                                counts[word] = 0
                            skip += [x for x in range(i, j)]
        
        for word, count in counts.items():                
            stmt = sql.insert(database.profanity_table).values(WORD=word, USER=user, COUNT=count)
            session.execute(stmt)
            
        session.commit()
