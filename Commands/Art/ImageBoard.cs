using NetCord;
using NetCord.Rest;
using NetCord.Services.ApplicationCommands;

namespace GlisterBot.Commands;

public partial class ImageBoardCommands(ApplicationCommandContext context)
{
    public async Task ExecuteFindImage(ImageBoard board, string tags, string sort)
    {
        await context.Interaction.SendResponseAsync(InteractionCallback.DeferredMessage());

        if (!(context.Channel is TextGuildChannel guildTextChannel && guildTextChannel.Nsfw))
        {
            tags += " rating:g";
        }

        ImageBoard.Post? post = (await board.GetPosts(tags + " sort:" + sort)).FirstOrDefault();

        if (post == null) {
            await context.Interaction.SendFollowupMessageAsync(
                new InteractionMessageProperties()
                    {
                        Embeds = [
                            new EmbedProperties()
                                .WithColor(Globals.Colors.Red)
                                .WithTitle("No images found.")
                                .WithDescription($"""
                                Remember to separate tags with spaces. Instead of a space in a tag, use an underscore, like this: `hakurei_reimu kirisame_marisa`.
                                For Japanese character names, remember to put the family name first (usually).
                                Note that the following tags are blacklisted: `{ImageBoard.tagBlacklist}`
                                """)
                        ]
                    }
            );
            return;
        }

        var image = await post.GetPreviewImage();
        await context.Interaction.SendFollowupMessageAsync(
            new InteractionMessageProperties()
            {
                Embeds = [
                    new EmbedProperties()
                        .WithTitle(tags)
                        .WithUrl(post.GetUrl())
                        .WithAuthor(new EmbedAuthorProperties().WithName(context.User.Username).WithIconUrl(context.User.GetAvatarUrl()?.ToString()))
                        .WithImage("attachment://image." + image.FileExtension)
                        .WithColor(Globals.Colors.DarkGreen)
                ],
                Attachments = [new AttachmentProperties("image." + image.FileExtension, image.DataStream)]
            }
        );
    }
}