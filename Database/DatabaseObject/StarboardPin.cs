namespace DatabaseObject;

public class StarboardPin
{
    public ulong Id { get; set; }
    public required Starboard Starboard { get; set; }
    public ulong MessageId { get; set; }
    public ulong StarboardId { get; set; }

    public void SyncIds()
    {
        StarboardId = Starboard.Id;
    }
}