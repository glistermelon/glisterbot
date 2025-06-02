namespace DatabaseObject;

public class WordbombFail
{
    public ulong Id { get; set; }
    public WordbombGame Game { get; set; }
    public string Phrase { get; set; }
    public ulong UserId { get; set; }
    public ulong Timestamp { get; set; }
    public ulong MessageId { get; set; }
    public ulong GameId { get; private set; }

    public void SyncIds()
    {
        GameId = Game.Id;
    }
}