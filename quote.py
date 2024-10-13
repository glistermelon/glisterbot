import database as db
from datetime import datetime
from database import sql, sql_conn
from sqlalchemy.orm import Session
from sqlalchemy.dialects import postgresql
import discord
import bot

quote_group = discord.app_commands.Group(name='quote', description='Weird server-dependent quote stuff!')
bot.tree.add_command(quote_group)

def vote_quote(quote_id : int, user_id : int, upvote : bool):

    new_net_score = None

    with Session(db.engine) as session:

        upvoted = session.execute(
            sql.select(db.quote_score_table.c.UPVOTED)
                .where(
                    (db.quote_score_table.c.QUOTE_ID == quote_id) &
                    (db.quote_score_table.c.USER_ID == user_id)
                )
                .limit(1)
        ).first()
        if upvoted is not None: upvoted = upvoted.UPVOTED

        currently_neutral = upvoted is None
        undo_current = False if currently_neutral else (upvote and upvoted) or ((not upvote) and (not upvoted))

        if currently_neutral:
            session.execute(
                sql.insert(db.quote_score_table).values(
                    QUOTE_ID=quote_id,
                    USER_ID=user_id,
                    UPVOTED=upvote
                )
            )
        elif undo_current:
            session.execute(
                sql.delete(db.quote_score_table)
                    .where(
                        (db.quote_score_table.c.QUOTE_ID == quote_id) &
                        (db.quote_score_table.c.USER_ID == user_id)
                    )
            )
        else:
            session.execute(
                sql.update(db.quote_score_table)
                    .where(
                        (db.quote_score_table.c.QUOTE_ID == quote_id) &
                        (db.quote_score_table.c.USER_ID == user_id)
                    )
                    .values(UPVOTED=upvote)
            )

        stmt = sql.select(sql.func.count()) \
                    .select_from(db.quote_score_table) \
                    .where(db.quote_score_table.c.QUOTE_ID == quote_id)

        upvotes = session.execute(stmt.where(db.quote_score_table.c.UPVOTED == True)).scalar()
        downvotes = session.execute(stmt.where(db.quote_score_table.c.UPVOTED == False)).scalar()

        result = session.execute(
            sql.update(db.quotes_table)
                .where(db.quotes_table.c.ID == quote_id)
                .values(SCORE=(upvotes - downvotes))
                .returning(db.quotes_table.c.SCORE)
        ).first()

        if result is not None:
            new_net_score = result.SCORE

        session.commit()

    user_score = None
    if undo_current:
        user_score = 0
    else:
        user_score = 1 if upvote else -1
    
    return new_net_score, user_score

