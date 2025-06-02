namespace DatabaseObject;

public class WordbombResult
{
    public ulong Id { get; set; }
    public WordbombGame Game { get; set; }
    public ulong UserId { get; set; }
    public bool Victory { get; set; }
    public int FailCount { get; set; }
    public int PassCount { get; set; }
    public ulong GameId { get; private set; }
    public void SyncIds()
    {
        GameId = Game.Id;
    }
}