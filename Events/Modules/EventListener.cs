public class EventListener<T>
{
    private bool active = false;
    private readonly Func<T, EventListener<T>, Task> callback;
    private readonly SemaphoreSlim semaphore = new(1, 1);
    private readonly bool preEvent;
    private CancellationTokenSource? cancel = null;

    public EventListener(Func<T, EventListener<T>, Task> callback, bool preEvent = false)
    {
        this.callback = callback;
        this.preEvent = preEvent;
    }

    public async Task HandleAsync(T args)
    {
        await semaphore.WaitAsync();
        if (active) await callback(args, this);
        semaphore.Release();
    }

    public void Activate()
    {
        active = true;
        AttachListener();
    }

    public void Deactivate()
    {
        active = false;
        RemoveListener();
        cancel?.Cancel();
    }

    public async Task WaitForDeactivation(int timeoutSeconds)
    {
        cancel = new();
        try { await Task.Delay(1000 * timeoutSeconds, cancel.Token); }
        catch (TaskCanceledException) { }
        if (active) Deactivate();
    }

    private void AttachListener()
    {
        if (preEvent) ForwardingEventHandler<T>.PreEventListeners.Add(this);
        else ForwardingEventHandler<T>.PostEventListeners.Add(this);
    }

    private void RemoveListener()
    {
        if (preEvent) ForwardingEventHandler<T>.PreEventListeners.Remove(this);
        else ForwardingEventHandler<T>.PostEventListeners.Remove(this);
    }
}