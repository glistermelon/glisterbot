from discord import app_commands
import discord
import bot
import database as db
from database import sql, sql_conn
from sqlalchemy.orm import Session
import sqlalchemy.dialects.postgresql as postgresql
from inspect import signature
from bisect import bisect
import re

rankings_group = app_commands.Group(name="rankings",description="See rankings of different categories from your server members!")

class Category:

    categories = {}

    def __init__(self, name : str, display_name : str, description : str, cmd_desc):

        row = sql_conn.execute(sql.select(db.rankings_cat_table).where(db.rankings_cat_table.c.NAME == name).limit(1)).first()

        if row is None:
            row = sql_conn.execute(
                sql.insert(db.rankings_cat_table).values(
                    NAME=name, DISPLAY_NAME=display_name
                )
            )
            sql_conn.commit()
            self.id = row.inserted_primary_key[0]
        else:
            self.id = row.ID
            if row.DISPLAY_NAME != display_name:
                sql_conn.execute(
                    sql.update(db.rankings_cat_table).values(
                        DISPLAY_NAME=display_name
                    )
                )
                sql_conn.commit()

        self.name = name
        self.display_name = display_name
        self.desc = description
        self.cmd_desc = cmd_desc

        Category.categories[self.name] = self

class Item:
    def __init__(self, name, score):
        self.name = name
        self.score = score

class View(discord.ui.View):

    timeout = 300
    page_length = 10

    async def on_timeout(self):
        self.clear_items()
        await self.ctx.edit_original_response(
            embed=discord.Embed(
                description='*Session expired after 5 minutes of inactivity.*',
                color=bot.neutral_color
            ),
            view=self
        )

    def __init__(self, user : discord.User, data : list[Item], title, ctx):
        super().__init__()
        self.page = 0
        self.user = user
        self.data = data
        self.title = title
        self.ctx = ctx
    
    def get_page(self, num):

        desc = ''
        items = self.data[num * View.page_length : (num + 1) * View.page_length]
        if len(items) == 0: return None
        for i in range(len(items)):
            item = items[i]
            stars = '<:gb_star:1093401758849572914>' * (int(round(item.score) / 2))
            stars += '<:gb_halfstar:1093401757280915558>' * (int(round(item.score) % 2))
            desc += f'**{num * View.page_length + i + 1}.** **{item.name}** - {round(item.score, 2)}/10  {stars}\n'
        desc = desc[:-1]

        return discord.Embed(
            title=self.title,
            description=desc,
            color=bot.default_color
        )

    @discord.ui.button(label=' < ',style=discord.ButtonStyle.blurple)
    async def left(self,ctx:discord.Interaction,b:discord.ui.Button):
        if ctx.user.id != self.user.id:
            await ctx.response.send_message('This is not your window!', ephemeral=True)
            return
        if self.page == 0:
            await ctx.response.send_message('There are no previous pages!', ephemeral=True)
        else:
            self.page -= 1
            await self.ctx.edit_original_response(embed=self.get_page(self.page))
            await ctx.response.defer()
            

    @discord.ui.button(label=' > ',style=discord.ButtonStyle.blurple)
    async def right(self,ctx:discord.Interaction,b:discord.ui.Button):
        if ctx.user.id != self.user.id:
            await ctx.response.send_message('This is not your window!', ephemeral=True)
            return
        embed = self.get_page(self.page + 1)
        if embed is None:
            await ctx.response.send_message('There are no pages after this one!', ephemeral=True)
        else:
            self.page += 1
            await self.ctx.edit_original_response(embed=embed)
            await ctx.response.defer()

