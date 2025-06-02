using NetCord.Gateway;
using NetCord.Hosting.Gateway;

[GatewayEvent(nameof(GatewayClient.MessageCreate))]
public class MessageCreateHandler : IGatewayEventHandler<Message>
{
    public static List<Func<Message, Task>> Handlers { get; } = [];

    public async ValueTask HandleAsync(Message message)
    {
        var copy = Handlers.ToArray();
        await Task.WhenAll(copy.Select(handler => handler(message)));
    }
}