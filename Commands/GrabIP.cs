using NetCord;
using NetCord.Rest;
using NetCord.Services.ApplicationCommands;

namespace GlisterBot.Commands;

public class GrabIP : ApplicationCommandModule<ApplicationCommandContext>
{
    [SlashCommand("grab-ip", "Very real IP grabber")]
    public static InteractionMessageProperties Execute(
        [SlashCommandParameter(Name = "user")] User user
    )
    {
        var rng = new Random(129079283 * (int)user.Id * DateTime.Now.Month);
        string ip = string.Join(".", Enumerable.Range(0, 4).Select(_ => rng.Next(256)));

        return new()
        {
            Content = $"<@{user.Id}>'s IP address is {ip}"
        };

    }
}


