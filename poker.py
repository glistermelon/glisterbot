# This code is terrible but I didn't intend for this to be a permanent feature at the time of writing
# And I don't wanna refactor it so...
# Currently only supports one server because nobody else uses glisterbot so
# If anyone actually wants multi-server support contact me or leave a github issue or something

import discord
from discord import app_commands
import bot
from types import SimpleNamespace
from random import randrange
from functools import partial
import asyncio
import json
import requests
import time
import math

SERVER_ID = 931838136223412235
AUTH_TOKEN = json.loads(open('config.json').read())['unb_token']

rate_limits = {}
idiot_list = []
active_games = []

def unbapi(method, url, userid, jsondata = None):
    # print(url)
    rate_limited = userid in rate_limits
    if rate_limited and rate_limits[userid] < time.time():
        rate_limited = False
        del rate_limits[userid]
    res = None
    if not rate_limited:
        res = requests.request(
            method, url,
            headers={ 'Authorization': AUTH_TOKEN },
            json=jsondata
        )
    if (rate_limited or res.status_code == 429):
        data = json.loads(res.content)
        wait = math.ceil((data['retry_after'] / 1000) if not rate_limited else (rate_limits[userid] - time.time()))
        if not rate_limited: rate_limits[userid] = time.time() + wait
        return f'UnbelievaBoat is rate limiting Glisterbot. Try again in {wait} seconds, maybe.'
    if (res.status_code != 200):
        return f'Unexpected error ({res.status_code}) while interacting with UnbelievaBoat\'s API.'
    return json.loads(res.content)

def get_balance(userid):
    data = unbapi('GET', f'https://unbelievaboat.com/api/v1/guilds/{SERVER_ID}/users/{userid}', userid)
    return data if type(data) == str else data['cash']

def modify_balance(userid, change):
    return unbapi('PATCH', f'https://unbelievaboat.com/api/v1/guilds/{SERVER_ID}/users/{userid}', userid, { 'cash': change })

cards_emojis = {
    'cloud_still': '<:cloud:1247400331802054687>',
    'cloud_flip': '<a:cloud:1247400330627649619>',
    'mushroom_still': '<:mushroom:1247400340794507304>',
    'mushroom_flip': '<a:mushroom:1247400422432575519>',
    'fireflower_still': '<:fireflower:1247400333454606377>',
    'fireflower_flip': '<a:fireflower:1247400332716146728>',
    'luigi_still': '<:luigi:1247400335329202216>',
    'luigi_flip': '<a:luigi:1247400334507376721>',
    'mario_still': '<:mario:1247400337875140609>',
    'mario_flip': '<a:mario:1247400411074138142>',
    'star_still': '<:star:1247400344334631013>',
    'star_flip': '<a:star:1247400434847584296>',
    'back': '<:back:1247400329943711805>',
    'plus': '<:plus:1247425658871877663>',
    'minus': '<:minus:1247426369147768892>'
}

Faces = SimpleNamespace()
Faces.CLOUD = 0
Faces.MUSHROOM = 1
Faces.FIREFLOWER = 2
Faces.LUIGI = 3
Faces.MARIO = 4
Faces.STAR = 5
NUM_FACES = 6

Results = SimpleNamespace()
Results.JUNK = 0
Results.ONE_PAIR = 1
Results.TWO_PAIRS = 2
Results.THREE_OF_A_KIND = 3
Results.FULL_HOUSE = 4
Results.FOUR_OF_A_KIND = 5
Results.FLUSH = 6

result_names = {
    Results.JUNK: 'Junk',
    Results.ONE_PAIR: 'One Pair',
    Results.TWO_PAIRS: 'Two Pairs',
    Results.THREE_OF_A_KIND: 'Three of a Kind',
    Results.FULL_HOUSE: 'Full House',
    Results.FOUR_OF_A_KIND: 'Four of a Kind',
    Results.FLUSH: 'Flush'
}