class VoteDialog():

    down_color = 0x7193ff
    up_color = 0xff4500

    class VoteButton(discord.ui.Button):

        def __init__(self, vote_dialog, upvote : bool, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.vote_dialog = vote_dialog
            self.upvote = upvote

        async def callback(self, ctx : discord.Interaction):
            try:
                await ctx.response.defer(thinking=False)
                await self.vote_dialog.update_score(self.upvote)
            except Exception as e:
                bot.logger.error(e)
                raise e

    def __init__(self, quote_id : int, user_id : int):
        self.quote_id = quote_id
        self.user_id = user_id

    async def send(self, ctx : discord.Interaction):

        self.ctx = ctx

        quote_score = None
        user_score = None

        with Session(db.engine) as session:

            quote_data = session.execute(
                sql.select(db.quotes_table)
                    .where(db.quotes_table.c.ID == self.quote_id)
                    .limit(1)
            ).first()

            if quote_data is None:
                await ctx.response.send_message(embed=discord.Embed(
                    title='Something went wrong.',
                    color=0xff0000
                ))
                return
            
            quote_score = quote_data.SCORE

            user_data = session.execute(
                sql.select(db.quote_score_table)
                    .where(
                        (db.quote_score_table.c.QUOTE_ID == self.quote_id) &
                        (db.quote_score_table.c.USER_ID == self.user_id)
                    )
                    .limit(1)
            ).first()

            if user_data is None:
                user_score = 0
            else:
                user_score = 1 if user_data.UPVOTED else -1

        await ctx.response.send_message(
            embed=self.get_embed(user_score, quote_score),
            view=self.get_view(user_score),
            ephemeral=True
        )

    def get_embed(self, user_score : int, quote_score : int):

        user_score_int = user_score
        user_score = str(user_score)
        if user_score_int > 0:
            user_score = '<:plus:1247425658871877663> ' + user_score
        elif user_score_int < 0:
            user_score = '<:minus:1247426369147768892> ' + user_score[1:]
        
        color = None
        if user_score_int > 0:
            color = VoteDialog.up_color
        elif user_score_int < 0:
            color = VoteDialog.down_color
        else:
            color = bot.neutral_color

        return discord.Embed(
            title=f'Quote score: {'+' if quote_score > 0 else ''}{quote_score}',
            description=f'Your current score of this quote is: {user_score}',
            color=color
        )
    
    def get_view(self, user_score : int):

        up_button = VoteDialog.VoteButton(
            self, True,
            emoji='<:redditupvote:932087927155068968>' if user_score == 1 else '<:emptyupvote:1294943835536752770>',
            style=discord.ButtonStyle.grey
        )

        down_button = VoteDialog.VoteButton(
            self, False,
            emoji='<:redditdownvote:932088189194231809>' if user_score == -1 else '<:emptydownvote:1294943834786238464>',
            style=discord.ButtonStyle.grey
        )

        view = discord.ui.View()
        view.add_item(up_button)
        view.add_item(down_button)
        return view

    async def update_score(self, upvoted : bool):

        quote_score, user_score = vote_quote(self.quote_id, self.user_id, upvoted)

        await self.ctx.edit_original_response(
            embed=self.get_embed(user_score, quote_score),
            view=self.get_view(user_score)
        )

class QuoteView(discord.ui.View):

    def __init__(self, quote_data):

        super().__init__()

        self.quote_data = quote_data

        self.add_item(discord.ui.Button(
            emoji='🔗',
            url=f'https://discord.com/channels/{quote_data.SERVER_ID}/{quote_data.CHANNEL_ID}/{quote_data.MESSAGE_ID}',
            style=discord.ButtonStyle.grey
        ))
    
    @discord.ui.button(
        emoji='<:CubeReddit:251440616003600384>',
        label='Vote',
        style=discord.ButtonStyle.blurple
    )
    async def vote(self, ctx : discord.Interaction, button : discord.ui.Button):
        await VoteDialog(self.quote_data.ID, ctx.user.id).send(ctx)


@quote_group.command(name='random', description='Get a random quote from someone in this server!')
async def random_quote(ctx : discord.Interaction, author : discord.User = None):
    await get_quote(ctx, author)

@quote_group.command(name='specific', description='Get a specific quote by ID.')
async def specific_quote(ctx : discord.Interaction, id : int):
    await get_quote(ctx, None, id)

async def get_quote(ctx : discord.Interaction, author : discord.User = None, quote_id : int = None):

    query = sql.select(db.quotes_table).where(db.quotes_table.c.SERVER_ID == ctx.guild.id)
    if author is not None: query = query.where(db.quotes_table.c.USER_ID == author.id)
    elif quote_id is not None: query = query.where(db.quotes_table.c.ID == quote_id)
    query = query.order_by(sql.func.random())
    quote_data = sql_conn.execute(query).first()

    if quote_data is None:
        extra = ''
        if author is not None: extra = 'by that author'
        elif quote_id is not None: extra = 'with that ID'
        extra = ' ' + extra
        await ctx.response.send_message(embed=discord.Embed(
            title=f'There are no registered quotes{extra} in this server!',
            description='Propose a new quote by right clicking any message, clicking `Applications`, then `Propose Quote`!'
        ))
        return

    embed = discord.Embed(
        description=quote_data.CONTENT,
        color=bot.default_color
    )

    embed.timestamp = datetime.fromtimestamp(quote_data.TIMESTAMP)

    embed.set_footer(text=f'Quote #{quote_data.ID}  •  Score {'+' if quote_data.SCORE > 0 else ''}{quote_data.SCORE}')

    if author is None:
        author = bot.client.get_user(quote_data.USER_ID)
    if author is None:
        embed.set_author(name='Unknown author')
    else:
        embed.set_author(name=author.name, icon_url=author.display_avatar.url)

    await ctx.response.send_message(
        embed=embed,
        view=QuoteView(quote_data)
    )

@bot.tree.context_menu(name='Propose Quote')
async def propose_quote(ctx : discord.Interaction, message : discord.Message):

    values = dict(
        MESSAGE_ID=message.id,
        CONTENT=message.content,
        USER_ID=message.author.id,
        CHANNEL_ID=message.channel.id,
        SERVER_ID=message.guild.id,
        TIMESTAMP=message.created_at.timestamp(),
        PROPOSED_BY=ctx.user.id
    )

    with Session(db.engine) as session:

        existing = session.execute(
            sql.select(db.quotes_table)
                .where(db.quotes_table.c.MESSAGE_ID == message.id)
                .limit(1)
        ).first()
        if existing is not None:
            await ctx.response.send_message(
                embed=discord.Embed(
                    title='Quote proposal failed',
                    description='Someone else has already proposed that message!',
                    color=0xff0000
                ),
                ephemeral=True
            )
            return

        inserted_id = session.execute(
            postgresql.insert(db.quote_proposals_table)
                .values(**values)
                .on_conflict_do_update(
                    constraint=db.quote_proposal_constraint, set_=values
                )
        ).inserted_primary_key[0]

        session.commit()

    await ctx.response.send_message(embed=discord.Embed(
        title='Quote proposed successfully',
        description=f'[This message]({message.jump_url}) will be considered for a server quote.'
                  + f'\nThis quote proposal\'s ID is `{inserted_id}`',
        color=0x00ff00
    ))

class ProposalView(discord.ui.View):

    def __init__(self, prop_data, embed : discord.Embed, embed_ctx : discord.Interaction):
        super().__init__()
        self.prop_data = prop_data
        self.embed = embed
        self.embed_ctx = embed_ctx

    @discord.ui.button(label='Accept', style=discord.ButtonStyle.green)
    async def accept(self, ctx : discord.Interaction, button : discord.ui.Button):

        if not bot.is_admin(ctx.guild, ctx.user):
            await ctx.response.send_message(
                'You must be an administrator to manage quote proposals!',
                ephemeral=True
            )
            return

        values = dict(
            MESSAGE_ID=self.prop_data.MESSAGE_ID,
            CONTENT=self.prop_data.CONTENT,
            USER_ID=self.prop_data.USER_ID,
            CHANNEL_ID=self.prop_data.CHANNEL_ID,
            SERVER_ID=self.prop_data.SERVER_ID,
            TIMESTAMP=self.prop_data.TIMESTAMP,
            SCORE=0
        )

        with Session(db.engine) as session:
            session.execute(
                postgresql.insert(db.quotes_table)
                    .values(**values)
                    .on_conflict_do_update(
                        constraint=db.quotes_constraint, set_=values
                    )
            )
            session.execute(
                sql.delete(db.quote_proposals_table)
                    .where(db.quote_proposals_table.c.ID == self.prop_data.ID)
            )
            session.commit()

        self.stop()

        self.embed.color = 0x00ff00
        self.embed.set_footer(text='Proposal accepted!')

        await ctx.response.defer(thinking=False)
        await self.embed_ctx.edit_original_response(embed=self.embed)

    @discord.ui.button(label='Reject', style=discord.ButtonStyle.red)
    async def reject(self, ctx : discord.Interaction, button : discord.ui.Button):

        if not bot.is_admin(ctx.guild, ctx.user):
            await ctx.response.send_message(
                'You must be an administrator to manage quote proposals!',
                ephemeral=True
            )
            return

        sql_conn.execute(
            sql.delete(db.quote_proposals_table)
                .where(db.quote_proposals_table.c.ID == self.prop_data.ID)
        )
        sql_conn.commit()

        self.stop()

        self.embed.color = 0xff0000
        self.embed.set_footer(text='Proposal rejected.')

        await ctx.response.defer(thinking=False)
        await self.embed_ctx.edit_original_response(embed=self.embed)

@quote_group.command(name='review', description='[ADMIN ONLY] Review a quote proposal.')
async def review_quote_proposal(ctx : discord.Interaction, id : int = None):

    query = sql.select(db.quote_proposals_table).where(db.quote_proposals_table.c.SERVER_ID == ctx.guild.id)
    if id is not None: query = query.where(db.quote_proposals_table.c.ID == id)
    query = query.order_by(sql.func.random()).limit(1)
    prop_data = sql_conn.execute(query).first()

    if prop_data is None:
        await ctx.response.send_message(
            embed=discord.Embed(
                title=f'There are no pending proposed quotes in this server{' with that id!' if id is not None else ''}!'
            ),
            ephemeral=True
        )
        return

    jump_url = f'https://discord.com/channels/{prop_data.SERVER_ID}/{prop_data.CHANNEL_ID}/{prop_data.MESSAGE_ID}'
    embed = discord.Embed(
        title=f'Quote Proposal #{prop_data.ID}',
        description=f'```\n{prop_data.CONTENT}\n```\n\n{jump_url} \nProposed by: <@{prop_data.PROPOSED_BY}>',
        color=bot.neutral_color
    )
    await ctx.response.send_message(
        embed=embed,
        view=ProposalView(prop_data, embed, ctx)
    )

@quote_group.command(name='remove', description='[ADMIN ONLY] Remove a quote from the registry.')
async def remove_quote(ctx : discord.Interaction, id : int, reason : str = None):

    num_deleted = 0

    with Session(db.engine) as session:

        message_id = session.execute(
            sql.select(db.quotes_table)
                .where(db.quotes_table.c.ID == id)
        ).first()

        if message_id is not None:

            message_id = message_id.MESSAGE_ID

            session.execute(
                sql.delete(db.quote_score_table)
                    .where(db.quote_score_table.c.QUOTE_MESSAGE_ID == message_id)
            )

            num_deleted = session.execute(
                sql.delete(db.quotes_table)
                    .where(db.quotes_table.c.MESSAGE_ID == message_id)
            ).rowcount

            session.commit()
    
    if num_deleted == 0:
        await ctx.response.send_message(
            embed=discord.Embed(
                title='Removal failed',
                description=f'There is no quote with ID `{id}`!',
                color=0xff0000
            ),
            ephemeral=True
        )
    else:
        await ctx.response.send_message(
            embed=discord.Embed(
                title=f'Quote #{id} removed',
                description=None if reason is None else f'Reason: {reason}',
                color=0xff0000
            )
        )