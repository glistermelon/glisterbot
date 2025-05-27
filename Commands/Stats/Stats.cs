using NetCord.Services.ApplicationCommands;

namespace GlisterBot.Commands;

[SlashCommand("stats", "Server statistics!")]
public partial class Stats : ApplicationCommandModule<ApplicationCommandContext>
{
    [SubSlashCommand("graph", "Stats with graphs!")]
    public partial class Graph : ApplicationCommandModule<ApplicationCommandContext> { }
}