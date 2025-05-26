using NetCord.Services.ApplicationCommands;

namespace GlisterBot.Commands;

[SlashCommand("stats", "Server statistics!")]
public partial class Stats : ApplicationCommandModule<ApplicationCommandContext> { }