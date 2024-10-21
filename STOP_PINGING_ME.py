import discord
import bot
import events
from datetime import datetime, timedelta

pinging_enabled = True

offense_counts = {}
offense_times = {}

@bot.tree.command(name='allow-pings', description='Stop people from pinging you grrrrr')
async def allow_pings(ctx : discord.Interaction, allow : bool):
    if ctx.user.id != 674819147963564054:
        await ctx.response.send_message('ermm who are you?????')
        return
    global pinging_enabled
    pinging_enabled = allow
    await ctx.response.send_message(f'Pings have been {'allowed' if allow else 'disallowed'}.')

async def on_message(message : discord.Message):

    if pinging_enabled: return
    
    if message.reference:
        ref = await bot.client.get_channel(message.reference.channel_id).fetch_message(message.reference.message_id)
        if ref.author.id == 674819147963564054: return
    
    glistermelon = bot.client.get_guild(931838136223412235).get_member(674819147963564054)
    if glistermelon not in message.mentions: return

    await message.delete()

    id = message.author.id
    now = datetime.now()

    if id in offense_times and (now - offense_times[id]).total_seconds() < 3600:
        offense_counts[id] += 1
    else:
        offense_counts[id] = 1
    offense_times[id] = now

    await message.author.timeout(
        timedelta(seconds=int(1.5*(2**offense_counts[id]))),
        reason='stop pinging me!!!!'
    )

events.add_listener('on_message', on_message)