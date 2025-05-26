using MessageLogging.DataTypes;

public class IntRangeSet
{
    public List<IntRange> Ranges { get; }

    public IntRangeSet()
    {
        Ranges = [];
    }

    public IntRangeSet(IntRange range)
    {
        Ranges = [range];
    }

    public IntRangeSet(IntRangeSet rangeSet)
    {
        Ranges = [.. rangeSet.Ranges];
    }

    public IntRangeSet(IEnumerable<IntRange> ranges)
    {
        Ranges = [];
        Add(ranges);
    }

    public IntRangeSet(TimeRange timeRange)
    {
        Ranges = [new IntRange(timeRange)];
    }

    public IntRangeSet(IEnumerable<TimeRange> timeRanges)
    {
        Ranges = [];
        Add(timeRanges.Select(r => new IntRange(r)));
    }

    public void Add(IntRange range)
    {
        if (Ranges.Any(r => range.Intersect(r) == OverlapStatus.Superset)) return;
        Ranges.RemoveAll(r => range.Intersect(r) == OverlapStatus.Subset);
        IntRange? left = Ranges.FindAndRemoveFirst(r => range.Intersect(r) == OverlapStatus.Left);
        IntRange? right = Ranges.FindAndRemoveFirst(r => range.Intersect(r) == OverlapStatus.Right);
        range = new IntRange(
            left == null ? range.Start : left.Start,
            right == null ? range.End : right.End
        );
        // [a, b] + [b + 1, c], etc, should be joined into one range
        left = Ranges.FindAndRemoveFirst(r => r.End + 1 == range.Start);
        right = Ranges.FindAndRemoveFirst(r => r.Start - 1 == range.End);
        if (left != null) range.Start = left.Start;
        if (right != null) range.End = right.End;
        Ranges.Add(range);
    }

    public void Add(IEnumerable<IntRange> ranges)
    {
        foreach (var range in ranges) Add(range);
    }

    public void Add(IntRangeSet rangeSet)
    {
        foreach (var range in rangeSet.Ranges) Add(range);
    }

    public void Subtract(IntRange range)
    {
        Ranges.RemoveAll(r => range.Intersect(r) == OverlapStatus.Subset);
        foreach (IntRange other in Ranges.Where(r => range.Intersect(r) != OverlapStatus.Disjoint).ToArray())
        {
            Ranges.Remove(other);
            Ranges.AddRange(other.Subtract(range));
        }
    }

    public void Subtract(IEnumerable<IntRange> ranges)
    {
        foreach (var range in ranges) Subtract(range);
    }

    public void Subtract(IntRangeSet rangeSet)
    {
        foreach (var range in rangeSet.Ranges) Subtract(range);
    }
}