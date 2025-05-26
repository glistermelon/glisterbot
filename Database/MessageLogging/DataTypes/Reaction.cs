namespace MessageLogging.DataTypes;

public class Reaction
{
    public int Id { get; set; }
    public required Server Server { get; set; }
    public required Message Message { get; set; }
    public required User User { get; set; }
    public required string? EmojiName { get; set; }
    public required ulong? ServerEmojiId { get; set; }

    // db columns for navigation properties
    public ulong ServerId { get; private set; }
    public ulong MessageId { get; private set; }
    public ulong UserId { get; private set; }
    public void SyncIds()
    {
        ServerId = Server.Id;
        MessageId = Message.Id;
        UserId = User.Id;
    }

    public bool Equals(Reaction other)
    {
        return Message.Id == other.Message.Id
            && User.Id == other.User.Id
            && EmojiName == other.EmojiName
            && ServerEmojiId == other.ServerEmojiId;
    }

    public bool Equals(ulong messageId, ulong userId, NetCord.MessageReactionEmoji emoji)
    {
        return Message.Id == messageId
            && User.Id == userId
            && EmojiName == emoji.Name
            && ServerEmojiId == emoji.Id;
    }
}