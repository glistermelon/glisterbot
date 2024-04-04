from types import SimpleNamespace
import json
import time
import discord
import bisect
from datetime import datetime
import math
import random


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

        print(
            f'Logged: "{msg.content}" - {msg.author.name}, {msg.created_at.strftime("%m/%d/%Y, %H:%M:%S")} ({msg.id})')

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


class Logger:
    default_file = 'messages.json'
    global_logger = None

    def __init__(self):
        self.timespans = Timespans()
        self.logs = {}

    def make_global(self):
        Logger.global_logger = self

    def to_json(self):
        return {
            'messages': {channel_id: [m.to_json() for m in messages] for channel_id, messages in self.logs.items()},
            'timespans': self.timespans.to_json()
        }

    @staticmethod
    def from_json(data):
        l = Logger()
        l.timespans = Timespans.from_json(data['timespans'])
        l.logs = {
            int(channel_id): [LoggedMessage.from_json(m) for m in messages]
            for channel_id, messages in data['messages'].items()
        }
        return l

    def save_to_file(self, f_name=None):
        if f_name is None: f_name = Logger.default_file
        with open(f_name, 'w') as f:
            f.write(json.dumps(self.to_json(), separators=(',', ':')))

    @staticmethod
    def load_from_file(f_name=None):
        if f_name is None: f_name = Logger.default_file
        try:
            with open(f_name) as f:
                return Logger.from_json(json.loads(f.read()))
        except FileNotFoundError:
            return Logger()

    async def log_all(self, channel: discord.TextChannel):

        log_timespans = Timespans()
        log_timespans.add_timespan(discord.utils.DISCORD_EPOCH // 1000 + 1, math.floor(time.time()))
        log_timespans.remove_timespans(self.timespans)

        if channel.id not in self.logs:
            self.logs[channel.id] = []
        msg_logs = self.logs[channel.id]

        i = 0
        for timespan in log_timespans.segments:
            async for msg in channel.history(
                    limit=None,
                    after=datetime.fromtimestamp(timespan.begin - 1),
                    before=datetime.fromtimestamp(timespan.end + 1),
                    oldest_first=True
            ):
                bisect.insort(msg_logs, LoggedMessage(msg), key=lambda m: m.timestamp)
                i += 1
                if i == 200:
                    i = 0
                    self.save_to_file()

                    total = 0
                    for message_list in self.logs.values():
                        total += len(message_list)
                    print(total, 'messages logged')

                self.timespans.add_timespan(discord.utils.DISCORD_EPOCH // 1000 + 1,
                                            math.floor(msg.created_at.timestamp()))

        self.save_to_file()

    def get_random_message(self):
        channels = list(self.logs.keys())
        i = random.choices([
            i for i in range(len(channels))
        ], [
            len(messages) for messages in self.logs.values()
        ])[0]
        messages = self.logs[channels]
        return messages[random.randrange(len(messages))]

    def get_messages(self):
        return (msg for _, messages in self.logs.items() for msg in messages)