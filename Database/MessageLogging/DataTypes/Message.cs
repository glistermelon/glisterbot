namespace MessageLogging.DataTypes;

public class Message
{
    public ulong Id { get; set; }
    public required string Content { get; set; }
    public required Server Server { get; set; }
    public ulong Timestamp { get; set; }
    public required User User { get; set; }
    public required Channel Channel { get; set; }
    public required string JumpURL { get; set; }
    public ICollection<Reaction> Reactions { get; set; } = [];
    public bool MentionsEveryone { get; set; }
    public ICollection<ulong> RolesMentioned { get; set; } = [];
    public ICollection<User> UsersMentioned { get; set; } = [];
    public Message? ReplyingTo { get; set; }
    public ICollection<Attachment> Attachments { get; set; } = [];

    // db columns for navigation properties
    public ulong ServerId { get; private set; }
    public ulong UserId { get; private set; }
    public ulong ChannelId { get; private set; }
    public ulong? ReplyingToId { get; private set; }
    public void SyncIds()
    {
        ServerId = Server.Id;
        UserId = User.Id;
        ChannelId = Channel.Id;
        ReplyingToId = ReplyingTo?.Id;
    }
}