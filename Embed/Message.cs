using NetCord;
using NetCord.Rest;

public static class MessageEmbed
{
    public static (EmbedProperties, ActionRowProperties?) Create(
        string? content,
        string? username,
        string? avatar_url,
        string? jump_url,
        DateTimeOffset? timestamp
    )
    {
        var embed = new EmbedProperties();

        if (content != null) embed = embed.WithDescription(content);

        embed = embed.WithAuthor(new()
        {
            IconUrl = avatar_url,
            Name = username ?? "Unknown User"
        });

        if (timestamp != null) embed = embed.WithTimestamp(timestamp);

        ActionRowProperties? actionRow = jump_url == null ? null : [
            new LinkButtonProperties(jump_url, new EmojiProperties("\U0001f517"))
        ];

        return (embed, actionRow);
    }

    public static async Task<(EmbedProperties, ActionRowProperties?)> Create(
        DatabaseObject.Message dbMessage,
        RestClient? restClient
    )
    {
        User? user = restClient == null ? null : await restClient.GetUserAsync(dbMessage.UserId);
        return Create(
            content: dbMessage.Content,
            username: user == null ? dbMessage.User?.Username : user.Username,
            avatar_url: user == null ? null : user.GetAvatarUrl()?.ToString(),
            jump_url: dbMessage.JumpURL,
            timestamp: DateTimeOffset.FromUnixTimeSeconds((long)dbMessage.Timestamp)
        );
    }

    public static async Task<(EmbedProperties, ActionRowProperties?)> Create(
        RestMessage message,
        ulong guildId
    )
    {
        return Create(
            content: message.Content,
            username: message.Author.Username,
            avatar_url: message.Author.GetAvatarUrl()?.ToString(),
            jump_url: message.GetJumpUrl(guildId),
            timestamp: message.CreatedAt
        );
    }
}