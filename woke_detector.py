import bot
import database as db
from database import sql, sql_conn
import discord

word_list = set(open('woke.txt').read().strip().split('\n'))

@bot.tree.command(name='detector', description='lmao')
async def detector(ctx : discord.Interaction, target_user : discord.User):
    
    ratio = None

    with sql.Session(db.engine) as session:

        base_stmt = sql.select(sql.func.count()).select_from(db.msg_table).where()

        total = session.execute(base_stmt).scalar()
        filters = []
        for word in word_list:
            word = word.replace('(s)', 's*')
            filters.append(db.msg_table.c.CONTENT.regexp_match(f'(?:^|\W){word}(?:$|\W)'), flags='i')
        woke = session.exceute(sql.select(sql.func.count()).select_from(db.msg_table).where(sql.or_(*filters)))
        ratio = woke / total
    
    await ctx.response.send_message(str(ratio))