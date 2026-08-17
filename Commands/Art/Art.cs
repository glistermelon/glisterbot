using System.Net.Http.Json;
using NetCord;
using NetCord.Rest;
using NetCord.Services.ApplicationCommands;

namespace GlisterBot.Commands;

[SlashCommand("art", "Art commands!")]
public partial class ArtCommands : ApplicationCommandModule<ApplicationCommandContext>
{
    protected readonly HttpClient httpClient = new();

    private class Yotd
    {
        public required string Url { get; set; }
        public string? Source { get; set; }
        public string? Content { get; set; }
        public string? Ship { get; set; }
    }

    [SubSlashCommand("yotd", "Yuri of the Day")]
    public async Task ExecuteYotd(
        [SlashCommandParameter(Name = "month")] int month,
        [SlashCommandParameter(Name = "day")] int day
    )
    {
        await Context.Interaction.SendResponseAsync(InteractionCallback.DeferredMessage());

        String url = $"https://glisterbyte.com/yuri/get?date=2026-{month}-{day}";
        Yotd? yotd;
        try
        {
            yotd = await httpClient.GetFromJsonAsync<Yotd>(url);
        }
        catch (HttpRequestException)
        {
            yotd = null;
        }

        if (yotd == null) {
            await Context.Interaction.SendFollowupMessageAsync(
                new InteractionMessageProperties()
                {
                    Embeds = [
                        new EmbedProperties()
                            .WithColor(Globals.Colors.Red)
                            .WithDescription($"No daily yuri was found for {month}/{day}!")
                    ]
                }
            );
            return;
        }

        List<string> descriptionLines = [];
        if (yotd.Ship != null) descriptionLines.Add(yotd.Ship);
        if (yotd.Content != null) descriptionLines.Add($"From *{yotd.Content}*");
        if (yotd.Source != null) descriptionLines.Add($"[Source]({yotd.Source})");
        string description = string.Join("\n", descriptionLines);

        await Context.Interaction.SendFollowupMessageAsync(
            new InteractionMessageProperties()
            {
                Embeds = [
                    new EmbedProperties()
                        .WithColor(Globals.Colors.DarkGreen)
                        .WithTitle($"Daily Yuri #{new DateTime(2026, month, day).DayOfYear} ({month}/{day})")
                        .WithUrl($"https://glisterbyte.com/yuri/2026-{month}-{day}")
                        .WithDescription(description)
                        .WithImage("https://glisterbyte.com" + yotd.Url)
                ]
            }
        );
    
    }

    [SubSlashCommand("random", "Get a random image")]
    public async Task ExecuteRandomWrapper(
        [SlashCommandParameter(Name = "tags")] string tags
    ) {
        await new ImageBoardCommands(Context).ExecuteFindImage(ImageBoard.gelbooru, tags, "random");
    }


    [SubSlashCommand("best", "Get the highest-scoring image")]
    public async Task ExecuteBest(
        [SlashCommandParameter(Name = "tags")] string tags
    ) {
        await new ImageBoardCommands(Context).ExecuteFindImage(ImageBoard.gelbooru, tags, "score:desc");
    }

    [SubSlashCommand("worst", "Get the lowest-scoring image")]
    public async Task ExecuteWorst(
        [SlashCommandParameter(Name = "tags")] string tags
    ) {
        await new ImageBoardCommands(Context).ExecuteFindImage(ImageBoard.gelbooru, tags, "score:asc");
    }

    [SubSlashCommand("newest", "Get the newest image")]
    public async Task ExecuteNewest(
        [SlashCommandParameter(Name = "tags")] string tags
    ) {
        await new ImageBoardCommands(Context).ExecuteFindImage(ImageBoard.gelbooru, tags, "id:desc");
    }

    [SubSlashCommand("oldest", "Get the oldest image")]
    public async Task ExecuteOldest(
        [SlashCommandParameter(Name = "tags")] string tags
    ) {
        await new ImageBoardCommands(Context).ExecuteFindImage(ImageBoard.gelbooru, tags, "id:asc");
    }

}