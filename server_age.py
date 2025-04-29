import bot
import discord
import sqlalchemy as sql
import log
from log import sql_conn
import database as db
from datetime import datetime
from dateutil.relativedelta import relativedelta
from page_view import BasicPaginatedEmbed

def get_member_join_date(member_id : int) -> datetime:

    result = sql_conn.execute(
        sql.select(sql.func.min(db.msg_table.c.TIMESTAMP))
            .where(db.msg_table.c.AUTHOR == member_id)
    ).scalar()

    return None if result is None else datetime.fromtimestamp(result)

def format_date(date : datetime):

    return date.strftime('%-d %B %Y')

def format_delta(delta : relativedelta):

    age_str = []

    if delta.years != 0: age_str.append(f'{delta.years} years')
    if delta.months != 0: age_str.append(f'{delta.months} months')
    if delta.days != 0: age_str.append(f'{delta.days} days')
    
    return ', '.join(age_str)

@bot.tree.command(name="member-age", description="See how long someone has been a server member for real.")
async def member_age(ctx : discord.Interaction, member : discord.Member):

    date = get_member_join_date(member.id)

    if date is None:
        await ctx.response.send_message(
            "That user doesn't appear to be a member of this server!",
            ephemeral=True
        )
    else:

        date_str = format_date(date)
        age_str = format_delta(relativedelta(datetime.now(), date))

        embed = discord.Embed(
            title = f"{member.name} Server Age",
            description = f'Join Date: **{date_str}**\nDuration: **{age_str}**',
            color = bot.default_color
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        await ctx.response.send_message(embed=embed)

oldest_members_content = None

def invalidate_oldest_cache():

    global oldest_members_content
    oldest_members_content = None

@bot.tree.command(name="oldest-members", description="Rank members by how long they've been here.")
async def oldest_members(ctx : discord.Interaction):

    global oldest_members_content

    followup = False

    if oldest_members_content is None:

        followup = True

        await ctx.response.defer(thinking=True)

        lines = []
        i = 1

        for member, date in sorted(((m, get_member_join_date(m.id)) for m in ctx.guild.members), key=lambda item : item[1].timestamp()):
            if date is None: continue
            date_str = format_date(date)
            lines.append(f'{i}. <@{member.id}> - Joined **{date_str}**')
            i += 1
        
        oldest_members_content = '\n'.join(lines)

    embed = BasicPaginatedEmbed(
        ctx=ctx,
        title='Oldest Server Members',
        content=oldest_members_content
    )

    if followup: await embed.followup()
    else: await embed.send()

log.log_update_callbacks.append(invalidate_oldest_cache)