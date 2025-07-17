using Microsoft.EntityFrameworkCore;
using NetCord;
using NetCord.Rest;
using NetCord.Services.ApplicationCommands;
using Npgsql;

namespace GlisterBot.Commands;

class PhraseLeaderboardQueryResult
{
    public ulong UserId { get; set; }
    public int Count { get; set; }
}

public partial class Stats
{
    [SubSlashCommand("phrase-leaderboard", "See what users have said a phrase the most.")]
    public async Task ExecutePhraseLeaderboard(string phrase)
    {
        await ExecutePhraseLeaderboardStatic(phrase, Context);
    }

    public static async Task ExecutePhraseLeaderboardStatic(
        string phrase,
        ApplicationCommandContext Context
    )
    {
        if (Context.Guild == null) return;

        phrase = phrase.Trim();

        if (phrase.Length > 100)
        {
            await Context.Interaction.SendResponseAsync(InteractionCallback.Message(
                new InteractionMessageProperties()
                {
                    Content = "That phrase is too long! Please pick a shorter phrase.",
                    Flags = MessageFlags.Ephemeral
                }
            ));
            return;
        }

        await Context.Interaction.SendResponseAsync(InteractionCallback.DeferredMessage());

        string rawSql = $@"
            SELECT ""USER_ID"", COUNT(*) FROM (
                SELECT unnest(
                    regexp_matches(
                        ""CONTENT"",
                        @regex,
                        'gi'
                    )
                ), ""USER_ID""
                FROM ""MESSAGES""
            )
            GROUP BY ""USER_ID"";";
        var regexParam = new NpgsqlParameter("regex", RegexHelper.GetPhraseRegex(phrase));
        var results = await new DatabaseContext().Database
            .SqlQueryRaw<PhraseLeaderboardQueryResult>(rawSql, regexParam)
            .ToListAsync();

        var baseEmbed = new EmbedProperties()
            .WithTitle($"Who has said \"{phrase}\" the most?")
            .WithColor(Globals.Colors.DarkGreen);

        if (results.Count == 0)
        {
            await Context.Interaction.SendFollowupMessageAsync(new InteractionMessageProperties()
            {
                Embeds = [baseEmbed.WithDescription(
                    "That phrase has never been said before! You could be the first... <:Smoothtroll:960789594658451497>"
                )]
            });
            return;
        }

        var serverMemberIds = await Context.Guild.GetUsersAsync().Select(u => u.Id).ToArrayAsync();
        results.RemoveAll(r => !serverMemberIds.Contains(r.UserId));

        List<string> pages = [];
        List<string> page = [];
        foreach (
            var resultWithIndex in results.OrderByDescending(r => r.Count)
                .Select((r, i) => new { Result = r, Index = i })
        )
        {
            var result = resultWithIndex.Result;
            var index = resultWithIndex.Index;
            page.Add($"{index + 1}. <@{result.UserId}> - **{result.Count}** time{(result.Count > 1 ? "s" : "")}");
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