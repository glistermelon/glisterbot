using NetCord;

public static class Globals
{
    public static readonly ulong DISCORD_EPOCH = 1420070400;
    public static Configuration Configuration { get; set; }
    
    public static class Colors
    {
        public static readonly Color EmbedNone = new(0x22212c);
        public static readonly Color DarkGreen = new(0x1f8b4c);
    }

}