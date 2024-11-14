import discord
from random import randrange, shuffle
from types import SimpleNamespace
import json
import bot
import asyncio
import events
import os
import base64
import math
from unidecode import unidecode

class Game:
    channels = []

    @staticmethod
    def is_channel_free(channel : discord.TextChannel):
        return channel.id not in Game.channels
    
    @staticmethod
    def free_channel(channel : discord.TextChannel):
        while channel.id in Game.channels:
            Game.channels.remove(channel.id)
    
    @staticmethod
    def claim_channel(channel : discord.TextChannel):
        Game.channels.append(channel.id)

def get_help_embed():
    help = open('wordbomb/help.md').read()
    i = help.index('\n')
    return discord.Embed(
        title=help[:i],
        description=help[i + 2:],
        color=bot.default_color
    )

# changing these will not actually change the values for the entire game
diff_freq = {
    'easy': 100,
    'medium': 300,
    'hard': 500
}

language_names = {
    'en': 'english',
    'es': 'español',
    'fr': 'français'
}

def extract_phrases(word_list : list[str], target_period : int):
    phrases = {}
    for word in word_list:
        for phrase_len in range(2, 4):
            for i in range(len(word) - phrase_len + 1):
                phrase = word[i : i + phrase_len]
                try:
                    phrases[phrase] += 1
                except:
                    phrases[phrase] = 1
    for phrase, count in phrases.items():
        period = len(word_list) / count
        if period <= target_period:
            yield phrase, [i for i in range(len(word_list)) if phrase in word_list[i]], period

def encode_number_list(numbers : list[int]):
    numbers = sorted(numbers)
    numbers = [numbers[0]] + [numbers[i] - numbers[i - 1] for i in range(1, len(numbers))]
    byte_list = bytearray()
    for n in numbers:
        length = math.ceil(math.log2(n + 1) / 8)
        byte_list.append(length)
        byte_list += n.to_bytes(length)
    return bytes(byte_list)

def decode_number_list(byte_list : bytes):
    i = 0
    numbers = []
    while i < len(byte_list):
        length = byte_list[i]
        numbers.append(int.from_bytes(byte_list[i + 1 : i + 1 + length]))
        i += length + 1
    for i in range(1, len(numbers)):
        numbers[i] += numbers[i - 1]
    return numbers

def update_phrase_cache():
    for language in ('en', 'es', 'fr'):
        if language in os.listdir('wordbomb/words'):
            continue
        print(f'Updating phrase cache for language: \'{language}\'')
        word_list = json.loads(open(f'wordbomb/words/{language}.json').read())
        os.mkdir(f'wordbomb/words/{language}')
        for diff_name, diff_period in diff_freq.items():
            os.mkdir(f'wordbomb/words/{language}/{diff_name}')
        for phrase, word_ids, period in extract_phrases(word_list, max(diff_freq.values())):
            encoded = str(base64.urlsafe_b64encode(bytes(ord(c) for c in phrase)))[2:-1]
            for diff_name, diff_period in diff_freq.items():
                data = encode_number_list(word_ids)
                if period <= diff_period:
                    with open(f'wordbomb/words/{language}/{diff_name}/{encoded}', 'wb') as file:
                        file.write(data)

update_phrase_cache()