def get_rate_command(category : Category, description : str, length_limit : int = None):

    async def rate(ctx : discord.Interaction, name : str, rating : int):

        item_name = name.strip()

        if length_limit and len(item_name) > length_limit:
            await ctx.response.send_message(f'Nice try. There is a {length_limit} character limit!')
            return

        if rating < 0 or rating > 10:
            await ctx.response.send_message('Rating must be between 0 and 10!', ephemeral=True)
            return
        
        blacklist = [r.REGEX for r in sql_conn.execute(sql.select(db.rankings_blacklist_table.c.REGEX).where(db.rankings_blacklist_table.c.SERVER == ctx.guild.id))]
        for regex in blacklist:
            if re.search(regex, item_name, re.IGNORECASE) is not None:
                await ctx.response.send_message('That phrase is banned!', ephemeral=True)
                return

        display_name = item_name
        item_name = item_name.lower()

        waiting_on = None
        item_added = None
        score = None
        score_id = None
        with Session(db.engine) as session:

            item = session.execute(sql.select(db.rankings_item_table).where(db.rankings_item_table.c.NAME == item_name)).first()

            if item is None:

                waiting_on = 2
                item_row = session.execute(sql.insert(db.rankings_item_table).values(
                    CATEGORY_ID=category.id,
                    NAME=item_name,
                    DISPLAY_NAME=display_name
                ))
                score_row = session.execute(sql.insert(db.rankings_score_table).values(
                    ITEM_ID=item_row.inserted_primary_key[0],
                    SERVER=ctx.guild.id,
                    COUNT=1,
                    SCORE=rating
                ))

                score_id = score_row.inserted_primary_key[0]

            else:

                display_name = item.DISPLAY_NAME

                score_row = session.execute(sql.select(db.rankings_score_table).where(
                    (db.rankings_score_table.c.ITEM_ID == item.ID) &
                    (db.rankings_score_table.c.SERVER == ctx.guild.id)
                ).limit(1).with_for_update()).first()
                
                score_id = None
                if score_row is None:
                    score_row = session.execute(sql.insert(db.rankings_score_table).values(
                        ITEM_ID=item.ID,
                        SERVER=ctx.guild.id,
                        COUNT=1,
                        SCORE=rating
                    ))
                    score_id = score_row.inserted_primary_key[0]
                else:
                    score_id = score_row.ID

                # TODO: scores is always empty if score_row was None
                scores = [
                    row.VALUE for row in
                    session.execute(
                        sql.select(db.rankings_table).where(
                            (db.rankings_table.c.SCORE_ID == score_id) &
                            (db.rankings_table.c.USER != ctx.user.id)
                        )
                    )
                ]
                scores.append(rating)
                score = sum(scores) / len(scores)

                num_scores = len(scores)
                if num_scores < 3: waiting_on = 3 - num_scores
                elif num_scores == 3: item_added = True

                session.execute(sql.update(db.rankings_score_table).where(
                    db.rankings_score_table.c.ID == score_id
                ).values(
                    COUNT=len(scores),
                    SCORE=score
                ))

            session.execute(postgresql.insert(db.rankings_table).values(
                USER=ctx.user.id,
                SCORE_ID=score_id,
                VALUE=rating
            ).on_conflict_do_update(constraint=db.rankings_constraint, set_=dict(VALUE=rating)))
            session.commit()
            
        desc = None
        if waiting_on is not None:
            desc = f'Only {waiting_on} more ranking(s) required until **{display_name}** is added to the ranking list!'
        elif item_added:
            desc = f'**{display_name}** has been added to the ranking list with a score of **{score}**!'
        else:
            desc = f'**{display_name}** now has a score of **{score}**!'

        await ctx.response.send_message(embed=discord.Embed(
            title=f'You have successfully ranked **{display_name}**: {rating}/10',
            description=desc,
            color=0xff9900 if waiting_on else 0x00ff00
        ))

    category.cmd_group.command(name='rate', description=description)(rate)

def get_view_command(category : Category, description : str, pending : bool):

    async def view(ctx : discord.Interaction):

        await ctx.response.send_message('Getting rankings...')

        ranks = []
        names = {}
        with Session(db.engine) as session:
            items = session.execute(sql.select(db.rankings_item_table).where(
                db.rankings_item_table.c.CATEGORY_ID == category.id
            )).all()
            for item in items:
                row = session.execute(sql.select(db.rankings_score_table).where(
                    (db.rankings_score_table.c.ITEM_ID == item.ID) &
                    (db.rankings_score_table.c.SERVER == ctx.guild.id)
                ).limit(1)).first()
                if row is None or (pending and row.COUNT >= 3) or (row.COUNT < 3 and not pending): continue
                ranks.append(row)
                names[item.ID] = item.DISPLAY_NAME
        
        if len(ranks) == 0:
            await ctx.edit_original_response(
                content = 'Nobody in your server has ranked anything yet! Check out `/rankings [category] rate`.'
            )
            return
        
        ranks = [Item(names[row.ITEM_ID], row.SCORE) for row in sorted(ranks, reverse=True, key=lambda r : (r.COUNT if pending else r.SCORE))]
        title = category.display_name
        if pending: title += ' Pending'
        title += ' Rankings'
        view = View(ctx.user, ranks, title, ctx)
        await ctx.edit_original_response(
            content='',
            embed=view.get_page(0),
            view=view
        )
    
    category.cmd_group.command(name='pending' if pending else 'view', description=description)(view)

