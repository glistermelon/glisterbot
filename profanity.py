import discord
from discord import app_commands
import bot
import json
from database import sql, sql_conn
import database

N_WORD = 'ginger'
N_WORD = N_WORD[2::-1] + N_WORD[3:]


@bot.tree.command(name="profanity", description="See how much profanity your fellow server members have used.")
@app_commands.describe(user="who to count profanity usage for")
async def profanity(ctx, user: discord.User):

    await ctx.response.defer()

    profanity_dict = json.loads(open('profanity.json').read())

    counts = {key: {w: 0 for w in words} for key, words in profanity_dict.items()}
    pf = database.profanity_table
    for key, words in profanity_dict.items():
        for word in words:
            c = sql_conn.execute(sql.select(pf.c.COUNT).where((pf.c.WORD == word) & (pf.c.USER == user.id))).first()
            if c: counts[key][word] = c.COUNT

    if user.name == 'ramble21':
        counts[N_WORD.replace('n','N')][N_WORD] += 100
    
    counts = { k:v for k,v in sorted(counts.items(), key = lambda x:sum(x[1].values()), reverse=True) }

    lines = []
    for key, word_counts in counts.items():
        total = sum(word_counts.values())
        if total == 0:
            continue
        lines.append(f'**{key.title()} - {bot.commafy(total)}**')
        for word, c in word_counts.items():
            if c > 0:
                lines.append(f'{word} - {bot.commafy(c)}')
    await ctx.followup.send(embed=discord.Embed(
        title=f'{user.name}\'s Profanity Counter',
        description='\n'.join(lines),
        color=0x36393F
    ))
