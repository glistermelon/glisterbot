namespace MessageLogging.DataTypes;

public class Channel
{
    public ulong Id { get; set; }
    public required Server Server { get; set; }
    public ulong ServerId { get; private set; }
    public void SyncIds()
    {
        ServerId = Server.Id;
    }
}