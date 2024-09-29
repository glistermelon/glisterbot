import discord
import bot

class PaginatedEmbed:

    class ButtonView(discord.ui.View):

        def __init__(self, owner : discord.User, notify):
            super().__init__()
            self.owner = owner
            self.notify = notify

        async def on_timeout(self):
            self.clear_items()
            await self.notify.on_timeout()

        @discord.ui.button(label=' < ',style=discord.ButtonStyle.blurple)
        async def left(self, ctx : discord.Interaction, b : discord.ui.Button):
            if ctx.user.id != self.owner.id:
                await ctx.response.send_message('This is not your window!', ephemeral=True)
                return
            await self.notify.prev_page(ctx)

        @discord.ui.button(label=' > ',style=discord.ButtonStyle.blurple)
        async def right(self, ctx : discord.Interaction, b : discord.ui.Button):
            if ctx.user.id != self.owner.id:
                await ctx.response.send_message('This is not your window!', ephemeral=True)
                return
            await self.notify.next_page(ctx)

    def __init__(self, ctx : discord.Interaction):
        self.page = 0
        self.ctx = ctx
        self.view = PaginatedEmbed.ButtonView(ctx.user, self)

    async def on_timeout(self):
        await self.ctx.edit_original_response(
            embed=discord.Embed(
                description='*Session expired after 5 minutes of inactivity.*',
                color=bot.neutral_color
            )
        )

    async def prev_or_next_page(self, prev : bool, ctx : discord.Interaction):
        offset = -1 if prev else 1
        embed = self.get_page(self.page + offset)
        if embed is None:
            await ctx.response.send_message(f'There are no pages {'before' if prev else 'after'} this one!', ephemeral=True)
        else:
            self.page += offset
            await self.ctx.edit_original_response(embed=embed)
            await ctx.response.defer()

    async def prev_page(self, ctx : discord.Interaction):
        await self.prev_or_next_page(True, ctx)
    
    async def next_page(self, ctx):
        await self.prev_or_next_page(False, ctx)

    def get_page(self, number):
        raise RuntimeError('get_page not overridden')
    
    async def send(self):
        await self.ctx.response.send_message(embed=self.get_page(self.page), view=self.view)