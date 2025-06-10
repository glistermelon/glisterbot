using NetCord.Gateway;
using NetCord.Hosting.Gateway;

[GatewayEvent(nameof(GatewayClient.MessageCreate))]
public class MessageCreateHandler : ForwardingEventHandler<Message> { }