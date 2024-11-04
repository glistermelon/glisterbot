import events
import discord
import re
import database as db
from database import sql, sql_conn
from sqlalchemy.dialects import postgresql
import datetime
import bot

RALLY_REGEX = 'Ah\\.\\.\\. a little whisper here, a sly nudge there\\.\\.\\. and voilà! .+ has mysteriously risen by .+ while .+ has\\.\\.\\. shall we say, slipped by .+\\. Until the morrow, feline schemer\\.\\.\\.'

async def detect_rally(message : discord.Message):

    if message.author.id != 1167542762212688003 or message.interaction_metadata is None:
        return

    user = message.interaction_metadata.user

    re_search = re.search(RALLY_REGEX, message.content)
    if re_search is None: return
    if re_search.span()[0] != 0: return

    booned = message.content[61 : message.content.index('has mysteriously', 61) - 1]
    baned = message.content[message.content.index('while', 61 + len(booned)) + 6 : message.content.index('has... shall we say,') - 1]

    if baned == 'Green Cat Technology' or booned == 'Pop Cat Hits':

        try:
            await user.timeout(datetime.timedelta(minutes=5))
        except:
            pass

        await message.channel.send(
            embed=discord.Embed(
                color=0xff0000,
                title='Hey!',
                description=f'<@{user.id}> has been muted for 5 minutes for being a traitor!'
            ),
            reference=message
        )

        return
    
    if booned == 'Green Cat Technology':

        sql_conn.execute(
            postgresql.insert(db.mute_table)
                .values(
                    USER_ID=user.id,
                    TIME=5
                )
                .on_conflict_do_update(
                    index_elements=['USER_ID'],
                    set_=dict(TIME=db.mute_table.c.TIME + 5)
                )
        )
        sql_conn.commit()

        await message.channel.send(
            embed=discord.Embed(
                color=0x00ff00,
                title='Thamk you!!!',
                description='For being awesome you now have +5 minutes of time you can use to mute non-awesome people...'
            ),
            reference=message
        )

        return
    
events.add_listener('on_message', detect_rally)

@bot.tree.command(name='mute', description='Use minutes from Purrtun rallies to mute your opps!')
async def rally_mute(ctx : discord.Interaction, user : discord.Member, minutes : int, reason : str = None):

    if minutes <= 0:
        await ctx.response.send_message(
            'Choose a positive integer, please!',
            ephemeral=True
        )
        return

    available = sql_conn.execute(
        sql.select(db.mute_table)
            .where(db.mute_table.c.USER_ID == ctx.user.id)
    ).first()

    if available is None or available.TIME < minutes:
        await ctx.response.send_message(
            embed=discord.Embed(
                color=0xff0000,
                title='You can\'t mute for that long!',
                description=f'You only have `{available.TIME}` minute{'s' if available.TIME > 1 else ''} available.'
            ),
            ephemeral=True
        )
        return
    
    try:
        if user.is_timed_out():
            await user.timeout(user.timed_out_until + datetime.timedelta(minutes=minutes))
        else:
            await user.timeout(datetime.timedelta(minutes=minutes))
    except:
        await ctx.response.send_message(
            embed=discord.Embed(
                color=0xff0000,
                title='You can\'t mute that user!',
                description=f'They probably have higher perms than Glisterbot.'
            ),
            ephemeral=True
        )
        return
    
    desc = f'<@{user.id}> has been muted by <@{ctx.user.id}> for {minutes} minutes'
    if reason: desc += f' for "{reason}"'
    await ctx.response.send_message(
        embed=discord.Embed(
            color=0x00ff00,
            title='get muted idiot',
            description=desc
        ),
        ephemeral=True
    )

    sql_conn.execute(
        sql.update(db.mute_table)
            .where(db.mute_table.c.USER_ID == ctx.user.id)
            .values(TIME=db.mute_table.c.TIME - minutes)
    )
    sql_conn.commit()