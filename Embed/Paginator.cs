using NetCord;
using NetCord.Rest;
using NetCord.Services.ComponentInteractions;

public class EmbedPaginatorState
{
    public List<EmbedProperties> Pages { get; }
    public int CurrentPage { get; set; }
    public Interaction Interaction { get; }

    public EmbedPaginatorState(List<EmbedProperties> pages, int currentPage, Interaction interaction)
    {
        Pages = pages;
        CurrentPage = currentPage;
        Interaction = interaction;
    }

    public EmbedPaginatorState(EmbedProperties baseEmbed, List<string> pages, int currentPage, Interaction interaction)
    {
        Pages = [.. pages.Select(desc => baseEmbed.Clone().WithDescription(desc))];
        CurrentPage = currentPage;
        Interaction = interaction;
    }

}

public class EmbedPaginator : ComponentInteractionModule<ButtonInteractionContext>
{
    private static readonly Dictionary<ulong, EmbedPaginatorState> activePaginators = [];

    public static (EmbedProperties, ActionRowProperties) Register(EmbedPaginatorState state)
    {
        activePaginators[state.Interaction.Id] = state;
        return (
            GetEmbed(state),
            [
                new ButtonProperties($"pagination-prev:{state.Interaction.Id}", "◀", ButtonStyle.Primary),
                new ButtonProperties($"pagination-next:{state.Interaction.Id}", "▶", ButtonStyle.Primary)
            ]
        );
    }

    private static EmbedProperties GetEmbed(EmbedPaginatorState state)
    {
        var user = state.Interaction.User;
        return state.Pages[state.CurrentPage]
            .WithFooter(new()
            {
                Text = $"{user.Username} - Page {state.CurrentPage + 1}/{state.Pages.Count}",
                IconUrl = user.GetAvatarUrl()?.ToString()
            });
    }

    [ComponentInteraction("pagination-prev")]
    public async Task PrevPage(ulong interactionId)
    {
        if (!activePaginators.TryGetValue(interactionId, out var state)) return;
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
        await state.Interaction.ModifyResponseAsync(m => m.Embeds = [GetEmbed(state)]);
    }
    
    [ComponentInteraction("pagination-next")]
    public async Task NextPage(ulong interactionId)
    {
        if (!activePaginators.TryGetValue(interactionId, out var state)) return;
        if (state == null || Context.User.Id != state.Interaction.User.Id) return;
        if (state.CurrentPage + 1 >= state.Pages.Count)
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
        await state.Interaction.ModifyResponseAsync(m => m.Embeds = [GetEmbed(state)]);
    }
}