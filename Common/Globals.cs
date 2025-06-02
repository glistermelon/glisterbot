#pragma warning disable 8618

using ScottPlot;

public static class Globals
{
    public static readonly ulong DISCORD_EPOCH = 1420070400;
    public static Configuration Configuration { get; set; }

    public static string AlphabetLower { get; } = "abcdefghijklmnopqrstuvwxyz";

    public static class Colors
    {
        public static readonly NetCord.Color EmbedNone = new(0x22212c);
        public static readonly NetCord.Color DarkGreen = new(0x1f8b4c);
        public static readonly NetCord.Color Green = new(0x25db34);
        public static readonly NetCord.Color Red = new(0xdb2525);
        public static readonly NetCord.Color Orange = new(0xdb8325);
        public static class Graph
        {
            public static readonly ScottPlot.Color Blue = ScottPlot.Color.FromHex("#1f76b3");
            public static readonly ScottPlot.Color LightGrey = ScottPlot.Color.FromColor(System.Drawing.Color.FromArgb(51, 51, 51));
            public static readonly ScottPlot.Color DarkGrey = ScottPlot.Color.FromColor(System.Drawing.Color.FromArgb(38, 38, 38));
            public static readonly ScottPlot.Color LighterGrey = ScottPlot.Color.FromColor(System.Drawing.Color.FromArgb(58, 58, 58));
            public static readonly ScottPlot.Color Invisible = ScottPlot.Color.FromColor(System.Drawing.Color.Transparent);
        }
    }

    public static string GraphFontName { get; private set; }

    public static void initializePlotFont()
    {
        GraphFontName = "DejaVuSans";
        Fonts.AddFontFile(
            name: GraphFontName,
            path: $"{Configuration.StaticFilesDir}/DejaVuSans.ttf"
        );
    }
}