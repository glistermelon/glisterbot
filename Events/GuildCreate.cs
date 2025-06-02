using Microsoft.Extensions.Logging;
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
        MessageLogHandler handler = new()
        {
            Logger = logger
        };
        logger.LogInformation("{}", server.Name);
        await handler.UpdateServer(server);
    }
}