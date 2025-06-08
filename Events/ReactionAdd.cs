using Events.Modules;
using NetCord.Gateway;
using NetCord.Hosting.Gateway;
using NetCord.Rest;

[GatewayEvent(nameof(GatewayClient.MessageReactionAdd))]
public class ReactionAddHandler : IGatewayEventHandler<MessageReactionAddEventArgs>
{
    private readonly RestClient restClient;

    public ReactionAddHandler(RestClient restClient) {
        this.restClient = restClient;
    }

    public async ValueTask HandleAsync(MessageReactionAddEventArgs args)
    {
        await StarboardManager.HandleReaction(args, restClient);
    }
}