#pragma warning disable 8618

using NetCord.Rest;
using Newtonsoft.Json;

public class DiscordServerJsonEntry
{
    public string tagIcon;
    public string tagText;
    // public int memberCount;
    // public string name;
    public string inviteShort;
    // public string inviteUrl;
    // public long serverId;
}

public class DiscordServerJsonWrapper
{
    public List<DiscordServerJsonEntry> data;
}

public class DiscordServerEntry
{
    public readonly ulong entryId;
    private static ulong entryIdCounter = 1;

    public readonly string tagIcon;
    public readonly string tagText;
    public readonly string inviteCode;

    public RestInvite? RestInvite { get; private set; } = null;
    private DateTimeOffset lastInviteUpdate = DateTimeOffset.MinValue;

    public DiscordServerEntry(DiscordServerJsonEntry jsonEntry)
    {
        entryId = entryIdCounter;
        entryIdCounter++;

        tagIcon = jsonEntry.tagIcon;
        tagText = jsonEntry.tagText;
        inviteCode = jsonEntry.inviteShort;
    }

    public async Task LoadRestInviteIfNecessary(RestClient restClient)
    {
        if ((DateTimeOffset.UtcNow - lastInviteUpdate).TotalDays >= 3)
        {
            try
            {
                RestInvite = await restClient.GetGuildInviteAsync(inviteCode, true, true);
            }
            catch (RestException) { }
            lastInviteUpdate = DateTimeOffset.UtcNow;
        }
    }
}

public class ServerListingHandler
{
    public static List<DiscordServerEntry> ServerEntries { get; private set; } = [];

    public static void Initialize()
    {
        string json = File.ReadAllText($"{Configuration.StaticFilesDir}/discord_tags/data.json");
        var jsonWrapper = JsonConvert.DeserializeObject<DiscordServerJsonWrapper>(json)
            ?? throw new Exception("Failed to initialize ServerListingHandler.serverEntries");
        ServerEntries = [.. jsonWrapper.data.Select(e => new DiscordServerEntry(e))];
    }
}