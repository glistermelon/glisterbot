public static class ChannelManager
{
    private static readonly Dictionary<ulong, (Task, CancellationTokenSource)> tasks = [];

    public static bool ChannelIsBusy(ulong channelId)
    {
        return tasks.ContainsKey(channelId);
    }

    public static void MarkAsBusy(ulong channelId, TimeSpan timeout, Func<Task>? callback = null)
    {
        MarkAsFree(channelId);
        var cancel = new CancellationTokenSource();
        tasks[channelId] = (TimeoutTask(channelId, timeout, cancel, callback), cancel);
    }

    public static async Task TimeoutTask(
        ulong channelId, TimeSpan timeout, CancellationTokenSource cancel, Func<Task>? callback
    )
    {
        try
        {
            await Task.Delay(timeout, cancel.Token);
            tasks.Remove(channelId);
            if (callback != null) await callback();
        }
        catch (TaskCanceledException) { }
    }

    public static void MarkAsFree(ulong channelId)
    {
        if (tasks.TryGetValue(channelId, out var value))
        {
            value.Item2.Cancel();
            tasks.Remove(channelId);
        }
    }
}