# I have no idea if these are properly balanced
result_multipliers = {
    Results.JUNK: 1,
    Results.ONE_PAIR: 0.1,
    Results.TWO_PAIRS: 0.1,
    Results.THREE_OF_A_KIND: 0.5,
    Results.FULL_HOUSE: 1,
    Results.FOUR_OF_A_KIND: 5,
    Results.FLUSH: 50
}

SLEEP = 1

faces = ('cloud', 'mushroom', 'fireflower', 'luigi', 'mario', 'star',)
for i in range(len(faces)):
    s = faces[i]
    cards_emojis[i] = {
        'still': cards_emojis[f'{s}_still'],
        'flip': cards_emojis[f'{s}_flip'],
    }
del faces
cards_emojis[-1] = {
    'still': cards_emojis['back'],
    'flip': cards_emojis['back']
}

@bot.tree.command(name='luigi-poker', description='Your favorite childhood gambling game.')
async def poker(ctx, bet : str):
    await Poker(ctx, bet).start()

class Poker:

    def __init__(self, ctx, bet : str):
        self.ctx = ctx
        self.bet = bet
        self.hits = []
    
    async def start(self):
        if (self.ctx.user.id in active_games):
            await self.ctx.response.send_message(
                'Finish the game you\'re currently playing first!\nIf you encounter this error while not already playing another game,'
                ' use /flush to resolve it. **Do not sporadically use this command or the bot may go offline.** Imagine fixing bugs...',
                ephemeral=True
            )
            return
        
        all = self.bet in ('a', 'm', 'all', 'max')

        if not all:
            if self.bet in ('', '-'): self.bet = '0'
            negative = self.bet.startswith('-')
            if negative: self.bet = self.bet[1:]
            if not self.bet.isnumeric():
                await self.ctx.response.send_message('You have to specify a proper number!')
                return
            self.bet = int(self.bet)
            if negative: self.bet = -self.bet

            if self.bet < 0:
                await self.ctx.response.send_message('Nice try idiot. The next game you win will have a negative multiplier. Good luck...')
                if self.ctx.user.id not in idiot_list:
                    idiot_list.append(self.ctx.user.id)
                return
            if self.bet == 0:
                await self.ctx.response.send_message('You have to bet something!')
                return
        
        bal = get_balance(self.ctx.user.id)
        if type(bal) != str:
            if all:
                if bal == 0:
                    await self.ctx.response.send_message('You have to bet something!')
                    return
                self.bet = bal
            if self.bet > bal:
                await self.ctx.response.send_message('You can\'t afford that bet! Note that Glisterbot cannot take money out of your bank.')
                return
            bal = modify_balance(self.ctx.user.id, -self.bet)
        if type(bal) == str:
            await self.ctx.response.send_message(embed=discord.Embed(
                title='Failed to start your Luigi Poker game!',
                description=bal,
                color=0xff0000
            ))
            return
        active_games.append(self.ctx.user.id)
        self.hand = [randrange(NUM_FACES) for _ in range(5)]
        await self.ctx.response.send_message(embed=self.get_embed(True, True), view=self.get_view())
        await asyncio.sleep(SLEEP)
        await self.ctx.edit_original_response(embed=self.get_embed(True, False), view=self.get_view())

    def get_embed(self, show_instruction : bool, reveal_all : bool, hide_hits : bool = True, all_still : bool = False, outcome = None, err = None, mod_bal = 0, idiot_alert = False):
        desc = None
        if show_instruction: desc = f'Bet: {self.bet:,} :coin:'
        elif outcome[1] == 0: desc = 'Tie! Bet returned.'
        else:
            desc = f'Outcome: {cards_emojis['plus' if mod_bal >= 0 else 'minus']}{abs(mod_bal):,} :coin:'
            if idiot_alert: desc += '\n:rofl: Your earnings were multiplied by -1 for being an idiot!'
            if err: desc += f'\n:warning: **{err}**'
        desc += '\n\n**Luigi\'s Hand:** '
        if show_instruction: desc += cards_emojis['back'] * 5
        else:
            desc += ''.join([cards_emojis[outcome[0][i]]['still' if all_still else 'flip'] for i in range(5)])
            desc += '\u1CBC' + result_names[outcome[3]]

        desc += '\n\n**Your Hand:**\u1CBC\u1CBC' + ''.join(
            [
                cards_emojis[self.hand[i] if (not hide_hits) or i not in self.hits else -1]
                    ['flip' if not all_still and (reveal_all or i in self.hits) else 'still']
                for i in range(5)
            ]
        )
        if show_instruction: desc += '\n\n**Select cards to draw, then hold to finalize your deck!**'
        else: desc += '\u1CBC' + result_names[outcome[2]]

        color = None
        if not outcome: color = 0x2b2d31
        elif outcome[1] == 0: color = 0xff7c0a
        elif outcome[1] == 1: color = 0x00ff00
        else: color = 0xff0000

        embed = discord.Embed(
                title='Luigi Poker',
                color=color,
                description=desc
            )
        return embed
    
    def get_view(self):
        view = discord.ui.View()

        for i in range(5):
            blank = i in self.hits
            button = discord.ui.Button(
                style=discord.ButtonStyle.danger,
                emoji=cards_emojis[self.hand[i]]['still'] if not blank else None,
                label='\u1CBC' if blank else None
            )
            button.callback = partial(self.hit, i)
            view.add_item(button)

        hold = discord.ui.Button(style=discord.ButtonStyle.blurple, label='Hold')
        hold.callback = self.hold
        view.add_item(hold)

        help = discord.ui.Button(style=discord.ButtonStyle.green, label='How to Play')
        help.callback = self.how_to
        view.add_item(help)

        self.view = view
        return view

    async def hit(self, i, ctx):
        if (ctx.user.id != self.ctx.user.id):
            await ctx.response.send_message('That isn\'t your game silly!', ephemeral=True)
            return
        if i in self.hits:
            await ctx.response.defer()
            return
        self.hits.append(i)
        self.hand[i] = randrange(NUM_FACES)
        if len(self.hits) == 5: await self.hold(ctx)
        else:
            await self.ctx.edit_original_response(embed=self.get_embed(True, False), view=self.get_view())
            await ctx.response.defer()
    
    async def hold(self, ctx):

        if (ctx.user.id != self.ctx.user.id):
            await ctx.response.send_message('That isn\'t your game silly!', ephemeral=True)
            return
        outcome = self.outcome()

        active_games.remove(self.ctx.user.id)
        
        self.view.stop()

        mod_bal = 0
        if outcome[1] == -1: mod_bal = -self.bet
        else: mod_bal = 0 if outcome[1] == 0 else self.bet * result_multipliers[outcome[2]]

        idiot = False
        if outcome[1] != -1 and self.ctx.user.id in idiot_list:
            idiot_list.remove(self.ctx.user.id)
            mod_bal = -mod_bal
            idiot = True

        err = None
        if outcome[1] != -1:
            err = modify_balance(self.ctx.user.id, mod_bal + self.bet)
            if type(err) != str: err = None
        await self.ctx.edit_original_response(embed=self.get_embed(False, False, False, False, outcome, err, mod_bal, idiot))
        await ctx.response.defer()
        await asyncio.sleep(SLEEP)
        await self.ctx.edit_original_response(embed=self.get_embed(False, False, False, True, outcome, err, mod_bal, idiot))
    
    async def how_to(self, ctx):

        cloud = cards_emojis['cloud_still']
        mushroom = cards_emojis['mushroom_still']
        fireflower = cards_emojis['fireflower_still']
        luigi = cards_emojis['luigi_still']
        mario = cards_emojis['mario_still']
        star = cards_emojis['star_still']

        await ctx.response.send_message(ephemeral=True, embed=discord.Embed(
            title = 'How to Play Luigi Poker',
            description=
                '**Glisterbot\'s Luigi Poker is based on the table minigame from New Super Mario Bros (DS).** '
                'It is easy to learn. Luigi is the dealer, and you are playing against him. '
                'You and Luigi each recieve 5 cards and hide them from each other. '
                'You and Luigi both can discard any number of the 5 cards from your hand and draw new cards to replace them. '
                'The winner is determined based on patterns in your hands, according to the following ranking system (the list goes from best to worst):\n\n'
                f'**Flush:** 5 cards with the same symbol, such as: {star}{star}{star}{star}{star}\n'
                f'**Four of a Kind:** 4 cards with the same symbol, such as: {star}{star}{star}{star}{mushroom}\n'
                f'**Full House:** 3 cards with the same symbol, where the remaining 2 cards also have the same symbols as each other, such as: {star}{star}{star}{mushroom}{mushroom}\n'
                f'**Three of a Kind:** 3 cards with the same symbol, such as: {star}{star}{star}{mushroom}{cloud}\n'
                f'**Two Pairs:** 2 sets of 2 cards each where both cards have the same symbol, such as: {star}{star}{mushroom}{mushroom}{cloud}\n'
                f'**One Pair:** 2 cards with the same symbol, but no other matching cards, such as: {star}{star}{fireflower}{mushroom}{cloud}\n'
                f'**Junk:** not a single match, such as: {star}{mario}{luigi}{fireflower}{mushroom}\n\n'
                'Ties are broken by the symbol on the set of cards with the most matches '
                '(most matches as in, if you and Luigi both have a Full House, the symbols on the sets of 3, not the sets of 2, are compared to break the tie). '
                'The symbols are ranked in the following order, from best to worst:\n'
                f'Star {star}, Mario {mario}, Luigi {luigi}, Fire flower {fireflower}, Mushroom {mushroom}, Cloud {cloud}'
        ))

    @staticmethod
    def get_rank(hand):
        counts = {}
        for card in hand:
            try:
                counts[card] += 1
            except:
                counts[card] = 1
        reverse_counts = { v:k for k,v in counts.items() }
        combos = { n : sum(1 for c in counts.values() if c == n) for n in range(2, 6) }
        if combos[5]: return (Results.FLUSH, hand[0], [])
        if combos[4]: return (Results.FOUR_OF_A_KIND, reverse_counts[4], [i for i in range(5) if hand[i] == reverse_counts[1]])
        if combos[3] and combos[2]: return (Results.FULL_HOUSE, reverse_counts[3], [])
        if combos[3]: return (Results.THREE_OF_A_KIND, reverse_counts[3], [hand.index(max([c for c in hand if counts[c] == 1]))])
        if combos[2] == 2: return (Results.TWO_PAIRS, max([c for c in hand if counts[c] == 2]), [i for i in range(5) if hand[i] == reverse_counts[1]])
        if combos[2]: return (Results.ONE_PAIR, reverse_counts[2], [i for i in range(5) if hand[i] == reverse_counts[1]])
        return (Results.JUNK, 0, list(range(5)))
    
    def outcome(self):
        luigi_hand = [randrange(NUM_FACES) for _ in range(5)]
        for i in Poker.get_rank(luigi_hand)[2]:
            luigi_hand[i] = randrange(NUM_FACES)
        luigi_rank = Poker.get_rank(luigi_hand)
        player_rank = Poker.get_rank(self.hand)
        comp = 0
        if player_rank[0] > luigi_rank[0]: comp = 1
        elif player_rank[0] < luigi_rank[0]: comp = -1
        elif player_rank[1] > luigi_rank[1]: comp = 1
        elif player_rank[1] < luigi_rank[1]: comp = -1
        # print(self.hand, luigi_hand, player_rank, luigi_rank, (luigi_hand, comp, player_rank[0], luigi_rank[0]))
        return (luigi_hand, comp, player_rank[0], luigi_rank[0])
