namespace MessageLogging.DataTypes;

public record TimeRange
{
    public int Id { get; set; }
    public ulong Start { get; set; }
    public ulong End { get; set; }
    public Server Server { get; set; }
    public ulong ServerId { get; private set; }

    public TimeRange() { }  // for EF

    public TimeRange(IntRange range)
    {
        Start = range.Start;
        End = range.End;
    }
}