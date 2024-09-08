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

react_check_regex = re.compile('^<.*:.+:[0-9]+>$')

@bot.tree.command(name='who-reacted-most', description='See who has reacted with a specific emoji the most.')
async def react_rank(ctx : discord.Interaction, phrase : str):

    print(phrase)

    emoji_id = None

    if react_check_regex.match(phrase):
        emoji_id = int(phrase[phrase.index(':', phrase.index(':') + 1) + 1 : -1])
    elif len(phrase) != 1:
        await ctx.response.send_message('The provided emoji is invalid!', ephemeral=True)
        return

    await ctx.response.defer()

    stmt = sql.select(db.reactions_table)
    if emoji_id: stmt = stmt.where(db.reactions_table.c.EMOJI_ID == emoji_id)
    else: stmt = stmt.where(db.reactions_table.c.EMOJI_NAME == phrase)
    data = sql_conn.execute(stmt)
    counts = {}
    for row in data:
        try:
            counts[row.USER] += 1
        except:
            counts[row.USER] = 1
    
    desc = None
    if len(counts) == 0:
        desc = 'Nobody has ever reacted with that!'
    else:
        desc = ''
        for user_id, count in sorted(counts.items(), key=lambda x:x[1], reverse=True):
            desc += f'<@{user_id}>: **{bot.commafy(count)}** times\n'
        desc = desc[:-1]

    embed=discord.Embed(
        title=f'Who has reacted with {phrase} the most?',
        description=desc,
        color=bot.default_color
    )

    bot.client.http.get_custom_emoji()

    await ctx.followup.send(embed=embed)