using NetCord.Rest;
using NetCord.Services;
using NetCord.Services.ApplicationCommands;

namespace GlisterBot.Commands;

[SlashCommand("rule34", "Rule34 commands!")]
[RequireNsfw<ApplicationCommandContext>("This command can only be used in an NSFW channel!")]
public partial class Rule34Commands : ApplicationCommandModule<ApplicationCommandContext>
{
    [SubSlashCommand("random", "Get a random image")]
    public async Task ExecuteRandom(
        [SlashCommandParameter(Name = "tags")] string tags
    ) {
        await new ImageBoardCommands(Context).ExecuteFindImage(ImageBoard.rule34, tags, "random");
    }

    [SubSlashCommand("best", "Get the highest-scoring image")]
    public async Task ExecuteBest(
        [SlashCommandParameter(Name = "tags")] string tags
    ) {
        await new ImageBoardCommands(Context).ExecuteFindImage(ImageBoard.rule34, tags, "score:desc");
    }

    [SubSlashCommand("worst", "Get the lowest-scoring image")]
    public async Task ExecuteWorst(
        [SlashCommandParameter(Name = "tags")] string tags
    ) {
        await new ImageBoardCommands(Context).ExecuteFindImage(ImageBoard.rule34, tags, "score:asc");
    }

    [SubSlashCommand("newest", "Get the newest image")]
    public async Task ExecuteNewest(
        [SlashCommandParameter(Name = "tags")] string tags
    ) {
        await new ImageBoardCommands(Context).ExecuteFindImage(ImageBoard.rule34, tags, "id:desc");
    }

    [SubSlashCommand("oldest", "Get the oldest image")]
    public async Task ExecuteOldest(
        [SlashCommandParameter(Name = "tags")] string tags
    ) {
        await new ImageBoardCommands(Context).ExecuteFindImage(ImageBoard.rule34, tags, "id:asc");
    }

    [SubSlashCommand("comment", "Get a random comment")]
    public async Task ExecuteComment()
    {
        await Context.Interaction.SendResponseAsync(InteractionCallback.DeferredMessage());

        var comment = await ImageBoard.rule34.GetRandomComment();

        if (comment == null) {
            await Context.Interaction.SendFollowupMessageAsync(
                new InteractionMessageProperties()
                {
                    Embeds = [
                        new EmbedProperties()
                            .WithColor(Globals.Colors.Red)
                            .WithDescription("Something went wrong.")
                    ]
                }
            );
            return;
        }

        EmbedProperties embed = new EmbedProperties()
            .WithColor(Globals.Colors.DarkGreen)
            .WithTitle($"Comment on Post #{comment.PostId}")
            .WithUrl(comment.PostUrl)
            .WithDescription($"**{comment.Author} said:** {comment.Content}");
        List<AttachmentProperties> attachments = [];

        if (comment.Image != null)
        {
            embed = embed.WithThumbnail(new("attachment://image." + comment.Image.FileExtension));
            attachments.Add(new("image." + comment.Image.FileExtension, comment.Image.DataStream));
        }

        await Context.Interaction.SendFollowupMessageAsync(
            new InteractionMessageProperties()
            {
                Embeds = [embed],
                Attachments = attachments
            }
        );
    }
}