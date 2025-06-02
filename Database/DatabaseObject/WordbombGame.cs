namespace DatabaseObject;

public class WordbombGame
{
    public ulong Id { get; set; }
    public ulong StartTimestamp { get; set; }
    public ulong EndTimestamp { get; set; }
    public ulong ChannelId { get; set; }
    public ulong LastMessageId { get; set; }
    public ulong ServerId { get; set; }
    public ICollection<WordbombFail> Fails { get; set; } = [];
    public ICollection<WordbombPass> Passes { get; set; } = [];
    public ICollection<WordbombResult> Results { get; set; } = [];
}