namespace DatabaseObject;

public class Attachment
{
    public int Id { get; set; }
    public required Message Message { get; set; }
    public required string ContentType { get; set; }
    public required string SourceURL { get; set; }
    public required string ProxyURL { get; set; }
    public int Size { get; set; }
    public ulong MessageId { get; private set; }
    public void SyncIds()
    {
        MessageId = Message.Id;
    }
}