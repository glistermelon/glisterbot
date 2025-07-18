using Microsoft.EntityFrameworkCore;
using NetCord;
using NetCord.Rest;
using NetCord.Services.ApplicationCommands;
using Npgsql;

namespace GlisterBot.Commands;

class MessageLeaderboardQueryResult
{
    public ulong UserId { get; set; }
    public int Count { get; set; }
}

public partial class Stats
{
    [SubSlashCommand("message-counts", "See who has sent the most messages.")]
    public async Task ExecuteMessageLeaderboard(bool includeBots = false)
    {
        if (Context.Guild == null) return;

        await Context.Interaction.SendResponseAsync(InteractionCallback.DeferredMessage());

        string rawSql = $@"
            SELECT ""USER_ID"", COUNT(*)
            FROM ""MESSAGES""
            GROUP BY ""USER_ID"";
        ";
        var results = await new DatabaseContext().Database
            .SqlQueryRaw<MessageLeaderboardQueryResult>(rawSql)
            .ToListAsync();

        var baseEmbed = new EmbedProperties()
            .WithTitle($"Message Count Leaderboard")
            .WithColor(Globals.Colors.DarkGreen);

        if (results.Count == 0)
        {
            await Context.Interaction.SendFollowupMessageAsync(new InteractionMessageProperties()
            {
                Embeds = [baseEmbed.WithDescription(
                    "Nobody has sent any messages!"
                )]
            });
            return;
        }

        var serverMembers = await Context.Guild.GetUsersAsync().ToArrayAsync();
        results.RemoveAll(r => !serverMembers.Select(u => u.Id).Contains(r.UserId));
        if (!includeBots)
        {
            var botMembers = serverMembers.Where(u => u.IsBot);
            results.RemoveAll(r => botMembers.Select(u => u.Id).Contains(r.UserId));
        }

        List<string> pages = [];
        List<string> page = [];
        foreach (
            var resultWithIndex in results.OrderByDescending(r => r.Count)
                .Select((r, i) => new { Result = r, Index = i })
        )
        {
            var result = resultWithIndex.Result;
            var index = resultWithIndex.Index;
            page.Add($"{index + 1}. <@{result.UserId}> - **{result.Count:n0}** message{(result.Count > 1 ? "s" : "")}");
            if (page.Count == 15)
            {
                pages.Add(string.Join("\n", page));
                page.Clear();
            }
        }
        if (page.Count != 0)
        {
            pages.Add(string.Join("\n", page));
        }

        (var embed, var actionRow) = EmbedPaginator.Register(new(baseEmbed, pages, 0, Context.Interaction));

        await Context.Interaction.SendFollowupMessageAsync(new InteractionMessageProperties()
        {
            Embeds = [embed],
            Components = [actionRow]
        });

    }
}