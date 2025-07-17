using NetCord.Services.ApplicationCommands;

namespace GlisterBot.Commands;

public class WhoSaidItMost : ApplicationCommandModule<ApplicationCommandContext>
{
    [SlashCommand("who-said-it-most", "See what users have said a phrase the most.")]
    public async Task ExecutePhraseLeaderboard(string phrase)
    {
        await Stats.ExecutePhraseLeaderboardStatic(phrase, Context);
    }
}