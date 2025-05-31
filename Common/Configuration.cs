#pragma warning disable 8618

public class Configuration
{
    public DiscordConfiguration Discord { get; set; }
    public DatabaseConfiguration Database { get; set; }
    public static string FileDir { get; set; } = "Files";
}

public class DiscordConfiguration
{
    public string Token { get; set; }
}

public class DatabaseConfiguration
{
    public string ConnectionString { get; set; }
}