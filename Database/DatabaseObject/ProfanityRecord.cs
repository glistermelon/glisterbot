namespace DatabaseObject;

public class ProfanityRecord
{
    public ulong Id { get; set; }
    public required Server Server { get; set; }
    public required User User { get; set; }
    public required string Word { get; set; }
    public required int Count { get; set; }
    public required ulong LastUpdated { get; set; }
    public ulong ServerId { get; private set; }
    public ulong UserId { get; private set; }
    public void SyncIds()
    {
        ServerId = Server.Id;
        UserId = User.Id;
    }
}