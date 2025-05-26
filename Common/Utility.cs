public static class Utility
{
    public static ulong CurrentTimestamp()
        => (ulong)DateTimeOffset.UtcNow.ToUnixTimeSeconds();

    public static class FormatTime
    {
        public static string Dashed(ulong timestamp)
            => DateTimeOffset.FromUnixTimeSeconds((long)timestamp).DateTime.ToString("dd-MM-yyyy");
        public static string Human(ulong timestamp)
            => DateTimeOffset.FromUnixTimeSeconds((long)timestamp).DateTime.ToString("d MMM yyyy");
        public static string DiscordLong(ulong timestamp)
            => $"<t:{timestamp}:D>";
    }

    public static ulong TimestampToSnowflake(ulong timestamp)
        => ((timestamp - Globals.DISCORD_EPOCH) * 1000) << 22;

}