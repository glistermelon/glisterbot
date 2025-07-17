using NetCord;
using NetCord.Rest;
using NetCord.Services.ApplicationCommands;
using NetCord.Services.ComponentInteractions;

namespace GlisterBot.Commands;

public class DiscordTagSearchEmbedPage : LazyPaginatedEmbedState
{
    private const int entriesPerPage = 10;
    private readonly List<DiscordServerEntry> serverEntries;
    private readonly string query;
    private readonly RestClient restClient;

    public DiscordTagSearchEmbedPage(
        IEnumerable<DiscordServerEntry> entries,
        string query,
        Interaction interaction,
        RestClient restClient
    )
        : base(0, (entries.Count() + entriesPerPage - 1) / entriesPerPage, interaction)
    {
        serverEntries = [.. entries];
        this.query = query.ToLower();
        this.restClient = restClient;
    }

    private EmbedProperties GetBaseEmbed() {
        return new EmbedProperties()
            .WithTitle($"`{query}` Tag Search")
            .WithColor(Globals.Colors.DarkGreen);
    }

    public override async Task<(EmbedProperties, List<IComponentProperties>)> LoadPage()
    {
        List<(string name, DiscordServerEntry entry)> selectedEntries = [];
        int unnamedCounter = 1;
        foreach (var entry in serverEntries.Skip(entriesPerPage * CurrentPage).Take(entriesPerPage))
        {
            await entry.LoadRestInviteIfNecessary(restClient);
            if (entry.RestInvite == null)
            {
                continue;
            }
            RestGuild? guild = entry.RestInvite.Guild;
            string name;
            if (guild == null)
            {
                name = $"unnamed {unnamedCounter}";
                unnamedCounter++;
            }
            else
            {
                name = guild.Name;
                if (guild.NsfwLevel == NsfwLevel.Explicit || guild.NsfwLevel == NsfwLevel.AgeRestricted)
                {
                    name = "[NSFW] " + name;
                }
            }
            selectedEntries.Add((name, entry));
        }
        selectedEntries = [.. selectedEntries.OrderByDescending(e => e.entry.RestInvite?.ApproximateUserCount ?? 0)];

        if (selectedEntries.Count == 0)
        {
            return (GetBaseEmbed().WithDescription("This page is empty."), []);
        }

        EmbedProperties embed = GetBaseEmbed()
            .WithFields([
                new() {
                    Name = "Tag",
                    Value = string.Join('\n', selectedEntries.Select(e => $"{e.entry.tagText}")),
                    Inline = true
                },
                new() {
                    Name = "Members",
                    Value = string.Join('\n', selectedEntries.Select(e => $"{e.entry.RestInvite?.ApproximateUserCount:n0}")),
                    Inline = true
                },
                new() {
                    Name = "Name",
                    Value = string.Join('\n', selectedEntries.Select(e => e.name)),
                    Inline = true
                }
            ]);

        var menu = new StringMenuProperties("tagsearch-select").AddOptions(
            selectedEntries.Select(e => new StringMenuSelectOptionProperties(
                e.name, $"{e.entry.entryId}"
            ))
        );

        return (embed, [menu]);
    }

    public override EmbedProperties GetLoadingEmbed()
    {
        return GetBaseEmbed().WithDescription("*Loading...*");
    }
}

public class InviteMenuInteractionModule(RestClient restClient) : ComponentInteractionModule<StringMenuInteractionContext>
{
    public RestClient RestClient { get; set; } = restClient;

    [ComponentInteraction("tagsearch-select")]
    public async Task GetServerInvite()
    {
        ulong entryId = ulong.Parse(Context.SelectedValues[0]);
        DiscordServerEntry? entry = ServerListingHandler.ServerEntries.Where(e => e.entryId == entryId).FirstOrDefault();
        if (entry == null)
        {
            await Context.Interaction.SendResponseAsync(InteractionCallback.Message(new()
            {
                Content = "Something went wrong.",
                Flags = MessageFlags.Ephemeral
            }));
        }
        else
        {
            await Context.Interaction.SendResponseAsync(InteractionCallback.Message(new()
            {
                Content = $"<@{Context.Interaction.User.Id}>\nhttps://discord.gg/" + entry.inviteCode
            }));
        }
    }
}

public class DiscordTagSearch(RestClient restClient) : ApplicationCommandModule<ApplicationCommandContext>
{
    [SlashCommand("discord-tag-search", "Search for Discord server tags (might be outdated)")]
    public async Task ExecuteTagSearch(string query)
    {
        if (query.Length == 0 || query.Length > 4)
        {
            await Context.Interaction.SendResponseAsync(InteractionCallback.Message(
                new InteractionMessageProperties()
                {
                    Content = "The tag query should be between 1 and 4 characters long.",
                    Flags = MessageFlags.Ephemeral
                }
            ));
            return;
        }

        await Context.Interaction.SendResponseAsync(InteractionCallback.DeferredMessage());

        query = query.ToLower();
        IEnumerable<DiscordServerEntry> entries = ServerListingHandler.ServerEntries
            .Where(e => e.tagText.ToLower().Contains(query));

        var baseEmbed = new EmbedProperties()
            .WithTitle("Message Log Status")
            .WithColor(Globals.Colors.DarkGreen);


        (var embed, var components) = await EmbedPaginator.RegisterLazy(new DiscordTagSearchEmbedPage(
            entries, query, Context.Interaction, restClient
        ));

        await Context.Interaction.SendFollowupMessageAsync(new InteractionMessageProperties()
        {
            Embeds = [embed],
            Components = components
        });
    }
}