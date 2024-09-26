import bot
import discord
import database as db
from database import sql, sql_conn
import re

def count_word_in_sentence(sentence : str, word : str):
    sentence = sentence.lower().strip()
    word = word.lower().strip()
    c = 0  # count
    i = -1 # index
    while True:
        i = sentence.find(word, i + 1)
        if i == -1: break
        j = i + len(word)
        if (i == 0 or not sentence[i - 1].isalpha()) and (j == len(sentence) or (not sentence[j].isalpha()) or sentence[j] == 's'):
            c += 1
    return c

@bot.tree.command(name='who-said-it-most', description='See who has said a specific word or phrase the most.')
async def quote_rank(ctx : discord.Interaction, phrase : str):

    await ctx.response.defer()

    messages = sql_conn.execute(sql.select(db.msg_table.c.CONTENT, db.msg_table.c.AUTHOR)).all()
    counts = {}
    for msg in messages:
        c = count_word_in_sentence(msg.CONTENT.lower(), phrase)
        if c == 0: continue
        try:
            counts[msg.AUTHOR] += c
        except:
            counts[msg.AUTHOR] = c
    
    desc = None
    if len(counts) == 0:
        desc = 'Nobody has ever said that, weirdo!'
    else:
        desc = ''
        for user_id, count in sorted(counts.items(), key=lambda x:x[1], reverse=True):
            desc += f'<@{user_id}>: **{bot.commafy(count)}** times\n'
        desc = desc[:-1]

    await ctx.followup.send(
        embed=discord.Embed(
            title=f'Who has said "{phrase}" the most?',
            description=desc,
            color=bot.default_color
        )
    )