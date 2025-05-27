using System.Globalization;

public enum TimeUnit
{
    Day,
    Week,
    Month,
    Year
}

public static class TimeUnitExtension
{
    public static string ToSqlString(this TimeUnit timeUnit)
    {
        return timeUnit switch
        {
            TimeUnit.Day => "YYYY-MM-DD",
            TimeUnit.Week => "YYYY-WW",
            TimeUnit.Month => "YYYY-MM",
            TimeUnit.Year => "YYYY",
            _ => throw new Exception("Cannot convert unrecognized TimeUnit to SQL string")
        };
    }

    public static DateTime ParseString(this TimeUnit timeUnit, string str)
    {
        int[] nums;
        switch (timeUnit)
        {
            case TimeUnit.Day:
                return DateTime.ParseExact(str, "yyyy-MM-dd", CultureInfo.InvariantCulture);
            case TimeUnit.Week:
                nums = [.. str.Split("-").Select(int.Parse)];
                DateTime firstDay = new(nums[0], 1, 1);
                firstDay = firstDay.AddDays(-(int)firstDay.DayOfWeek);
                return firstDay.AddDays((nums[1] - 1) * 7);
            case TimeUnit.Month:
                nums = [.. str.Split("-").Select(int.Parse)];
                return new DateTime(nums[0], nums[1], 1);
            case TimeUnit.Year:
                return new DateTime(int.Parse(str), 1, 1);
            default:
                throw new Exception("Cannot use unrecognized TimeUnit to parse string");
        }
    }

    public static List<DateTime> GetAllTimesBetween(this TimeUnit timeUnit, DateTime startTime, DateTime endTime)
    {
        DateTime time = startTime;
        List<DateTime> output = [time];
        switch (timeUnit)
        {
            case TimeUnit.Day:
                while (time < endTime)
                {
                    time = time.AddDays(1);
                    output.Add(time);
                }
                break;
            case TimeUnit.Week:
                while (time < endTime)
                {
                    time = time.AddDays(7);
                    output.Add(time);
                }
                break;
            case TimeUnit.Month:
                while (time < endTime)
                {
                    time = time.AddMonths(1);
                    output.Add(time);
                }
                break;
            case TimeUnit.Year:
                while (time < endTime)
                {
                    time = time.AddYears(1);
                    output.Add(time);
                }
                break;
            default:
                throw new Exception("Cannot use unrecognized TimeUnit to parse string");
        }
        output.RemoveAt(output.Count - 1); // most likely a time after the present time
        return output;
    }
}