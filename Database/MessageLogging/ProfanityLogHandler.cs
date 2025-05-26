using System.Threading.Tasks;
using MessageLogging.DataTypes;
using Microsoft.EntityFrameworkCore;
using Newtonsoft.Json;

namespace MessageLogging;

public class ServerUpdateQueryResult {
    public ulong UserId { get; set; }
    public string Phrase { get; set; }
    public int Count { get; set; }
}

public class UserProfanityInfo
{
    public Dictionary<string, int> TotalCounts { get; set; } = [];
    public Dictionary<string, Dictionary<string, int>> Counts { get; set; } = [];
}

public class ProfanityLogHandler(DatabaseContext dbContext)
{
    private static readonly ulong UPDATE_INTERVAL = 60 * 60 * 12; // 12 hours

    private static Dictionary<string, List<string>> profanity = [];

    public static void Initialize()
    {
        string json = File.ReadAllText("files/profanity.json");
        profanity = JsonConvert.DeserializeObject<Dictionary<string, List<string>>>(json)
            ?? throw new Exception("Failed to initialize ProfanityLogHandler.profanity");
    }

    public async Task UpdateUser(User dbUser, Server dbServer)
    {
        string regex_insert = string.Join("|", profanity.Values.SelectMany(l => l));
        string raw_sql =
            $@"WITH phrase_matches AS (
            SELECT
                ""USER_ID"",
                LOWER(match) AS phrase
            FROM (
                SELECT
                ""USER_ID"",
                unnest(
                    regexp_matches(
                    ""CONTENT"",
                    '\y(?:{regex_insert})\y',
                    'gi'
                    )
                ) AS match
                FROM ""MESSAGES""
                WHERE ""SERVER_ID""='{dbServer.Id}'
                    AND ""USER_ID""='{dbUser.Id}'
                )
            )
            SELECT
            ""USER_ID"",
            phrase,
            COUNT(*) AS count
            FROM phrase_matches
            GROUP BY ""USER_ID"", phrase
            ORDER BY ""USER_ID"", phrase;";

        ulong now = Utility.CurrentTimestamp();
        dbContext.RemoveRange(
            await dbContext.ProfanityRecords
                .Where(r => r.UserId == dbUser.Id)
                .ToListAsync()
        );
        await dbContext.ProfanityRecords.AddRangeAsync(
            (await dbContext.Database.SqlQueryRaw<ServerUpdateQueryResult>(raw_sql)
                .ToListAsync())
                .Select(r =>
                {
                    var record = new ProfanityRecord()
                    {
                        Server = dbServer,
                        User = dbUser,
                        Word = r.Phrase,
                        Count = r.Count,
                        LastUpdated = now
                    };
                    record.SyncIds();
                    return record;
                })
        );
        await dbContext.SaveChangesAsync();
    }

    public async Task UpdateUserIfNecessary(User dbUser, Server dbServer)
    {
        ProfanityRecord? record = await dbContext.ProfanityRecords.FirstOrDefaultAsync();
        if (record == null || Utility.CurrentTimestamp() - record.LastUpdated >= UPDATE_INTERVAL)
        {
            await UpdateUser(dbUser, dbServer);
        }
    }

    public async Task<UserProfanityInfo> GetProfanity(User dbUser, Server dbServer)
    {
        await UpdateUserIfNecessary(dbUser, dbServer);
        List<ProfanityRecord> records = await dbContext.ProfanityRecords
            .Where(r => r.UserId == dbUser.Id).ToListAsync()
            ?? throw new Exception($"Failed to get profanity records for user {dbUser.Id}");

        Dictionary<string, string> reverseMap = profanity
            .SelectMany(pair => pair.Value.Select(v => new { Key = v, Value = pair.Key }))
            .ToDictionary(pair => pair.Key, pair => pair.Value);
        Dictionary<string, int> totalCounts = [];
        Dictionary<string, Dictionary<string, int>> counts = [];
        foreach (var record in records)
        {
            string word = record.Word;
            string category = reverseMap[word];
            if (!counts.ContainsKey(category)) counts[category] = [];
            counts[category][word] = counts[category].GetValueOrDefault(word, 0) + record.Count;
            totalCounts[category] = totalCounts.GetValueOrDefault(category, 0) + record.Count;
        }
        return new UserProfanityInfo()
        {
            TotalCounts = totalCounts,
            Counts = counts
        };
    }

}