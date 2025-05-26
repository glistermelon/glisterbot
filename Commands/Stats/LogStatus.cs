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
        IntRangeSet timespans = new(
            await new DatabaseContext().TimeRanges.Where(t => t.ServerId == serverId).ToListAsync()
        );
        string desc = "**Recorded Times**\n" + string.Join("\n", timespans.Ranges.Select(
            r => $"{Utility.FormatTime.DiscordLong(r.Start)} - {Utility.FormatTime.DiscordLong(r.End)}"
        ));

        var embed = new EmbedProperties()
            .WithTitle("Message Log Status")
            .WithDescription(desc)
            .WithColor(Globals.Colors.DarkGreen);

        return new()
        {
            Embeds = [embed]
        };

    }
}