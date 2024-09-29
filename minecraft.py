import discord
import bot
import database as db
from database import sql, sql_conn
from sqlalchemy.dialects import postgresql
from page_view import PaginatedEmbed
from types import SimpleNamespace
import aiohttp
import asyncio
from sqlalchemy.orm import Session

minecraft_group = discord.app_commands.Group(name='minecraft', description='Minecraft related commands!')
bot.tree.add_command(minecraft_group)

@minecraft_group.command(name='link-account', description='Link your minecraft account to glisterbot.')
async def register_account_uuid(ctx : discord.Interaction, minecraft_username : str):

    uuid = None
    try:
        data = None
        async with aiohttp.ClientSession() as session:
            data = await session.get(f'https://api.mojang.com/users/profiles/minecraft/{minecraft_username}')
        data = await data.json()
        uuid = data['id']
        minecraft_username = data['name']
    except:
        await ctx.response.send_message('Something went wrong. Try again later.', ephemeral=True)
        return

    try:

        with Session(db.engine) as session:

            values = dict(
                MINECRAFT_UUID=uuid,
                DISCORD_ID=ctx.user.id,
                SERVER=ctx.guild.id
            )
            stmt = postgresql.insert(db.minecraft_users_table).values(**values)
            session.execute(
                stmt.on_conflict_do_update(
                        constraint=db.minecraft_users_constraint,
                        set_={ i[0] : getattr(stmt.excluded, i[0]) for i in values.items() }
                    )
            )

            values = dict(
                UUID=uuid,
                NAME=minecraft_username
            )
            stmt = postgresql.insert(db.minecraft_names_table).values(**values)
            session.execute(
                stmt.on_conflict_do_update(
                        constraint=db.minecraft_names_constraint,
                        set_={ i[0] : getattr(stmt.excluded, i[0]) for i in values.items() }
                    )
            )

            session.commit()

    except Exception as e:
        print('fuckkkkkkkkkk')
        print(e)

    await ctx.response.send_message(
        embed=discord.Embed(
            title='Minecraft account successfully linked',
            description=f'Username: `{minecraft_username}`\nUUID: `{uuid}`',
            color=0x00ff00
        )
    )

@minecraft_group.command(name='players', description='View all linked accounts in this server.')
async def view_players(ctx : discord.Interaction):

    class ViewPlayers(PaginatedEmbed):

        per_page = 10

        def __init__(self, ctx : discord.Interaction, players : list[SimpleNamespace]):
            super().__init__(ctx)
            self.players = players

        def get_page(self, number):
            
            if number < 0: return None

            start_index = ViewPlayers.per_page * number
            end_index = start_index + ViewPlayers.per_page

            if start_index >= len(self.players): return None
            if end_index > len(self.players): end_index = len(self.players)

            desc = []
            for i in range(start_index, end_index):
                player = self.players[i]
                desc.append(f'<@{player.discord_id}> - `{player.minecraft_name}`')
            
            return discord.Embed(
                title='Minecraft Players in this Server',
                description='\n'.join(desc),
                color=bot.default_color
            )
    
    players = []
    for r in sql_conn.execute(
        sql.select(db.minecraft_users_table).where(db.minecraft_users_table.c.SERVER == ctx.guild.id)
    ):
        player = SimpleNamespace()
        player.discord_id = r.DISCORD_ID
        player.minecraft_name = sql_conn.execute(
            sql.select(db.minecraft_names_table).where(db.minecraft_names_table.c.UUID == r.MINECRAFT_UUID).limit(1)
        ).first().NAME
        players.append(player)
    
    if len(players) == 0:
        await ctx.response.send_message('There are no players currently linked in this server', ephemeral=True)
        return

    await ViewPlayers(ctx, players).send()

@bot.tree.command(name='update-minecraft-names', description='[HIGH ADMIN ONLY] Updates the UUID-username database.')
async def update_names(ctx : discord.Interaction):
    
    if ctx.user.id != 674819147963564054:
        await ctx.response.send_message('Only the bot owner can use this command!', ephemeral=True)
        return
    
    await ctx.response.defer()

    update_count = 0
    for row in sql_conn.execute(sql.select(db.minecraft_names_table.c.UUID)):
        async with aiohttp.ClientSession() as session:
            response = None
            while True:
                await asyncio.sleep(1)
                response = await session.get(f'https://sessionserver.mojang.com/session/minecraft/profile/{row.UUID}')
                if response.status != 429: break
                asyncio.sleep(int(response.headers['Retry-After']))
            new_name = None
            try:
                new_name = response['name']
            except:
                continue
            if new_name != row.NAME:
                update_count += 1
                sql_conn.execute(
                    sql.update(db.minecraft_names_table)
                        .where(db.minecraft_names_table.c.UUID == row.UUID)
                        .values(NAME=new_name)
                )
                sql_conn.commit()
    
    await ctx.followup.send(f'{update_count} rows successfully updated.')