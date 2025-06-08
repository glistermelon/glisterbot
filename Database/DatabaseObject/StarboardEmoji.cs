namespace DatabaseObject;

public class StarboardEmoji
{
    public ulong Id { get; set; }
    public required Starboard Starboard { get; set; }
    public required string EmojiName { get; set; }
    public required ulong? EmojiId { get; set; }
    public ulong StarboardId { get; set; }

    public void SyncIds()
    {
        StarboardId = Starboard.Id;
    }
}