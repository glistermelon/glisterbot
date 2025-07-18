#pragma warning disable 8618

public class Configuration
{
    public DiscordConfiguration Discord { get; set; }
    public DatabaseConfiguration Database { get; set; }
    public static string StaticFilesDir { get; set; } = "Files";
    public static string DynamicFilesDir { get; set; } = "Cache";
    public static int RedditDeletionListenerPort { get; set; }
}

public class DiscordConfiguration
{
    public string Token { get; set; }
}

public class DatabaseConfiguration
{
    public string ConnectionString { get; set; }
}