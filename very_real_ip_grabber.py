import bot
import discord
import random
from datetime import datetime

# funny

@bot.tree.command(name='grab-ip', description='Very real IP grabber')
async def update_logs(ctx : discord.Interaction, user : discord.User):
    random.seed(user.id)
    random.seed(random.randrange(129079283 * datetime.now().month))
    ip = '.'.join(str(random.randrange(256)) for _ in range(4))
    await ctx.response.send_message(f'<@{user.id}>\'s IP address is {ip}')