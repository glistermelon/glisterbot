using Microsoft.Extensions.Logging;
using NetCord;
using NetCord.Gateway;
using NetCord.Hosting.Gateway;

namespace Events;

[GatewayEvent(nameof(GatewayClient.GuildCreate))]
public class GuildCreateEventHandler(ILogger<GuildCreateEventHandler> logger) : IGatewayEventHandler<GuildCreateEventArgs>
{
    public async ValueTask HandleAsync(GuildCreateEventArgs args)
    {
        var server = args.Guild;
        if (server == null) return;

        foreach (var channel in await server.GetChannelsAsync())
        {
            if (channel.Id == Globals.RedditDeletionChannelId)
            {
                _ = Task.Run(() => new RedditDeletionListener((TextChannel)channel).ListenAsync());
                break;
            }
        }

        MessageLogHandler handler = new()
        {
            Logger = logger
        };
        logger.LogInformation("{}", server.Name);
        await handler.UpdateServer(server);
    }
}
