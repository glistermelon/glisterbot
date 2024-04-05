from types import SimpleNamespace
import json
import time
import discord
import bisect
from datetime import datetime
import math
import random
import bot


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

    def to_json(self):
        data = []
        for s in self.segments:
            data.append([s.begin, s.end])
        return data

    @staticmethod
    def from_json(data):
        t = Timespans()
        for pair in data:
            t.add_timespan(pair[0], pair[1])
        return t


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
        self.reactions = [[r.emoji if type(r.emoji) is str else r.emoji.id, r.count] for r in msg.reactions]

        #print(
        #    f'Logged: "{msg.content}" - {msg.author.name}, {msg.created_at.strftime("%m/%d/%Y, %H:%M:%S")} ({msg.id})')

    def to_json(self):

        adv_data = {}
        if self.mention_everyone:
            adv_data['me'] = True
        if len(self.mentions) != 0:
            adv_data['ms'] = self.mentions if len(self.mentions) > 1 else self.mentions[0]
        if len(self.role_mentions) != 0:
            adv_data['rms'] = self.role_mentions if len(self.role_mentions) > 1 else self.role_mentions[0]
        if len(self.reactions) != 0:
            adv_data['rs'] = self.reactions if len(self.reactions) > 1 else self.reactions[0]
        return [self.id, self.content, self.timestamp, self.author, self.jump_url, adv_data]

    @staticmethod
    def from_json(data):

        m = LoggedMessage()
        m.id = data[0]
        m.content = data[1]
        m.timestamp = data[2]
        m.author = data[3]
        m.jump_url = data[4]
        adv_data = data[-1]

        m.mention_everyone = 'me' in adv_data
        m.mentions = adv_data['ms'] if 'ms' in adv_data else []
        m.role_mentions = adv_data['rms'] if 'rms' in adv_data else []
        m.reactions = adv_data['rs'] if 'rs' in adv_data else []

        if type(m.mention_everyone) is not list: m.mention_everyone = [m.mention_everyone]
        if type(m.mentions) is not list: m.mentions = [m.mentions]
        if type(m.role_mentions) is not list: m.role_mentions = [m.role_mentions]
        if type(m.reactions) is not list: m.reactions = [m.reactions]

        return m


class TextChannelLogger:
    save_dir = 'messages'
    loggers = {}

    def __init__(self, channel: discord.TextChannel):
        self.timespans = Timespans()
        self.messages = []
        self.channel = channel
        TextChannelLogger.loggers[channel.id] = self

    def to_json(self):
        return {
            'messages': [m.to_json() for m in self.messages],
            'timespans': self.timespans.to_json()
        }

    @staticmethod
    async def from_json(channel_id, data):
        channel = await bot.client.fetch_channel(channel_id)
        if channel is None: return None
        l = TextChannelLogger(channel)
        l.timespans = Timespans.from_json(data['timespans'])
        l.messages = [LoggedMessage.from_json(m) for m in data['messages']]
        return l

    def save_to_file(self, save_dir=None):
        if save_dir is None: save_dir = TextChannelLogger.save_dir
        with open(f'{save_dir}/{self.channel.id}.json', 'w') as f:
            f.write(json.dumps(self.to_json(), separators=(',', ':')))

    @staticmethod
    async def load_from_file(channel_id, save_dir=None):
        if save_dir is None: save_dir = TextChannelLogger.save_dir
        try:
            with open(f'{save_dir}/{channel_id}.json') as f:
                return await TextChannelLogger.from_json(channel_id, json.loads(f.read()))
        except FileNotFoundError:
            channel = await bot.client.fetch_channel(channel_id)
            return TextChannelLogger(channel) if channel is not None else None

    async def log_all(self):
    
        print('Logging: #' + self.channel.name)

        log_timespans = Timespans()
        log_timespans.add_timespan(discord.utils.DISCORD_EPOCH // 1000 + 1, math.floor(time.time()))
        log_timespans.remove_timespans(self.timespans)

        i = 0
        for timespan in log_timespans.segments:
            async for msg in self.channel.history(
                    limit=None,
                    after=datetime.fromtimestamp(timespan.begin - 1),
                    before=datetime.fromtimestamp(timespan.end + 1),
                    oldest_first=True
            ):
                bisect.insort(self.messages, LoggedMessage(msg), key=lambda m: m.timestamp)
                self.timespans.add_timespan(discord.utils.DISCORD_EPOCH // 1000 + 1,
                                            math.floor(msg.created_at.timestamp()))
                i += 1
                if i == 100:
                    i = 0
                    self.save_to_file()
                    print(len(self.messages), 'messages logged', end='\r')
        
        print('')

        self.save_to_file()

    def get_random_message(self):
        return self.messages[random.randrange(len(self.messages))]

    def get_messages(self):
        return (msg for _, messages in self.logs.items() for msg in messages)