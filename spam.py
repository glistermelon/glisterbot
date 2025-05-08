import discord
import bot
import asyncio

SPAM_PERIOD = 5
MAX_PINGS = 100

BANNED_CHANNELS = [
    931838136223412239
]

active_tasks = []

async def spam_func(target_id, channel : discord.TextChannel, pings : int):
    for _ in range(pings):
        await channel.send(f'<@{target_id}>')
        await asyncio.sleep(SPAM_PERIOD)

@bot.tree.command(name="spam-ping", description="Spam ping someone.")
async def spam_ping(ctx : discord.Interaction, target : discord.Member, number_of_pings : int):

    if number_of_pings > MAX_PINGS:
        await ctx.response.send_message(
            f'You can only ping at most {MAX_PINGS} times!',
            ephemeral=True
        )
        return

    await ctx.response.defer(thinking=False)

    task = asyncio.create_task(spam_func(target.id, ctx.channel, number_of_pings))
    active_tasks.append(task)

@bot.tree.command(name="stop-spam-ping", description="[ADMIN ONLY] Stop spam pinging.")
async def cancel_spam(ctx : discord.Interaction):

    if not bot.is_admin(ctx.guild, ctx.user):
        await ctx.response.send_message(
            "You must be an admin to do this!"
        )
        return
    
    await ctx.response.send_message(
        "Stopping all spam ping sessions."
    )

    for task in active_tasks:
        task.cancel()