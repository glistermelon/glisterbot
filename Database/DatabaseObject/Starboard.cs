namespace DatabaseObject;

public class Starboard
{
    public ulong Id { get; set; }
    public ulong ServerId { get; set; }
    public ulong ChannelId { get; set; }
    public ulong? RoleId { get; set; }
    public string? EmojiName { get; set; }
    public ulong? EmojiId { get; set; }
    public int MinimumReactionCount { get; set; }
    public ICollection<StarboardEmoji> AllEmojis { get; set; } = [];
    public ICollection<StarboardPin> Pins { get; set; } = [];
}