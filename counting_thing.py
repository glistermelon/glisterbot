import discord
import bot
from random import randrange

COUNTING_CHANNEL_ID = 1257766634546925599
COUNTING_BOT_ID = 726560538145849374

@bot.client.event
async def on_message_edit(before : discord.Message, after : discord.Message):

    if after.channel.id != COUNTING_CHANNEL_ID or before.edited_at: return
    
    has_reaction = False
    for r in after.reactions:
        async for u in r.users():
            if u.id == COUNTING_BOT_ID:
                has_reaction = True
                break
        if has_reaction: break
    if not has_reaction: return

    if randrange(5) == 0:
        await after.channel.send(
            f'@everyone! <@{after.author.id}> just edited their number!',
            reference=after
        )