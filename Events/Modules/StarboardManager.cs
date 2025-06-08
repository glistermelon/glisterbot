using Microsoft.EntityFrameworkCore;
using NetCord;
using NetCord.Gateway;
using NetCord.Rest;

namespace Events.Modules;

public static class StarboardManager
{
    public static async Task HandleReaction(MessageReactionAddEventArgs args, RestClient restClient)
    {
        if (args.GuildId == null) return;
        var dbContext = new DatabaseContext();
        List<DatabaseObject.Starboard> dbStarboards = await dbContext.Starboards
            .Where(b => b.ServerId == args.GuildId)
            .Include(b => b.AllEmojis)
            .Include(b => b.Pins)
            .ToListAsync();
        dbStarboards.RemoveAll(b => !b.AllEmojis.Any(e => e.Matches(args.Emoji)));
        foreach (var dbStarboard in dbStarboards)
        {
            if (dbStarboard.ChannelId == args.ChannelId) continue;
            var message = await restClient.GetMessageAsync(args.ChannelId, args.MessageId);
            if (message == null) continue;
            if (
                (message.Reactions.FirstOrDefault(r => dbStarboard.AllEmojis.Any(e => e.Matches(r.Emoji)))?.Count ?? 0)
                    < dbStarboard.MinimumReactionCount
            ) continue;
            if (await dbStarboard.Pin(message, (ulong)args.GuildId, restClient))
            {
                dbContext.SaveChanges();
            }
        }
    }
}

public static class DbStarboardExtensions
{
    public static async Task<bool> Pin(
        this DatabaseObject.Starboard starboard,
        RestMessage message,
        ulong guildId,
        RestClient restClient
    )
    {
        if (starboard.Pins.Any(p => p.MessageId == message.Id)) return false;

        (var embed, var actionRow) = MessageEmbed.Create(message, guildId);

        string? imageUrl = message.Attachments
            .FirstOrDefault(a => Globals.MediaTypes.ImageTypes.Contains(a.ContentType))
            ?.ProxyUrl;
        if (imageUrl != null) embed = embed.WithImage(imageUrl);

        var msgProps = new MessageProperties()
        {
            Embeds = [embed],
            Components = actionRow == null ? [] : [actionRow]
        };
        if (starboard.RoleId != null)
        {
            msgProps = msgProps.WithContent($"<@&{starboard.RoleId}>");
        }

        var sentMessage = await restClient.SendMessageAsync(starboard.ChannelId, msgProps);

        if (starboard.EmojiName != null)
        {
            ReactionEmojiProperties reaction = starboard.EmojiId == null
                ? new(starboard.EmojiName)
                : new(starboard.EmojiName, (ulong)starboard.EmojiId);
            await restClient.AddMessageReactionAsync(
                sentMessage.ChannelId, sentMessage.Id, reaction
            );
        }

        var dbPin = new DatabaseObject.StarboardPin()
        {
            Starboard = starboard,
            MessageId = message.Id
        };
        dbPin.SyncIds();
        starboard.Pins.Add(dbPin);

        return true;
    }
}

public static class DbStarboardEmojiExtensions {
    public static bool Matches(
        this DatabaseObject.StarboardEmoji dbEmoji,
        MessageReactionEmoji reactionEmoji
    )
    {
        return dbEmoji.EmojiName == reactionEmoji.Name && dbEmoji.EmojiId == reactionEmoji.Id;
    }
}