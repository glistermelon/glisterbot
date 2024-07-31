import bot
import discord
from discord import app_commands
import datetime
import time
import sqlalchemy as sql
from log import sql_conn


#name = "top_messagers"
#description = "See who has commented the most in this server."

@bot.tree.command(name="top-messagers", description="See who has sent the most messages.")
@app_commands.choices(category=[
    app_commands.Choice(name='total messages',value=0),
    app_commands.Choice(name='messages per day',value=1)]
)
async def callback(ctx, category : app_commands.Choice[int]):

    await ctx.response.send_message("Generating stats...", ephemeral=True)

    category = category.value

    # I'm not bothering with a better way to implement these right now
    # At the very least AUTHOR is an int so this should be perfectly safe
    authors = (row.AUTHOR for row in sql_conn.execute(sql.text('SELECT DISTINCT ON ("AUTHOR") "AUTHOR" FROM "Messages";')))
    
    ranks = {}
    earliest = time.time()
    latest = 0
    for author in authors:
        stats = sql_conn.execute(sql.text(f'SELECT COUNT(*), MAX("TIMESTAMP"), MIN("TIMESTAMP") FROM "Messages" WHERE "AUTHOR"={author}')).first()
        ranks[author] = stats.count
        if stats.min < earliest: earliest = stats.min
        if stats.max > latest: latest = stats.max

    keys = list(ranks.keys())
    keys.sort(reverse=True,key=lambda k:ranks[k])

    desc = f'Total messages: **{'{:,}'.format(sum(ranks.values()))}**\n'

    for i in range(len(keys)):
        user = discord.utils.get(bot.client.users, id = keys[i])
        if user != None and not user.bot:
            num = ranks[keys[i]]
            if category == 0: num = '{:,}'.format(int(num))
            else: num = round(num / ((latest - earliest) / 60 / 60 / 24), 4)
            desc += f'{i + 1}. <@{keys[i]}> - {num} messages\n'

    await ctx.channel.send(
        f"<@{ctx.user.id}>",
        embed=discord.Embed(
            title = "Members with the most messages:",
            description = desc,
            color = bot.default_color
        )
    )
