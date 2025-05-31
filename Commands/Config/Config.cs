using NetCord.Services.ApplicationCommands;

namespace GlisterBot.Commands;

[SlashCommand("config", "Glisterbot configuration for this server")]
public partial class Config : ApplicationCommandModule<ApplicationCommandContext>
{
    [SubSlashCommand("alt-account", "Configuration of alt accounts")]
    public partial class AltAccount : ApplicationCommandModule<ApplicationCommandContext> { }
}