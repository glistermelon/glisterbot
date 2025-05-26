using Microsoft.EntityFrameworkCore;
using NetCord;
using NetCord.Rest;
using NetCord.Services.ApplicationCommands;

namespace GlisterBot.Commands;

public partial class Stats
{
    [SubSlashCommand("mentions", "See who someone is most obsessed with")]
    public async Task<InteractionMessageProperties> ExecuteMentions(
        [SlashCommandParameter(Name = "user")] User user
    )
    {
        var dbContext = new DatabaseContext();
        var mentions = await dbContext.Messages
            .Where(m => m.UserId == user.Id)
            .SelectMany(m => m.UsersMentioned)
            .GroupBy(u => u.Id)
            .Select(g => new { UserId = g.Key, Count = g.Count() })
            .ToListAsync();

        var server = Context.Guild;
        if (server == null) return "";
        var serverUsers = await server.GetUsersAsync().Select(u => u.Id).ToArrayAsync();
        mentions.RemoveAll(g => !serverUsers.Contains(g.UserId));

        mentions.Sort((a, b) => b.Count - a.Count);

        List<string> descLines = [];
        foreach (var datum in mentions)
        {
            descLines.Add($"<@{datum.UserId}> - **{datum.Count}** mentions");
        }

        var embed = new EmbedProperties()
            .WithTitle($"Who has {user.Username} mentioned most?")
            .WithColor(Globals.Colors.DarkGreen);

        List<string> pages = [.. descLines.Chunk(15).Select(c => string.Join("\n", c))];
        if (pages.Count == 0)
        {
            pages.Add("*This guy has literally never mentioned anyone!*");
        }

        (embed, var actionRow) = EmbedPaginator.Register(new(embed, pages, 0, Context.Interaction));

        return new()
        {
            Embeds = [embed],
            Components = [actionRow]
        };

    }
}