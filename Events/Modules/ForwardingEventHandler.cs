using NetCord.Hosting.Gateway;

public abstract class ForwardingEventHandler<T> : IGatewayEventHandler<T>
{
    public static List<EventListener<T>> PreEventListeners { get; set; } = [];
    public static List<EventListener<T>> PostEventListeners { get; set; } = [];

    public async ValueTask HandleAsync(T args)
    {
        EventListener<T>[] preEventListenersCopy = [.. PreEventListeners];
        await Task.WhenAll(preEventListenersCopy.Select(l => l.HandleAsync(args)));

        await HandleAsyncForward(args);

        EventListener<T>[] postEventListenersCopy = [.. PostEventListeners];
        await Task.WhenAll(postEventListenersCopy.Select(l => l.HandleAsync(args)));
    }

    public virtual ValueTask HandleAsyncForward(T args) => ValueTask.CompletedTask;
}