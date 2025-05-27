using Microsoft.EntityFrameworkCore;
using NetCord.Rest;
using NetCord.Services.ApplicationCommands;

namespace GlisterBot.Commands;

public partial class Stats
{
    [SubSlashCommand("log-status", "Get the status of message log")]
    public async Task<InteractionMessageProperties> ExecuteLogStatus()
    {
        if (Context.Guild == null) return "";
        var serverId = Context.Guild.Id;

        Dictionary<ulong, IntRangeSet> timespans = (await new DatabaseContext().TimeRanges
                .Where(t => t.Channel.ServerId == serverId)
                .ToListAsync())
                .GroupBy(t => t.ChannelId)
                .ToDictionary(g => g.Key, g => new IntRangeSet(g.ToList()));



        string titleString = "# Recorded Times";
        List<string> fields = [titleString];
        List<string> pages = [];
        int lines = 1;
        foreach (var channelId in timespans.Keys)
        {
            string field = $"## <#{channelId}>";
            lines += 2;
            foreach (var range in timespans[channelId].Ranges)
            {
                field += $"\n{Utility.FormatTime.DiscordLong(range.Start)} - {Utility.FormatTime.DiscordLong(range.End)}";
                lines++;
            }
            fields.Add(field);
            if (lines > 10)
            {
                pages.Add(string.Join("\n\n", fields));
                fields = [titleString];
                lines = 1;
            }
        }
        if (fields.Count != 0) pages.Add(string.Join("\n\n", fields));

        var baseEmbed = new EmbedProperties()
            .WithTitle("Message Log Status")
            .WithColor(Globals.Colors.DarkGreen);

        (var embed, var actionRow) = EmbedPaginator.Register(new(baseEmbed, pages, 0, Context.Interaction));

        return new()
        {
            Embeds = [embed],
            Components = [actionRow]
        };

    }
}