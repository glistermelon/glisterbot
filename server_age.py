import bot
import discord
import sqlalchemy as sql
from log import sql_conn
import database as db
from datetime import datetime
from dateutil.relativedelta import relativedelta

@bot.tree.command(name="member-age", description="See how long someone has been a server member for real.")
async def member_age(ctx : discord.Interaction, member : discord.Member):

    result = sql_conn.execute(
        sql.select(db.msg_table).where(db.msg_table.c.AUTHOR == member.id)
        .order_by(db.msg_table.c.TIMESTAMP.asc())
        .limit(1)
    ).first()

    if result is None:
        await ctx.response.send_message(
            "That user doesn't appear to be a member of this server!",
            ephemeral=True
        )
    else:

        date = datetime.fromtimestamp(result.TIMESTAMP)
        date_str = date.strftime('%-d %B %Y')

        delta = relativedelta(datetime.now(), date)
        age_str = []
        if delta.years != 0: age_str.append(f'{delta.years} years')
        if delta.months != 0: age_str.append(f'{delta.months} months')
        if delta.days != 0: age_str.append(f'{delta.days} days')
        age_str = ', '.join(age_str)

        embed = discord.Embed(
            title = f"{member.name} Server Age",
            description = f'Join Date: **{date_str}**\nDuration: **{age_str}**',
            color = bot.default_color
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        print(embed)
        await ctx.response.send_message(embed=embed)