def get_details_command(category : Category, description : str):

    async def details(ctx : discord.Interaction, name : str):

        item_name = name.strip()

        overall_score = None
        ratings = {}
        all_scores = []

        with Session(db.engine) as session:

            item_row = session.execute(
                sql.select(db.rankings_item_table).where(db.rankings_item_table.c.NAME == item_name.lower()).limit(1)
            ).first()

            if item_row is None:
                await ctx.response.send_message(f'"{item_name}" is not in the rankings list!')
                return

            item_name = item_row.DISPLAY_NAME
            
            score_row = session.execute(
                sql.select(db.rankings_score_table).where(
                    (db.rankings_score_table.c.ITEM_ID == item_row.ID) &
                    (db.rankings_score_table.c.SERVER == ctx.guild.id)
                ).limit(1)
            ).first()
            
            overall_score = score_row.SCORE

            for row in session.execute(
                sql.select(db.rankings_table).where(db.rankings_table.c.SCORE_ID == score_row.ID)
            ):
                ratings[row.USER] = row.VALUE
            
            if len(ratings) >= 3:
                item_ids = [r.ID for r in session.execute(
                    sql.select(db.rankings_item_table.c.ID).where(db.rankings_item_table.c.ID != item_row.ID)
                )]
                for item_id in item_ids:
                    print(item_id)
                    row = session.execute(
                        sql.select(db.rankings_score_table.c.SCORE, db.rankings_score_table.c.COUNT).where(
                            (db.rankings_score_table.c.ITEM_ID == item_id) &
                            (db.rankings_score_table.c.SERVER == ctx.guild.id)
                        ).limit(1)
                    ).first()
                    if row.COUNT >= 3: all_scores.append(row.SCORE)
        
        stars = "<:gb_star:1093401758849572914>" * int(overall_score / 2)
        stars += "<:gb_halfstar:1093401757280915558>" * int(overall_score % 2)
        desc = f"**Overall Ranking: {overall_score}/10** {stars}\n"
        for user, rating in ratings.items():
            stars = "<:gb_star:1093401758849572914>" * (rating // 2)
            stars += "<:gb_halfstar:1093401757280915558>" * (rating % 2)
            desc += f"<@{user}> - {rating}/10 {stars}\n"
        desc = desc[:-1]

        title = None
        if len(ratings) < 3: title = f'{item_name} Ranking Details'
        else:
            all_scores.sort()
            title = f'#{len(all_scores) - bisect(all_scores, overall_score) + 1} - {item_name}'
        await ctx.response.send_message(embed=discord.Embed(title=title, description=desc, color=bot.default_color))

    category.cmd_group.command(name='details', description=description)(details)

def remove_item(session : Session, server_id : int, name_or_id : str | int) -> str:

    stmt = sql.select(db.rankings_item_table)
    if type(name_or_id) is str: stmt = stmt.where(db.rankings_item_table.c.NAME == name_or_id)
    else: stmt = stmt.where(db.rankings_item_table.c.ID == name_or_id)
    item_row = session.execute(stmt.limit(1)).first()

    if item_row is None: return f'"{name_or_id}" does not exist.'

    stmt = sql.select(db.rankings_score_table).where(
            (db.rankings_score_table.c.ITEM_ID == item_row.ID) &
            (db.rankings_score_table.c.SERVER == server_id)
    )
    
    score_row = session.execute(stmt.limit(1)).first()

    if score_row is None: return f'"{name_or_id}" does not exist for the provided subcategory in your server.'

    score_id = score_row.ID

    session.execute(
        sql.delete(db.rankings_kick_table).where(db.rankings_kick_table.c.SCORE_ID == score_id)
    )
    session.execute(
        sql.delete(db.rankings_table).where(db.rankings_table.c.SCORE_ID == score_id)
    )
    session.execute(
        sql.delete(db.rankings_score_table).where(db.rankings_score_table.c.ID == score_id)
    )

    item_id = item_row.ID

    if session.execute(sql.select(db.rankings_score_table).where(db.rankings_score_table.c.ITEM_ID == item_id).limit(1)).first() is None:
        session.execute(sql.delete(db.rankings_item_table).where(db.rankings_item_table.c.ID == item_id))

def get_remove_command(category : Category, description : str):

    async def remove(ctx : discord.Interaction, name : str, reason : str):

        if not ctx.user.guild_permissions.administrator:
            await ctx.response.send_message('You must be an admin to use this command!', ephemeral=True)
            return

        name = name.strip().lower()

        with Session(db.engine) as session:
            err = remove_item(session, ctx.guild.id, name)
            if err:
                await ctx.response.send_message(err, ephemeral=True)
                return
            session.commit()

        await ctx.response.send_message(embed=discord.Embed(
            title=f'"{name}" has been removed from {category.display_name}',
            description=f'**Reason:** {reason}',
            color=0xff0000
        ))

    category.cmd_group.command(name='remove', description=description)(remove)

def get_rename_command(category : Category, description : str):

    async def rename(ctx : discord.Interaction, current_name : str, new_name : str):

        if not ctx.user.guild_permissions.administrator:
            await ctx.response.send_message('You must be an admin to use this command!', ephemeral=True)
            return

        name = current_name.strip().lower()
        new_name = new_name.strip()

        with Session(db.engine) as session:

            stmt = sql.update(db.rankings_item_table).where(db.rankings_item_table.c.NAME == name).values(DISPLAY_NAME=new_name)
            new_name_lower = new_name.lower()
            if new_name_lower != current_name:
                existing = session.execute(
                    sql.select(db.rankings_item_table).where(db.rankings_item_table.c.NAME == new_name_lower)
                ).first()
                if existing is not None:
                    await ctx.response.send_message('Another entry already has that name!', ephemeral=True)
                    return
                stmt = stmt.values(NAME=new_name_lower)
            updated = session.execute(stmt).rowcount

            if updated == 0:
                await ctx.response.send_message(f'"{name}" does not exist.', ephemeral=True)
                return

            session.commit()

        await ctx.response.send_message(embed=discord.Embed(
            title=f'"{name}" has been renamed to "{new_name}"',
            color=0x00ff00
        ))

    category.cmd_group.command(name='rename', description=description)(rename)

def get_vote_kick_command(category : Category, description : str):

    async def vote_kick(ctx : discord.Interaction, name : str):

        name = name.strip().lower()

        do_remove = False
        rem_votes = None
        display_name = None

        with Session(db.engine) as session:

            item_row = session.execute(
                sql.select(db.rankings_item_table).where(db.rankings_item_table.c.NAME == name).limit(1)
            ).first()

            if item_row is None:
                await ctx.response.send_message(f'"{name}" does not exist.', ephemeral=True)
                return
            
            display_name = item_row.DISPLAY_NAME
            
            score_id = session.execute(
                sql.select(db.rankings_score_table.c.ID).where(
                    (db.rankings_score_table.c.ITEM_ID == item_row.ID) &
                    (db.rankings_score_table.c.SERVER == ctx.guild.id)
                )
            ).first().ID

            votes = session.execute(
                sql.select(db.rankings_kick_table).where(db.rankings_kick_table.c.SCORE_ID == score_id)
            ).all()
            extra_vote = True
            for row in votes:
                if row.SCORE_ID == score_id and row.USER == ctx.user.id:
                    extra_vote = False
                    break
            votes = len(votes)
            if extra_vote: votes += 1

            if votes >= 3:
                do_remove = True
                remove_item(session, ctx.guild.id, name)
            else:
                rem_votes = 3 - votes
                session.execute(
                    sql.insert(db.rankings_kick_table).values(
                        USER=ctx.user.id, SCORE_ID=score_id
                    )
                )

            session.commit()

        title = None
        desc = None
        color = None
        if do_remove:
            title = f'"{display_name}" was kicked from the {category.display_name} rankings!'
            color = 0xff0000
        else:
            title = f'You voted to kick "{display_name}" from the {category.display_name} rankings!'
            desc = f'If "{display_name}" receives {rem_votes} more votes, it will be kicked.'
            color = 0xff9900
        
        embed = discord.Embed(title=title, description=desc, color=color)
        embed.set_footer(text='Abusing vote kicks will get you banned.')
        await ctx.response.send_message(embed=embed)

    category.cmd_group.command(name='vote-kick', description=description)(vote_kick)

def get_ban_regex_command(category : Category, description : str, ban : bool):

    async def ban_regex(ctx : discord.Interaction, regex : str):

        if not ctx.user.guild_permissions.administrator:
            await ctx.response.send_message('You must be an admin to use this command!', ephemeral=True)
            return

        regex = regex.strip().lower()

        if ban:
            sql_conn.execute(
                postgresql.insert(db.rankings_blacklist_table).values(REGEX=regex, SERVER=ctx.guild.id).on_conflict_do_nothing()
            )
        else:
            removed = sql_conn.execute(sql.delete(db.rankings_blacklist_table).where(db.rankings_blacklist_table.c.REGEX == regex)).rowcount
            if removed == 0:
                await ctx.response.send_message('There is no ban record matching that regex!', ephemeral=True)
                return

        await ctx.response.send_message(embed=discord.Embed(
            title=f'`{regex}` has been {'' if ban else 'un'}banned for {category.display_name}',
            color=0xff0000
        ))

    

def get_list_banned_regex_command(category : Category, description : str):

    async def get_banned_regexes(ctx : discord.Interaction):

        regexes = [r.REGEX for r in sql_conn.execute(
            sql.select(db.rankings_blacklist_table.c.REGEX).where(db.rankings_blacklist_table.c.SERVER == ctx.guild.id)
        )]

        if len(regexes) == 0:
            await ctx.response.send_message(embed=discord.Embed(title='There are no banned regexes in this server!', color=0xff0000))
        else:
            await ctx.response.send_message(embed=discord.Embed(
                title='Banned Regexes',
                description='```\n' + '\n'.join([f'{i + 1}: {regexes[i]}' for i in range(len(regexes))]) + '\n```'
            ))
    
    category.cmd_group.command(name='banned-regexes', description=description)(get_banned_regexes)

gd_category = Category(
    'geometrydash', 'Geometry Dash Levels',
    'Rankings for Geometry Dash levels!',
    {
        'rate': 'Rate GD levels out of 10 for the server rankings list.',
        'view': 'See how server members have ranked popular levels.',
        'pending': 'See rankings that have yet to meet the 3 rate requirement.',
        'details': 'See how server members ranked a particular level.'
    }
)

categories = [
    gd_category
]

for cat in categories:
    group = app_commands.Group(name=cat.name, description=cat.desc, parent=rankings_group)
    cat.cmd_group = group
    get_rate_command(cat, cat.cmd_desc['rate'], 20)
    get_view_command(cat, cat.cmd_desc['view'], False)
    get_view_command(cat, cat.cmd_desc['pending'], True)
    get_details_command(cat, cat.cmd_desc['details'])
    get_remove_command(cat, '[ADMIN ONLY] Remove rated items from the rankings.')
    get_rename_command(cat, '[ADMIN ONLY] Rename levels.')
    get_vote_kick_command(cat, 'Vote to kick levels from the rankings.')
    get_ban_regex_command(cat, '[ADMIN ONLY] Ban a regex server-wide.', True)
    get_ban_regex_command(cat, '[ADMIN ONLY] Unban a regex server-wide.', False)
    get_list_banned_regex_command(cat, 'See what regexes are banned in this server.')
    

bot.tree.add_command(rankings_group)

# TODO
# subcategories should really be tied to the categories
# so like add a subcategories attribute to the Category class
# SQL should probably reflect that ownership too