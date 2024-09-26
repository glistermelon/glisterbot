import matplotlib.pyplot as plt
import database
from database import sql, sql_conn
from datetime import datetime, timedelta
import pandas as pds
import numpy
from types import SimpleNamespace
import bot
import discord
from io import BytesIO
import math

def message_chart(ctx : discord.Interaction, target_user : discord.User | None, time_window : discord.app_commands.Choice[str], sql_filter = None):

    time_window = time_window.value

    weekly = time_window == 'week'
    if weekly: time_window = 'day'

    stats = {}

    stmt = sql.select(database.msg_table.c.AUTHOR, database.msg_table.c.TIMESTAMP)
    if target_user is not None: stmt = stmt.where(database.msg_table.c.AUTHOR == target_user.id)
    if sql_filter is not None: stmt = stmt.where(sql_filter)
    stmt = stmt.order_by(database.msg_table.c.TIMESTAMP.asc())

    for row in sql_conn.execute(stmt):

        date = datetime.fromtimestamp(int(row.TIMESTAMP))

        def increment(t):
            try:
                stats[t] += 1
            except:
                stats[t] = 1

        if time_window == 'year':
            increment(datetime(year=date.year, month=1, day=1))
        elif time_window == 'month':
            increment(datetime(year=date.year, month=date.month, day=1))
        else:
            increment(datetime(year=date.year, month=date.month, day=date.day))

    months =  ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

    stats = { i[0] : i[1] for i in sorted(stats.items(), key=lambda i:i[0]) }

    data = []

    date = list(stats.keys())[0]
    end_date = datetime.now()
    i = 0
    label_indices = []

    if weekly: # account for first day being skipped
        second_day = date + timedelta(1)
        if second_day in stats:
            stats[second_day] += stats[date]
        else:
            stats[second_day] = stats[date]
        del stats[date]

    while date <= end_date:

        label = ''
        if (time_window == 'year' or (date.month in (1, 4, 7, 10) and (time_window == 'month' or date.day == 1))) \
            or (weekly and date.month in (1, 4, 7, 10) and date.day <= 7):
            label = str(date.year)
            if time_window != 'year':
                label = months[date.month - 1] + ' ' + label
            label_indices.append(i)
        else:
            label = '-'.join(str(n) for n in (date.year, date.month, date.day))
        
        i += 1

        if date in stats:
            data.append((label, stats[date]))
        else:
            data.append((label, 0))

        if time_window == 'year':
            date = datetime(year=date.year + 1, month=1, day=1)
        elif time_window == 'month':
            year = date.year
            month = date.month + 1
            if month == 13:
                year += 1
                month = 1
            date = datetime(year=year, month=month, day=1)
        elif weekly:
            date += timedelta(1)
            next_date = date + timedelta(6)
            if next_date not in stats: stats[next_date] = 0
            while date < next_date:
                if date in stats:
                    stats[next_date] += stats[date]
                    del stats[date]
                date += timedelta(1)
        else:
            date += timedelta(1)

    dataframe = pds.DataFrame(data, columns=['Date', 'Count'])

    dark_color = (0.15, 0.15, 0.15)
    light_color = (0.2, 0.2, 0.2)
    white_color = (1.0, 1.0, 1.0)

    plt.figure(facecolor=dark_color)

    plt.plot(dataframe['Date'], dataframe['Count'])
    plt.ylabel('Messages')

    axes = plt.gca()

    i = 0
    for label in axes.xaxis.get_ticklabels():
        if i not in label_indices:
            label.set_visible(False)
        i += 1

    if time_window == 'day':
        axes.tick_params(bottom=False)

    plt.xticks(rotation=90)

    axes.set_facecolor(light_color)
    axes.tick_params(colors=white_color)
    axes.yaxis.label.set_color(white_color)

    axes.spines['top'].set_color(dark_color)
    axes.spines['right'].set_color(dark_color)
    axes.spines['bottom'].set_color(white_color)
    axes.spines['left'].set_color(white_color)

    axes.set_axisbelow(True)
    axes.yaxis.grid(color=(0.25, 0.25, 0.25), linestyle='dashed')

    plt.tight_layout()

    image = BytesIO()
    plt.savefig(image, format='png')
    image.seek(0)
    return image

choices = discord.app_commands.choices(time_window=[
    discord.app_commands.Choice(name='daily', value='day'),
    discord.app_commands.Choice(name='weekly', value='week'),
    discord.app_commands.Choice(name='monthly', value='month'),
    discord.app_commands.Choice(name='yearly', value='year')
])

@bot.tree.command(name='message-chart', description='Visualize someone\'s message frequency over time.')
@choices
async def general_message_chart(ctx : discord.Interaction, target_user : discord.User, time_window : discord.app_commands.Choice[str]):
    image = message_chart(ctx, target_user, time_window)
    image_file = discord.File(image, filename='message_chart.png')
    embed = discord.Embed(title=f'{target_user.name}\'s Message Frequency')
    embed.set_image(url='attachment://message_chart.png')
    await ctx.response.send_message(embed=embed, file=image_file)

@bot.tree.command(name='word-chart', description='Visualize the usage frequency of a specific phrase over time.')
@choices
async def general_message_chart(ctx : discord.Interaction, phrase : str, time_window : discord.app_commands.Choice[str]):
    if len(phrase) > 20:
        await ctx.response.send_message('Length of phrase cannot exceed 20 characters.', ephemeral=True)
        return
    image = message_chart(
        ctx, None, time_window,
        sql.or_(
            database.msg_table.c.CONTENT.contains(phrase),
            database.msg_table.c.CONTENT.regexp_match(f'(?:^|\\W){phrase}(?:$|\\W)', flags='i')
        )
    )
    image_file = discord.File(image, filename='message_chart.png')
    embed = discord.Embed(title=f'"{phrase}" Usage Frequency')
    embed.set_image(url='attachment://message_chart.png')
    await ctx.response.send_message(embed=embed, file=image_file)