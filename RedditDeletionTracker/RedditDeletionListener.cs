#pragma warning disable 8618

using System.Net;
using System.Net.Sockets;
using MessagePack;
using NetCord;
using NetCord.Rest;

[MessagePackObject]
public class RedditDeletionMessage
{
    [Key("title")]
    public string Title { get; set; }

    [Key("desc")]
    public string Description { get; set; }

    [Key("timestamp")]
    public long Timestamp { get; set; }

    [Key("post_url")]
    public string PostUrl { get; set; }

    [Key("image_url")]
    public string? ImageUrl { get; set; }
}

public class RedditDeletionListener(TextChannel outputChannel)
{
    public async Task ListenAsync()
    {
        var listener = new TcpListener(IPAddress.Loopback, Configuration.RedditDeletionListenerPort);
        listener.Start();
        while (true)
        {
            var client = await listener.AcceptTcpClientAsync();
            using var stream = client.GetStream();
            try
            {
                while (true)
                {
                    byte[] lengthBytes = new byte[4];
                    await stream.ReadExactlyAsync(lengthBytes, 0, 4);
                    int length = BitConverter.ToInt32([.. lengthBytes.Reverse()], 0);

                    byte[] rawData = new byte[length];
                    await stream.ReadExactlyAsync(rawData, 0, length);

                    var message = MessagePackSerializer.Deserialize<RedditDeletionMessage>(rawData);

                    var embed = new EmbedProperties()
                        .WithTitle(message.Title)
                        .WithColor(Globals.Colors.DarkGreen)
                        .WithDescription(message.Description)
                        .WithTimestamp(DateTimeOffset.FromUnixTimeSeconds(message.Timestamp))
                        .WithUrl(message.PostUrl);
                    if (message.ImageUrl != null)
                    {
                        embed = embed.WithImage(new EmbedImageProperties(message.ImageUrl));
                    }
                    await outputChannel.SendMessageAsync(new MessageProperties().WithEmbeds([embed]));
                }
            }
            catch (IOException) { }
        }
    }
}