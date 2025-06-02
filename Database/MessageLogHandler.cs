using DatabaseObject;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Storage;
using Microsoft.Extensions.Logging;
using NetCord;
using NetCord.Rest;

public class MessageLogHandler
{
    public required ILogger Logger { get; set; }
    private readonly DatabaseContext dbContext = new();

    public async Task<IntRangeSet> GetRecordedTime(ulong channelId)
    {
        return new IntRangeSet(
            (await dbContext.Channels
                .Include(c => c.RecordedTimespans)
                .FirstAsync(c => c.Id == channelId))
                .RecordedTimespans
        );
    }

    public async Task<IntRangeSet> GetUnrecordedTime(ulong channelId)
    {
        IntRangeSet unrecorded = new(
            new IntRange(Globals.DISCORD_EPOCH, Utility.CurrentTimestamp())
        );
        IntRangeSet? recorded = await GetRecordedTime(channelId);
        if (recorded != null) unrecorded.Subtract(recorded);
        return unrecorded;
    }

    private async Task CommitUpdatedData(
        ulong latestTimestamp,
        DatabaseObject.Channel dbChannel,
        IntRange timeRange,
        IDbContextTransaction transaction
    ) {
        try
        {
            IntRangeSet recorded = await GetRecordedTime(dbChannel.Id);
            recorded.Add(new IntRange(
                timeRange.Start < latestTimestamp ? timeRange.Start : latestTimestamp,
                latestTimestamp
            ));
            dbContext.TimeRanges.RemoveRange(dbChannel.RecordedTimespans);
            dbChannel.RecordedTimespans = [.. recorded.Ranges.Select(r => new TimeRange(r))];
            await dbContext.SaveChangesAsync();
            await transaction.CommitAsync();
        }
        catch
        {
            await transaction.RollbackAsync();
            throw;
        }
    }

    private async Task UpdateChannel(RestGuild server, TextChannel channel, IntRange timeRange)
    {
        dbContext.GetOrAddToDbChannel(channel.Id, server.Id);
        var dbChannel = await dbContext.Channels
            .Include(c => c.RecordedTimespans)
            .FirstAsync(c => c.Id == channel.Id);

        int logged = 0;
        int totalLogged = 0;
        ulong latestTimestamp = 0;

        var transaction = await dbContext.Database.BeginTransactionAsync();

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
            latestTimestamp = dbMessage.Timestamp;

            logged++;
            totalLogged++;
            if (logged == 500 || latestTimestamp > timeRange.End)
            {
                await CommitUpdatedData(latestTimestamp, dbChannel, timeRange, transaction);
                transaction = await dbContext.Database.BeginTransactionAsync();
                Logger.LogInformation("\t\t\t[ML] [{}] {} messages logged", server.Id, totalLogged);
                logged = 0;
                if (latestTimestamp > timeRange.End) break;
            }
        }

        if (logged != 0)
        {
            await CommitUpdatedData(latestTimestamp, dbChannel, timeRange, transaction);
            Logger.LogInformation("\t\t\t[ML] [{}] {} messages logged", server.Id, totalLogged);
        }
        else await transaction.RollbackAsync();

    }

    public async Task UpdateServer(RestGuild server)
    {
        dbContext.GetOrAddToDbServer(server.Id);
        dbContext.SaveChanges();

        Logger.LogInformation("[ML] Updating logs for server {} '{}'", server.Id, server.Name);
        foreach (var channel in await server.GetChannelsAsync())
        {
            var dbChannel = dbContext.GetOrAddToDbChannel(channel.Id, server.Id);
            dbContext.SaveChanges();

            var unrecordedTime = await GetUnrecordedTime(dbChannel.Id);

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