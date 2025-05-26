// inclusive [Start, End]

using MessageLogging.DataTypes;

public enum OverlapStatus
{
    Disjoint,
    Left,
    Right,
    Superset,
    Subset
}

public class IntRange(ulong start, ulong end)
{
    public ulong Start { get; set; } = start;
    public ulong End { get; set; } = end;

    public IntRange(TimeRange timeRange) : this(timeRange.Start, timeRange.End) { }

    // other is [OverlapStatus] of this
    public OverlapStatus Intersect(IntRange other)
    {
        if (Start > other.End || End < other.Start) return OverlapStatus.Disjoint;
        if (Start >= other.Start && End > other.End) return OverlapStatus.Left;
        if (Start < other.Start && End <= other.End) return OverlapStatus.Right;
        if (Start >= other.Start && End <= other.End) return OverlapStatus.Superset;
        return OverlapStatus.Subset;
    }
    
    public void Add(IntRange other)
    {
        switch (Intersect(other))
        {
            case OverlapStatus.Disjoint:
                throw new Exception("Attempt to add disjoint IntRange.");
            case OverlapStatus.Left:
                Start = other.Start;
                break;
            case OverlapStatus.Right:
                End = other.End;
                break;
            case OverlapStatus.Superset:
                Start = other.Start;
                End = other.End;
                break;
            case OverlapStatus.Subset:
                break;
        }
    }

    public List<IntRange> Subtract(IntRange other)
    {
        return Intersect(other) switch
        {
            OverlapStatus.Disjoint => [this],
            OverlapStatus.Left => [new IntRange(other.End + 1, End)],
            OverlapStatus.Right => [new IntRange(Start, other.Start - 1)],
            OverlapStatus.Superset => [],
            OverlapStatus.Subset => [
                new IntRange(Start, other.Start - 1),
                new IntRange(other.End + 1, End)
            ],
            _ => throw new Exception("IntRange.Subtract exception that should never happen"),
        };
    }
}