class WordBomb:

    help = get_help_embed()
    dictionaries = {
        file[:file.index('.')] : json.loads(open(f'wordbomb/words/{file}').read())
        for file in os.listdir('wordbomb/words') if file.endswith('.json')
    }

    def __init__(self, ctx : discord.Interaction, difficulty : str, language : str):

        self.ctx = ctx

        self.difficulty = difficulty
        self.language = language
        self.phrases = os.listdir(f'wordbomb/words/{language}/{difficulty}')
        self.dictionary = WordBomb.dictionaries[language]

        self.players = []
        self.defeated_players = []
        
        self.used_words = []

        self.config = SimpleNamespace()
        self.config.lives = 3
        self.config.time = 10

        self.started = False
        self.cancelled = False

    @staticmethod
    def score(number, time, lives, difficulty):
        score = ((time - 20) ** 2) / 80 * 60000 / diff_freq[difficulty] * number / 4
        if score != 0: score += 75 * lives
        return int(score)

    class View(discord.ui.View):

        def init(self, game):
            self.game = game

        @discord.ui.button(label="Start Game", style=discord.ButtonStyle.green)
        async def start(self, ctx, button):
            if ctx.user.id != self.game.ctx.user.id:
                await ctx.response.send_message('Only the creator of the game can start it!', ephemeral=True)
                return
            await ctx.response.send_message('Starting WordBomb game...')
            await self.game.play_game()

        @discord.ui.button(label="Join Game", style=discord.ButtonStyle.blurple)
        async def join(self, ctx, button):
            if self.game.includes_player(ctx.user):
                await ctx.response.send_message('You have already joined this game!', ephemeral=True)
                return
            await self.game.add_player(ctx.user)
            await ctx.response.send_message('You successfully joined the game!', ephemeral=True)

        @discord.ui.button(label="Leave Game", style=discord.ButtonStyle.red)
        async def leave(self, ctx, button):
            if not self.game.includes_player(ctx.user):
                await ctx.response.send_message('You aren\'t part of this game!', ephemeral=True)
                return
            await self.game.remove_player(ctx.user)
            await ctx.response.send_message('You successfully left the game.', ephemeral=True)

        @discord.ui.button(label="Help", style=discord.ButtonStyle.grey)
        async def help(self, ctx, button):
            await ctx.response.send_message(embed=WordBomb.help, ephemeral=True)
    
    class Player:

        def __init__(self, user : discord.User, lives : int):
            self.user = user
            self.lives = lives
            self.alphabet = [c for c in 'abcdefghijklmnopqrstuvwxyz']
        
        def needs_letter(self, letter : str):
            return letter in self.alphabet
        
        def mark_letter_used(self, letter : str):
            if letter in self.alphabet:
                self.alphabet.remove(letter)
            
        def used_all_letters(self):
            return len(self.alphabet) == 0

        def reset_alphabet(self):
            self.alphabet = [c for c in 'abcdefghijklmnopqrstuvwxyz']
        
        def add_life(self):
            self.lives += 1
        
        def take_life(self):
            self.lives -= 1
        
        def is_dead(self):
            return self.lives == 0

    async def update_queue_embed(self):
        desc = self.get_queue_description()
        self.queue_embed.description = desc
        await self.ctx.edit_original_response(embed=self.queue_embed)

    async def add_player(self, user : discord.User):
        if self.includes_player(user): return
        self.players.append(WordBomb.Player(user, self.config.lives))
        await self.update_queue_embed()

    async def remove_player(self, user : discord.User, defeated : bool = False):
        for i in range(len(self.players)):
            if self.players[i].user.id == user.id:
                self.players.pop(i)
                break
        if defeated: self.defeated_players.append(user)
        elif len(self.players) == 0: await self.cancel_game()
        else: await self.update_queue_embed()

    def includes_player(self, user : discord.User):
        for player in self.players:
            if player.user.id == user.id:
                return True
        return False
    
    def get_queue_description(self):

        lang = language_names[self.language]
        lang = lang[0].upper() + lang[1:]

        desc = f'**Starting Lives:** {self.config.lives}'
        desc += f'\n**Turn Time:** {self.config.time}'
        desc += f'\n**Language:** {lang}'
        desc += f'\n**Players:**'
        
        for player in self.players:
            desc += f'\n<@{player.user.id}>'

        return desc
    
    async def start_queue(self):

        Game.claim_channel(self.ctx.channel)

        self.view = WordBomb.View()
        self.view.init(self)

        self.queue_embed = discord.Embed(
            title='Word Bomb',
            description=self.get_queue_description(),
            color=bot.default_color
        )
        image = discord.File("wordbomb/bomb.png",filename="bomb.png")
        self.queue_embed.set_thumbnail(url="attachment://bomb.png")
        await self.ctx.response.send_message(file=image, embed=self.queue_embed, view=self.view)

        await self.add_player(self.ctx.user)
    
    async def cancel_game(self):
        if self.started: return
        self.cancelled = True
        self.view.stop()
        await self.ctx.channel.send('Game cancelled by host!', reference=await self.ctx.original_response())
        Game.free_channel(self.ctx.channel)
    
    async def play_game(self):
        if self.cancelled: return
        self.started = True
        self.view.stop()
        shuffle(self.players)
        while len(self.players) >= 1: # todo
            for player in self.players:
                await self.test_player(player)
        winner = self.players[0]
        score = WordBomb.score(len(self.defeated_players), self.config.time, winner.lives, self.difficulty)
        embed=discord.Embed(
            title=f'{winner.user.name} is the victor! :partying_face:',
            description=f'<@{winner.user.id}>, you earned {bot.commafy(score)} points.',
            color=0x00FF00
        )
        embed.set_image(url=winner.user.display_avatar.url)
        await self.ctx.channel.send(embed=embed)
        Game.free_channel(self.ctx.channel)
    
    async def test_player(self, player : Player):
        phrase = self.phrases[randrange(len(self.phrases))]
        self.answer_indices = decode_number_list(open(f'wordbomb/words/{self.language}/{self.difficulty}/{phrase}', 'rb').read())
        phrase = str(base64.urlsafe_b64decode(bytes([ord(c) for c in phrase])))[2:-1]
        alphabet = ''
        for s in ('abcdefghijklm', 'nopqrstuvwxyz'):
            for c in s:
                if player.needs_letter(c):
                    alphabet += f':regional_indicator_{c}:'
                else:
                    alphabet += ':heavy_minus_sign:'
            alphabet += '\n'
        embed = discord.Embed(
            title = f"**{phrase.upper()}**",
            description = f"It's <@{player.user.id}>'s turn!\n\n{alphabet}",
            color = bot.neutral_color
        )
        embed.set_thumbnail(url=player.user.display_avatar.url)
        await self.ctx.channel.send(embed=embed)

        self.active_user = player.user
        self.phrase = phrase

        self.event = asyncio.Event()
        events.add_listener('on_message', self.callback, channel = self.ctx.channel)
        try:
            await asyncio.wait_for(self.event.wait(), timeout=self.config.time)
        except asyncio.TimeoutError:
            pass
        else:
            await self.event.wait()
            events.rm_listener('on_message', self.callback)
            return
        events.rm_listener('on_message', self.callback)
        player.take_life()
        embed = None
        if player.is_dead():
            embed = discord.Embed(description=f"**<@{player.user.id}> is out!**", color=0xff0000)
            await self.remove_player(player.user, True)
        else:
            embed = discord.Embed(description=f"**<@{player.user.id}> failed!** {player.lives} lives left", color=0xff9900)
        await self.ctx.channel.send(embed=embed)
    
    async def callback(self, msg : discord.Message):
        if msg.author != self.active_user: return
        content = unidecode(msg.content.strip().lower())
        if self.phrase in content and content in self.used_words:
            await msg.add_reaction('🔂')
            return
        if self.phrase not in content or content not in (self.dictionary[i] for i in self.answer_indices):
            await msg.add_reaction('❌')
            return
        
        self.used_words.append(content)

        player = None
        for p in self.players:
            if p.user == msg.author:
                player = p
                break
        if player is None: return # this should never happen
        embed = None
        for letter in content:
            player.mark_letter_used(letter)
        if player.used_all_letters():
            player.reset_alphabet()
            player.add_life()
            embed = discord.Embed(
                description=f"**<@{msg.author.id}> passed and earned an extra life!**",
                color=0x00FF00
            )
        else:
            embed = discord.Embed(description=f"**<@{msg.author.id}> passed!**", color=0x00FF00)

        # interrupt the waiting test_player, but set another event
        # to wait until bot responds before continuing to next round
        self.event.set()
        self.event = asyncio.Event()

        await msg.add_reaction('✅')
        await msg.channel.send(embed=embed, reference=msg, mention_author=False)

        self.event.set()

#@discord.app_commands.describe(
#        lives="The number of times a player can fail before they're eliminated.",
#        time="The amount of time (in seconds) each player is given to guess.",
#)
@bot.tree.command(name='wordbomb', description='Play wordbomb on Discord!')
@discord.app_commands.choices(difficulty=[
    discord.app_commands.Choice(name='easy', value='easy'),
    discord.app_commands.Choice(name='medium', value='medium'),
    discord.app_commands.Choice(name='hard', value='hard')
])
@discord.app_commands.choices(language=[
    discord.app_commands.Choice(name='english', value='en'),
    discord.app_commands.Choice(name='español', value='es'),
    discord.app_commands.Choice(name='français', value='fr')
])
async def callback(ctx : discord.Interaction, difficulty : discord.app_commands.Choice[str], language : discord.app_commands.Choice[str] = None):
    if not Game.is_channel_free(ctx.channel):
        await ctx.response.send_message('There is already a game present in this channel!',ephemeral=True)
        return
    await WordBomb(ctx, difficulty.value, language.value if language else 'en').start_queue()