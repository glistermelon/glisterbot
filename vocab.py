import discord
import bot
import database as db
from database import sql, sql_conn
import json
import random
import events
import asyncio
from sqlalchemy.dialects import postgresql

LANGUAGES = {
    'fr': 'french',
    'es': 'spanish'
}

VERBS = {
    lang : json.loads(open(f'vocab/{lang}/verbs.json', encoding='utf-8').read())
    for lang in LANGUAGES.keys()
}

ACTIVE_CHANNELS = []

@discord.app_commands.choices(language=[
    discord.app_commands.Choice(name=long, value=short + '|' + long)
    for short, long in LANGUAGES.items()
])
@bot.tree.command(name='vocab', description='Practice vocabulary.')
async def test_vocab(ctx : discord.Interaction, language : discord.app_commands.Choice[str]):

    if ctx.channel.id in ACTIVE_CHANNELS:
        await ctx.response.send_message('You can\'t practice two things at once in the same channel!', ephemeral=True)
        return
    ACTIVE_CHANNELS.append(ctx.channel.id)

    reverse = bool(random.randrange(2))

    language = language.value.split('|')
    language_name = language[1]
    language = language[0]

    verbs = { v : 0 for v in VERBS[language].items() }

    for row in sql_conn.execute(
        sql.select(db.vocab_table)
            .where(
                (db.vocab_table.c.LANG == language) &
                (db.vocab_table.c.USER == ctx.user.id) &
                (db.vocab_table.c.REVERSE == reverse)
            )
    ):
        verbs[(row.WORD, row.ENGLISH)] = row.SCORE

    verb_list = []
    need_improvement = 0
    for v, s in verbs.items():
        verb_list.append(v)
        if s <= 0:
            need_improvement += 1
            if need_improvement == 15:
                break
    verbs = { v : verbs[v] for v in verb_list }
    
    verb_odds = { v : 1 / (1 + s) if s > 0 else 1 - s for v, s in verbs.items() }

    choice = random.choices(list(verb_odds.keys()), list(verb_odds.values()), k=1)[0]

    choice_prompt = choice[1 if reverse else 0]
    choice_answer = choice[0 if reverse else 1]

    wait_task = None
    answer_message = None
    async def check(m : discord.Message):
        if m.author != ctx.user: return
        content = m.content.strip().lower()
        given_up = content == 'idk'
        answered = content == choice_answer
        if not (given_up or answered): return
        if answered:
            nonlocal answer_message
            answer_message = m
        events.rm_listener('on_message', check)
        wait_task.cancel()

    embed = discord.Embed(
        color=bot.neutral_color,
        title=choice_prompt,
        description=f'What is the {language_name if reverse else 'english'} translation of this word?\n*You have 10 seconds to answer!*'
    )
    embed.set_thumbnail(url="attachment://flag.png")
    flag = discord.File(f'vocab/{language}/flag.png', filename='flag.png')

    await ctx.response.send_message(embed=embed, file=flag)

    wait_task = asyncio.create_task(asyncio.sleep(10))
    events.add_listener('on_message', check, channel=ctx.channel)
    try:
        await wait_task
    except asyncio.CancelledError:
        pass

    if answer_message:
        await ctx.channel.send(
            embed=discord.Embed(
                color=0x00ff00,
                title='That\'s correct!'
            ),
            reference=answer_message
        )
        embed.color = 0x00ff00
        embed.description = f'Translated correctly!'
    else:
        await ctx.channel.send(
            embed=discord.Embed(
                color=0xff0000,
                title='You didn\'t answer correctly in time!',
                description=f'The correct answer was:  `{choice_answer}`.'
            ),
            reference=await ctx.original_response()
        )
        embed.color = 0xff0000
        embed.description = f'You didn\'t answer correctly in time!'
    await ctx.edit_original_response(embed=embed)

    new_score = verbs[choice] + (1 if answer_message else -1)
    sql_conn.execute(
        postgresql.insert(db.vocab_table)
            .values(
                WORD=choice[0],
                USER=ctx.user.id,
                SCORE=new_score,
                LANG=language,
                REVERSE=reverse,
                ENGLISH=choice[1]
            )
            .on_conflict_do_update(
                constraint=db.vocab_constraint,
                set_=dict(SCORE=new_score)
            )
    )
    sql_conn.commit()

    ACTIVE_CHANNELS.remove(ctx.channel.id)