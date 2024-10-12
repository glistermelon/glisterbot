import database as db
from datetime import datetime
from database import sql, sql_conn
from sqlalchemy import func as sql_func
from sqlalchemy.orm import Session
from sqlalchemy.dialects import postgresql
import discord
import bot

quote_group = discord.app_commands.Group(name='quote', description='Weird server-dependent quote stuff!')
bot.tree.add_command(quote_group)

class QuoteView(discord.ui.View):

    active_views = []

    class VoteButton(discord.ui.Button):

        def __init__(self, upvote : bool, quote_view, *args, **kwargs):

            super().__init__(*args, **kwargs)

            self.upvote = upvote
            self.quote_view = quote_view
        
        async def callback(self, ctx : discord.Interaction):

            await ctx.response.defer(thinking=False)

            score = None

            with Session(db.engine) as session:

                upvoted = session.execute(
                    sql.select(db.quote_score_table.c.UPVOTED)
                        .where(
                            (db.quote_score_table.c.QUOTE_ID == self.quote_view.quote_data.ID) &
                            (db.quote_score_table.c.USER_ID == ctx.user.id)
                        )
                        .limit(1)
                ).first()

                if upvoted is not None and upvoted.UPVOTED == self.upvote:
                    return

                if upvoted is None:         
                    session.execute(
                        sql.insert(db.quote_score_table).values(
                            QUOTE_ID=self.quote_view.quote_data.ID,
                            USER_ID=ctx.user.id,
                            UPVOTED=self.upvote
                        )
                    )
                else:
                    session.execute(
                        sql.delete(db.quote_score_table)
                            .where(
                                (db.quote_score_table.c.QUOTE_ID == self.quote_view.quote_data.ID) &
                                (db.quote_score_table.c.USER_ID == ctx.user.id)
                            )
                    )

                score = session.execute(
                    sql.update(db.quotes_table)
                        .where(db.quotes_table.c.ID == self.quote_view.quote_data.ID)
                        .values(SCORE=db.quotes_table.c.SCORE + (1 if self.upvote else -1))
                        .returning(db.quotes_table.c.SCORE)
                ).first().SCORE

                session.commit()

            for quote_view in QuoteView.active_views:
                if quote_view.quote_data.ID != self.quote_view.quote_data.ID:
                    continue
                quote_view.score_button.label = str(score)
                quote_view.refresh_buttons()
                await quote_view.embed_ctx.edit_original_response(view=quote_view)

    class UnresponsiveButton(discord.ui.Button):
        async def callback(self, ctx : discord.Interaction):
            await ctx.response.defer(thinking=False)

    def __init__(self, quote_data, embed : discord.Embed, embed_ctx : discord.Interaction):

        super().__init__()

        self.quote_data = quote_data
        self.embed = embed
        self.embed_ctx = embed_ctx
        self.score_button = QuoteView.UnresponsiveButton(
            label=str(self.quote_data.SCORE),
            style=discord.ButtonStyle.blurple
        )
        self.refresh_buttons()

        QuoteView.active_views.append(self)
    
    async def on_timeout(self):

        QuoteView.active_views.remove(self)
    
    def refresh_buttons(self):

        self.clear_items()

        score = int(self.score_button.label)
        if score < 0: self.score_button.style = discord.ButtonStyle.red
        elif score == 0: self.score_button.style = discord.ButtonStyle.blurple
        else: self.score_button.style = discord.ButtonStyle.green

        self.add_item(discord.ui.Button(
            emoji='🔗',
            style=discord.ButtonStyle.grey,
            url=f'https://discord.com/channels/{self.quote_data.SERVER_ID}/{self.quote_data.CHANNEL_ID}/{self.quote_data.MESSAGE_ID}'
        ))
        self.add_item(QuoteView.VoteButton(
            True, self,
            emoji='👍', style=discord.ButtonStyle.grey
        ))
        self.add_item(self.score_button)
        self.add_item(QuoteView.VoteButton(
            False, self,
            emoji='👎', style=discord.ButtonStyle.grey
        ))

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
    query = query.order_by(sql_func.random())
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
    embed.set_footer(text=f'Quote #{quote_data.ID}')
    if author is None: author = bot.client.get_user(quote_data.USER_ID)
    if author is None:
        embed.set_author(name='Unknown author')
    else:
        embed.set_author(name=author.name, icon_url=author.display_avatar.url)

    await ctx.response.send_message(
        embed=embed,
        view=QuoteView(quote_data, embed, ctx)
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
    query = query.order_by(sql_func.random()).limit(1)
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