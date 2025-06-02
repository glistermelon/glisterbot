#pragma warning disable 8618

using NetCord;
using NetCord.Rest;
using NetCord.Services.ApplicationCommands;
using GlisterBot.Commands.Wordbomb;
using Microsoft.EntityFrameworkCore;
using ScottPlot;

namespace GlisterBot.Commands;

public class WordbombCommandModule : ApplicationCommandModule<ApplicationCommandContext>
{
    [SlashCommand("wordbomb", "Play wordbomb on Discord!")]
    public InteractionMessageProperties ExecutePlayWordbomb(
        WordbombDifficulty difficulty,
        WordbombLanguage language = WordbombLanguage.English
    )
    {
        if (Context.Guild == null) return "";
        if (ChannelManager.ChannelIsBusy(Context.Channel.Id))
        {
            return new()
            {
                Content = "There is already a game or activity active in this channel!",
                Flags = MessageFlags.Ephemeral
            };
        }
        ChannelManager.MarkAsBusy(Context.Channel.Id, TimeSpan.FromMinutes(5));
        return WordbombQueue.Register(new()
        {
            Interaction = Context.Interaction,
            Difficulty = difficulty,
            Language = language,
            Users = [Context.User],
            ChannelId = Context.Channel.Id,
            ServerId = Context.Guild.Id
        });
    }

    [SlashCommand("wordbomb-stats", "Wordbomb statistics!")]
    public async Task<InteractionMessageProperties> ExecuteWordbombStats(
        User? user = null
    )
    {
        if (Context.Guild == null) return "";

        if (user == null) user = Context.User;

        var dbContext = new DatabaseContext();

        int gamesWon = dbContext.WordbombResults.Where(
            r => r.Victory && r.UserId == user.Id && r.Game.ServerId == Context.Guild.Id
        ).Count();
        int gamesLost = dbContext.WordbombResults.Where(
            r => !r.Victory && r.UserId == user.Id && r.Game.ServerId == Context.Guild.Id
        ).Count();
        int gamesPlayed = gamesWon + gamesLost;
        if (gamesPlayed == 0) goto not_enough_games_error;
        double winLoseRatio = gamesLost == 0 ? double.NaN : (double)gamesWon / gamesLost;

        var missedPhrases = (await GetMissedPhrases(user.Id, Context.Guild.Id, dbContext))
            .Take(3).Select(r => r.Phrase).ToList();
        ulong? oppUserId = await GetBestOpposingPlayerId(user.Id, Context.Guild.Id, dbContext);

        List<string> words = await dbContext.WordbombPasses
            .Where(p => p.Game.ServerId == Context.Guild.Id && p.UserId == user.Id)
            .Select(p => p.Word)
            .ToListAsync();
        if (words.Count == 0) goto not_enough_games_error;
        double averageWordLength = (double)words.Select(w => w.Length).Sum() / words.Count;
        string longestWord = words.Select(w => (w, w.Length)).MaxBy(g => g.Length).w;
        string? favoriteWord = words.GroupBy(w => w).MaxBy(g => g.Count())?.Key;

        List<ulong> survivalCounts = await GetPromptSurvivalCounts(user.Id, Context.Guild.Id, dbContext);
        double averageSurvivalTime = (double)survivalCounts.Aggregate(0ul, (s, n) => s + n) / survivalCounts.Count;
        ulong longestGame = survivalCounts.Max();
        ulong shortestGame = survivalCounts.Min();

        string desc = "";
        desc += $"**Games Played:** {gamesPlayed}";
        desc += $"**\nGames Won:** {gamesWon}";
        desc += $"**\nGames Lost**: {gamesLost}";
        desc += $"**\nWin-to-Lose Ratio:** {winLoseRatio:f2}";
        desc += $"**\nMost-Missed Prompts:** " + string.Join(", ", missedPhrases);
        desc += $"**\nBiggest Opp:** <@{oppUserId}>";
        desc += $"**\nAverage Word Length:** {averageWordLength:f2}";
        desc += $"**\nLongest Word:** `{longestWord}`";
        desc += $"**\nFavorite Word:** `{favoriteWord}`";
        desc += $"**\nAverage Survival Time:** {averageSurvivalTime:f2} prompts";

        desc += $"**\nLongest Game:** {longestGame} prompt";
        if (longestGame != 1) desc += "s";

        desc += $"**\nShortest Game:** {shortestGame} prompt";
        if (shortestGame != 1) desc += "s";

        return new()
        {
            Embeds = [
                new EmbedProperties()
                    .WithTitle($"{user.Username}'s Wordbomb Statistics")
                    .WithColor(Globals.Colors.DarkGreen)
                    .WithDescription(desc)
            ]
        };

    not_enough_games_error:
        return new()
        {
            Embeds = [
                new EmbedProperties()
                    .WithTitle($"{user.Username}'s Wordbomb Statistics")
                    .WithColor(Globals.Colors.DarkGreen)
                    .WithDescription(
                        user.Id == Context.User.Id
                        ? "You have not yet played enough games for statistics to be compiled!"
                        : "This user has not yet played enough games for statistics to be compiled!"
                    )
            ]
        };
    }

