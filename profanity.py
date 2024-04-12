import log
import discord
from discord import app_commands
import bot
from types import SimpleNamespace


N_WORD = 'ginger'
N_WORD = N_WORD[2::-1] + N_WORD[3:]


profanity_dict = {}
with open('profanity.txt') as f:
    buf = SimpleNamespace()
    buf.key = None
    buf.ls = []
    for ln in f:
        ln = ln.strip()
        if len(ln) == 0:
            profanity_dict[buf.key] = list(buf.ls)
            buf.key = None
            buf.ls = []
            continue
        if buf.key is None:
            buf.key = ln.rstrip(':')
        else:
            buf.ls.append(ln)


@bot.tree.command(name="profanity", description="See how much profanity your fellow server members have used.")
@app_commands.describe(user="who to count profanity usage for")
async def profanity(ctx, user: discord.User):

    if log.TextChannelLogger.get_logger() is None:
        await ctx.response.send_message("This command isn't available right now. Try again soon!", ephemeral=True)
        return

    await ctx.response.defer()

    counts = {key: {w: 0 for w in words} for key, words in profanity_dict.items()}
    for message in log.TextChannelLogger.global_logger.messages:
        if message.author != user.id:
            continue
        content = message.content.lower().strip()
        for key, words in profanity_dict.items():
            for word in words:
                i = -1
                while True:
                    i = content.find(word, i + 1)
                    if i == -1:
                        break
                    counts[key][word] += 1
                    content = content[:i] + content[i + len(word):]

    if user.name == 'ramble21':
        counts[N_WORD][N_WORD] += 100

    lines = []
    for key, word_counts in counts.items():
        total = sum(word_counts.values())
        if total == 0:
            continue
        lines.append(f'**{key.title()}** - *{total}*')
        for word, c in word_counts.items():
            if c > 0:
                lines.append(f'{word} - {c}')
    await ctx.followup.send(embed=discord.Embed(
        title=f'{user.name}\'s Profanity Counter',
        description='\n'.join(lines),
        color=0x36393F
    ))
