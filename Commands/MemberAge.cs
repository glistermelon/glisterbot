using Microsoft.EntityFrameworkCore;
using NetCord;
using NetCord.Rest;
using NetCord.Services.ApplicationCommands;
using NodaTime;

public class MemberAgeCommandModule : ApplicationCommandModule<ApplicationCommandContext>
{
    [SlashCommand("member-age", "See how long someone has been a server member for real.")]
    public async Task<InteractionMessageProperties> ExecuteMemberAge(User user)
    {
        if (Context.Guild == null) return "";
        ulong? timestamp = await new DatabaseContext().Messages
            .Where(m => m.UserId == user.Id && m.ServerId == Context.Guild.Id)
            .Select(m => (ulong?)m.Timestamp)
            .MinAsync();
        if (timestamp == null)
        {
            return new()
            {
                Content = "That user doesn't appear to be a member of this server!",
                Flags = NetCord.MessageFlags.Ephemeral
            };
        }
        else
        {
            var date = DateTimeOffset.FromUnixTimeSeconds((long)timestamp);
            string dateStr = FormatDate(date);

            var delta = NodaTime.Period.Between(
                LocalDateTime.FromDateTime(date.UtcDateTime),
                LocalDateTime.FromDateTime(DateTime.UtcNow)
            );
            string ageStr = FormatTimeDelta(delta);
            
            return new()
            {
                Embeds = [
                    new EmbedProperties()
                        .WithTitle($"{user.Username} Server Age")
                        .WithDescription($"Join Date: **{dateStr}**\nDuration: **{ageStr}**")
                        .WithColor(Globals.Colors.DarkGreen)
                        .WithThumbnail(user.GetAvatarUrl()?.ToString())
                ]
            };
        }
    }

    [SlashCommand("oldest-members", "Rank members by how long they've been here.")]
    public async Task<InteractionMessageProperties> ExecuteOldestMembers(bool includeBots = false)
    {
        if (Context.Guild == null) return "";
        List<(ulong UserId, ulong MinTimestamp)> results = (await new DatabaseContext().Messages
            .Where(m => m.ServerId == Context.Guild.Id)
            .GroupBy(m => m.UserId)
            .Select(g => new
            {
                UserId = g.Key,
                MinTimestamp = g.Min(m => m.Timestamp)
            })
            .ToListAsync())
            .Select(g => (g.UserId, g.MinTimestamp))
            .ToList();

        var serverMembers = await Context.Guild.GetUsersAsync().ToArrayAsync();
        results.RemoveAll(r => !serverMembers.Select(u => u.Id).Contains(r.UserId));
        if (!includeBots)
        {
            var botMembers = serverMembers.Where(u => u.IsBot);
            results.RemoveAll(r => botMembers.Select(u => u.Id).Contains(r.UserId));
        }

        var serverMemberIds = await Context.Guild.GetUsersAsync().Select(u => u.Id).ToArrayAsync();
        results.RemoveAll(r => !serverMemberIds.Contains(r.UserId));

        // -------- hardcoded exceptions --------
        // Mostly so people stop bothering me about these
        results = results.Select(r =>
        {
            var timestamp = r.MinTimestamp;

            // RGDCTW Vaz
            if (r.UserId == 705360840345518121) timestamp = 1642238012;

            return (r.UserId, timestamp);
        }).ToList();
        // --------------------------------------

        List<string> lines = [];
        foreach ((var result, var i) in results.OrderBy(r => r.MinTimestamp).Select((r, i) => (r, i)))
        {
            string dateStr = FormatDate(DateTimeOffset.FromUnixTimeSeconds((long)result.MinTimestamp));
            lines.Add($"{i + 1}. <@{result.UserId}> - Joined **{dateStr}**");
        }
        List<string> pages = [.. lines.Chunk(10).Select(chunk => string.Join("\n", chunk))];
        (var embed, var actionRow) = EmbedPaginator.Register(new(
            new EmbedProperties()
                .WithTitle("Oldest Server Members")
                .WithColor(Globals.Colors.DarkGreen),
            pages,
            0,
            Context.Interaction
        ));
        return new()
        {
            Embeds = [embed],
            Components = [actionRow]
        };
    }

    private static string FormatDate(DateTimeOffset date) {
        return date.ToString("d MMMM yyyy");
    }

    private static string FormatTimeDelta(NodaTime.Period period)
    {
        List<string> parts = [];
        if (period.Years != 0) parts.Add($"{period.Years} years");
        if (period.Months != 0) parts.Add($"{period.Months} months");
        if (period.Days != 0) parts.Add($"{period.Days} days");
        return parts.Count != 0 ? string.Join(", ", parts) : "less than a day";
    }
}