    private static async Task<List<GroupedPhraseCountResult>> GetMissedPhrases(ulong userId, ulong serverId, DatabaseContext dbContext)
    {
        string rawSql = $@"
            SELECT ""PHRASE"", COUNT(*)
            FROM ""WORDBOMB_FAILS"" f
            JOIN ""WORDBOMB_GAMES"" g ON g.""ID"" = f.""GAME_ID""
            WHERE f.""USER_ID"" = {userId}
                AND g.""SERVER_ID"" = {serverId}
            GROUP BY f.""PHRASE""
            ORDER BY count DESC";
        return await dbContext.Database.SqlQueryRaw<GroupedPhraseCountResult>(rawSql).ToListAsync();
    }

    private static async Task<ulong?> GetBestOpposingPlayerId(ulong userId, ulong serverId, DatabaseContext dbContext)
    {
        string rawSql = $@"
            SELECT r2.""USER_ID"", COUNT(*) AS ""COUNT""
            FROM ""WORDBOMB_RESULTS"" r1
            JOIN ""WORDBOMB_RESULTS"" r2
                ON r1.""GAME_ID"" = r2.""GAME_ID"" AND r2.""VICTORY""
            JOIN ""WORDBOMB_GAMES"" g
                ON r1.""GAME_ID"" = g.""ID""
            WHERE g.""SERVER_ID"" = {serverId}
                AND r1.""USER_ID"" = {userId}
                AND NOT r1.""VICTORY""
            GROUP BY r2.""USER_ID""
            ORDER BY ""COUNT"" DESC
            LIMIT 1";
        return (await dbContext.Database.SqlQueryRaw<GroupedUserCountResult>(rawSql).FirstOrDefaultAsync())?.UserId;
    }

    private static async Task<List<ulong>> GetPromptSurvivalCounts(ulong userId, ulong serverId, DatabaseContext dbContext)
    {
        string rawSql = $@"
            SELECT COUNT(*) AS prompt_count
            FROM ""WORDBOMB_PASSES"" p
            JOIN ""WORDBOMB_GAMES"" g ON g.""ID"" = p.""GAME_ID""
            WHERE p.""USER_ID"" = {userId}
                AND g.""SERVER_ID"" = {serverId}
            GROUP BY p.""GAME_ID""";
        return (await dbContext.Database.SqlQueryRaw<PromptSurvivalCountResult>(rawSql).ToListAsync())
            .Select(r => r.Count).ToList();
    }
}

class GroupedPhraseCountResult
{
    public string Phrase { get; set; }
    public int Count { get; set; }
}

class GroupedUserCountResult
{
    public ulong UserId { get; set; }
    public int Count { get; set; }
}

class PromptSurvivalCountResult {
    public ulong Count { get; set; }
}