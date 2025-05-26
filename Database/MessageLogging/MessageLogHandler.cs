using MessageLogging.DataTypes;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging;
using NetCord;
using NetCord.Rest;

namespace MessageLogging;

public class MessageLogHandler
{
    public required ILogger Logger { get; set; }
    private readonly DatabaseContext dbContext = new();

    public async Task<IntRangeSet> GetRecordedTime(ulong serverId)
    {
        dbContext.GetOrAddToDbServer(serverId);
        return new IntRangeSet(
            (await dbContext.Servers
                .Include(s => s.RecordedTimespans)
                .FirstAsync(s => s.Id == serverId))
                .RecordedTimespans
        );
    }

    public async Task<IntRangeSet> GetUnrecordedTime(ulong serverId)
    {
        IntRangeSet unrecorded = new(
            new IntRange(Globals.DISCORD_EPOCH, Utility.CurrentTimestamp())
        );
        IntRangeSet? recorded = await GetRecordedTime(serverId);
        if (recorded != null) unrecorded.Subtract(recorded);
        return unrecorded;
    }

    private async Task UpdateChannel(RestGuild server, TextChannel channel, IntRange timeRange)
    {
        dbContext.GetOrAddToDbServer(server.Id);
        var dbServer = await dbContext.Servers
            .Include(s => s.RecordedTimespans)
            .FirstAsync(s => s.Id == server.Id);

        int logged = 0;
        int totalLogged = 0;

        var transaction = dbContext.Database.BeginTransaction();

        await foreach (var message in channel.GetMessagesAsync(
            new()
            {
                BatchSize = 100,
                Direction = PaginationDirection.After,
                From = Utility.TimestampToSnowflake(timeRange.Start)
            }
        ))
        {
            var dbMessage = await dbContext.GetOrAddToDbMessage(message, channel, server.Id);

            logged++;
            totalLogged++;
            if (logged == 500 || dbMessage.Timestamp > timeRange.End)
            {
                try
                {
                    IntRangeSet recorded = await GetRecordedTime(server.Id);
                    recorded.Add(new IntRange(
                        timeRange.Start < dbMessage.Timestamp ? timeRange.Start : dbMessage.Timestamp,
                        dbMessage.Timestamp
                    ));
                    dbContext.TimeRanges.RemoveRange(dbServer.RecordedTimespans);
                    dbServer.RecordedTimespans = [.. recorded.Ranges.Select(r => new TimeRange(r))];
                    dbContext.SaveChanges();
                    transaction.Commit();
                }
                catch (Exception exception)
                {
                    transaction.Rollback();
                    Logger.LogError(exception, "An exception was thrown while logging messages.");
                    return;
                }
                transaction = dbContext.Database.BeginTransaction();
                Logger.LogInformation("\t\t\t[ML] [{}] {} messages logged", server.Id, totalLogged);
                if (dbMessage.Timestamp > timeRange.End) break;
                logged = 0;
            }
        }

        transaction.Commit();
    }

    public async Task UpdateServer(RestGuild server)
    {
        dbContext.GetOrAddToDbServer(server.Id);
        dbContext.SaveChanges();

        var unrecordedTime = await GetUnrecordedTime(server.Id);

        Logger.LogInformation("[ML] Updating logs for server {} '{}'", server.Id, server.Name);
        foreach (var channel in await server.GetChannelsAsync())
        {
            var dbChannel = dbContext.GetOrAddToDbChannel(channel.Id, server.Id);
            dbContext.SaveChanges();

            Logger.LogInformation("\t[ML] [{}] Logging channel: {} '{}'", server.Id, channel.Id, channel.Name);
            foreach (IntRange range in unrecordedTime.Ranges)
            {
                if (channel is not TextChannel) continue;
                Logger.LogInformation(
                    "\t\t[ML] [{}] Logging over time range {} ({}) - {} ({})",
                    server.Id,
                    range.Start,
                    Utility.FormatTime.Dashed(range.Start),
                    range.End,
                    Utility.FormatTime.Dashed(range.End)
                );
                await UpdateChannel(server, (TextChannel)channel, range);
            }
        }

    }
}