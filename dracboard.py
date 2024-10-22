from quote import MessageEmbed
import discord
import bot
import database as db
from database import sql, sql_conn

DRACBOARD_CHANNEL_ID = 1296939876616503297
REACT_EMOJI ='🧛' 
EMOJIS = '🧛🧛🏻🧛🏼🧛🏽🧛🏾🧛🏿🧛‍♀️🧛🏻‍♀️🧛🏼‍♀️🧛🏽‍♀️🧛🏾‍♀️🧛🏿‍♀️🧛‍♂️🧛🏻‍♂️🧛🏼‍♂️🧛🏽‍♂️🧛🏾‍♂️🧛🏿‍♂️'
MINIMUM_REACTION_COUNT = 3
PING_STR = '<@&1297757042454429809>'
EXEMPT_CHANNELS = [
    998219646668898384, # roles
    1296939876616503297, # dracboard
    1028873703863373955 # glisterbot-announcements
]

async def dracboard_pin(m : discord.Message):

    sql_conn.execute(
        sql.insert(db.dracboard_table).values(
            MESSAGE_ID=m.id
        )
    )
    sql_conn.commit()

    embed=MessageEmbed(
        content=m.content,
        author=m.author,
        timestamp=m.created_at,
        jump_url=m.jump_url,
        color=bot.neutral_color
    )

    view = discord.ui.View()
    view.add_item(embed.get_jump_button())

    response = await (await bot.client.fetch_channel(DRACBOARD_CHANNEL_ID)).send(
        PING_STR,
        embed=embed,
        view=view
    )

    await response.add_reaction(REACT_EMOJI)

async def check_message(m : discord.Message):

    if m.channel.id in EXEMPT_CHANNELS: return
    
    c = 0
    users = []

    for r in m.reactions:
        if r.is_custom_emoji() or r.emoji not in EMOJIS:
            continue
        async for u in r.users():
            u = u.id
            if u in users: continue
            users.append(u)
            c += 1
            if c >= MINIMUM_REACTION_COUNT: break
        if c >= MINIMUM_REACTION_COUNT: break

    if c >= MINIMUM_REACTION_COUNT:
        already_pinned = sql_conn.execute(
            sql.select(db.dracboard_table)
                .where(db.dracboard_table.c.MESSAGE_ID == m.id)
                .limit(1)
        ).rowcount
        if not already_pinned:
            await dracboard_pin(m)

@bot.client.event
async def on_reaction_add(reaction : discord.Reaction, user : discord.User):
    if user.bot: return
    await check_message(reaction.message)

@bot.client.event
async def on_raw_reaction_add(payload : discord.RawReactionActionEvent):
    if (await bot.client.fetch_user(payload.user_id)).bot: return
    await check_message(
        await (await bot.client.fetch_channel(payload.channel_id)).fetch_message(payload.message_id)
    )
