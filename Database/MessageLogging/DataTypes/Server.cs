namespace MessageLogging.DataTypes;

public class Server
{
    public ulong Id { get; set; }
    public List<TimeRange> RecordedTimespans { get; set; } = [];
}