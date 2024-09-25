import bot
import database as db
from database import sql, sql_conn
import discord
from sqlalchemy.orm import Session

word_list = set(open('woke.txt').read().strip().split('\n'))

@bot.tree.command(name='woke-detector', description='Own the libs (joke)')
async def detector(ctx : discord.Interaction, target_user : discord.User):

    await ctx.response.defer()

    ratio = None

    with Session(db.engine) as session:

        base_stmt = sql.select(sql.func.count()).select_from(db.msg_table).where(db.msg_table.c.AUTHOR == target_user.id)

        total = session.execute(base_stmt).scalar()
        filters = []
        for word in word_list:
            check = db.msg_table.c.CONTENT.contains(word.replace('(s)', ''))
            word = word.replace('(s)', 's*')
            regex = db.msg_table.c.CONTENT.regexp_match(f'(?:^|\\W){word}(?:$|\\W)', flags='i')
            filters.append(sql.and_(check, regex))
        woke = session.execute(base_stmt.where(sql.or_(*filters))).scalar()
        ratio = woke / total

    result = None
    desc = None
    color = None
    if ratio < 0.001:
        result = 'BASED and REDPILLED'
        color = 0x00ff00
    elif ratio < 0.002:
        result = 'NEUTRAL'
        color = bot.neutral_color
    elif ratio < 0.005:
        result = 'WOKE'
        color = 0xff9900
    else:
        result = 'VERY WOKE'
        color = 0xff0000

    await ctx.followup.send(embed=discord.Embed(
        title=f'{target_user.name} is {result}!',
        color=color,
        description=f'{target_user.name}\'s wokeness score is `{ratio * 100000}`!'
    ))
