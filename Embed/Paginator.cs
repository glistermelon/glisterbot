using NetCord;
using NetCord.Rest;
using NetCord.Services.ComponentInteractions;

public abstract class PaginatedEmbedState(int currentPage, int pageCount, Interaction interaction)
{
    public int CurrentPage { get; set; } = currentPage;
    public int PageCount { get; set; } = pageCount;
    public Interaction Interaction { get; set; } = interaction;

    protected EmbedFooterProperties GetFooter()
    {
        var user = Interaction.User;
        return new()
        {
            Text = $"{user.Username} - Page {CurrentPage + 1}/{PageCount}",
            IconUrl = user.GetAvatarUrl()?.ToString()
        };
    }
}

public class SimplePaginatedEmbedState : PaginatedEmbedState
{
    public List<EmbedProperties> Pages { get; }

    public SimplePaginatedEmbedState(List<EmbedProperties> pages, int currentPage, Interaction interaction)
        : base(currentPage, pages.Count, interaction)
    {
        Pages = pages;
    }

    public SimplePaginatedEmbedState(EmbedProperties baseEmbed, List<string> pages, int currentPage, Interaction interaction)
        : base(currentPage, pages.Count, interaction)
    {
        Pages = [.. pages.Select(desc => baseEmbed.Clone().WithDescription(desc))];
    }

    public virtual EmbedProperties GetEmbed()
    {
        return Pages[CurrentPage].WithFooter(GetFooter());
    }

}

public abstract class LazyPaginatedEmbedState : PaginatedEmbedState
{
    public LazyPaginatedEmbedState(int currentPage, int pageCount, Interaction interaction)
        : base(currentPage, pageCount, interaction)
    { }

    public abstract Task<(EmbedProperties, List<IComponentProperties>)> LoadPage();
    public abstract EmbedProperties GetLoadingEmbed();

    public async Task<(EmbedProperties, List<IComponentProperties>)> GetEmbedAsync()
    {
        var result = await LoadPage();
        result.Item1 = result.Item1.WithFooter(GetFooter());
        return result;
    }
}

public class EmbedPaginator : ComponentInteractionModule<ButtonInteractionContext>
{
    private static readonly Dictionary<ulong, SimplePaginatedEmbedState> simplePaginators = [];
    private static readonly Dictionary<ulong, LazyPaginatedEmbedState> lazyPaginators = [];

    private static ActionRowProperties GetPageControlComponent(PaginatedEmbedState state)
    {
        return new ActionRowProperties([
            new ButtonProperties($"pagination-prev:{state.Interaction.Id}", "◀", ButtonStyle.Primary),
            new ButtonProperties($"pagination-next:{state.Interaction.Id}", "▶", ButtonStyle.Primary)
        ]);
    }

    public static (EmbedProperties, ActionRowProperties) Register(SimplePaginatedEmbedState state)
    {
        simplePaginators[state.Interaction.Id] = state;
        return (state.GetEmbed(), GetPageControlComponent(state));
    }

    public static async Task<(EmbedProperties, List<IComponentProperties>)> RegisterLazy(LazyPaginatedEmbedState state)
    {
        lazyPaginators[state.Interaction.Id] = state;
        List<IComponentProperties> components = [GetPageControlComponent(state)];
        (var embed, var moreComponents) = await state.GetEmbedAsync();
        components.AddRange(moreComponents);
        return (embed, components);
    }

    public void GetState(
        ulong interactionId,
        out PaginatedEmbedState? state,
        out SimplePaginatedEmbedState? simpleState,
        out LazyPaginatedEmbedState? lazyState
    )
    {
        state = null;
        lazyState = null;

        simplePaginators.TryGetValue(interactionId, out simpleState);
        if (simpleState != null)
        {
            state = simpleState;
            return;
        }

        lazyPaginators.TryGetValue(interactionId, out lazyState);
        if (lazyState != null)
        {
            state = lazyState;
            return;   
        }
    }

    [ComponentInteraction("pagination-prev")]
    public async Task PrevPage(ulong interactionId)
    {
        PaginatedEmbedState? state;
        SimplePaginatedEmbedState? simpleState;
        LazyPaginatedEmbedState? lazyState;
        GetState(interactionId, out state, out simpleState, out lazyState);
        if (state == null || Context.User.Id != state.Interaction.User.Id) return;
        if (state.CurrentPage == 0)
        {
            await Context.Interaction.SendResponseAsync(
                InteractionCallback.Message(
                    new InteractionMessageProperties
                    {
                        Content = "There are no pages before this one!",
                        Flags = MessageFlags.Ephemeral
                    }
                )
            );
            return;
        }
        await Context.Interaction.SendResponseAsync(InteractionCallback.DeferredModifyMessage);
        state.CurrentPage--;
        if (simpleState != null)
        {
            await state.Interaction.ModifyResponseAsync(m => m.Embeds = [simpleState.GetEmbed()]);
        }
        else
        {
            if (lazyState == null) return;
            await state.Interaction.ModifyResponseAsync(m => m.Embeds = [lazyState.GetLoadingEmbed()]);
            List<IComponentProperties> components = [GetPageControlComponent(state)];
            (var embed, var moreComponents) = await lazyState.GetEmbedAsync();
            components.AddRange(moreComponents);
            await state.Interaction.ModifyResponseAsync(m => {
                m.Embeds = [embed];
                m.Components = components;
            });
        }   
    }

    [ComponentInteraction("pagination-next")]
    public async Task NextPage(ulong interactionId)
    {
        PaginatedEmbedState? state;
        SimplePaginatedEmbedState? simpleState;
        LazyPaginatedEmbedState? lazyState;
        GetState(interactionId, out state, out simpleState, out lazyState);
        if (state == null || Context.User.Id != state.Interaction.User.Id) return;
        if (state.CurrentPage + 1 >= state.PageCount)
        {
            await Context.Interaction.SendResponseAsync(
                InteractionCallback.Message(
                    new InteractionMessageProperties
                    {
                        Content = "There are no pages after this one!",
                        Flags = MessageFlags.Ephemeral
                    }
                )
            );
            return;
        }
        await Context.Interaction.SendResponseAsync(InteractionCallback.DeferredModifyMessage);
        state.CurrentPage++;
        if (simpleState != null)
        {
            await state.Interaction.ModifyResponseAsync(m => m.Embeds = [simpleState.GetEmbed()]);
        }
        else
        {
            if (lazyState == null) return;
            await state.Interaction.ModifyResponseAsync(m => m.Embeds = [lazyState.GetLoadingEmbed()]);
            List<IComponentProperties> components = [GetPageControlComponent(state)];
            (var embed, var moreComponents) = await lazyState.GetEmbedAsync();
            components.AddRange(moreComponents);
            await state.Interaction.ModifyResponseAsync(m => {
                m.Embeds = [embed];
                m.Components = components;
            });
        }
    }
}