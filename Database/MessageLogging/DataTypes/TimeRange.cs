#pragma warning disable 8618

namespace MessageLogging.DataTypes;

public record TimeRange
{
    public int Id { get; set; }
    public ulong Start { get; set; }
    public ulong End { get; set; }
    public Channel Channel { get; set; }
    public ulong ChannelId { get; private set; }

    public TimeRange() { }  // for EF

    public TimeRange(IntRange range)
    {
        Start = range.Start;
        End = range.End;
    }
}