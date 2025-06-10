using NetCord;
using NetCord.Rest;
using NetCord.Gateway;

namespace GlisterBot.Commands.Wordbomb;

public class WordbombPlayer
{
    public User User { get; set; }
    public int Lives { get; set; }
    public List<char> RemainingLetters { get; } = [];

    public WordbombPlayer(User user, int lives)
    {
        User = user;
        Lives = lives;
        ResetLetters();
    }

    public void ResetLetters()
    {
        RemainingLetters.Clear(); // should not be necessary but just in case
        RemainingLetters.AddRange(Globals.AlphabetLower);
    }
}

public class WordbombGame(
    WordbombDifficulty difficulty,
    WordbombLanguage language,
    List<User> users,
    ulong channelId,
    ulong serverId,
    RestClient restClient
) {
    private List<WordbombPlayer> players = users.Select(u => new WordbombPlayer(u, 3)).ToList();
    private int currentPlayerIndex = 0;
    private readonly RestClient restClient = restClient;
    private readonly ulong channelId = channelId;
    private readonly ulong serverId = serverId;
    private WordbombPatternManager patternManager = new(difficulty, language);
    private readonly List<string> usedWords = [];
    private readonly DatabaseContext dbContext = new();
    private DatabaseObject.WordbombGame dbGame = null!;

    public async Task TestNextPlayer()
    {
        ChannelManager.MarkAsBusy(channelId, TimeSpan.FromMinutes(5));

        var player = players[currentPlayerIndex];

        var phrase = patternManager.GetRandomPattern();

        var promptEmbed = new EmbedProperties()
            .WithTitle($"**{phrase.Phrase.ToUpper()}**")
            .WithDescription(
                $"It's <@{player.User.Id}>'s turn!\n\n"
                + string.Join("", Globals.AlphabetLower.Select(
                    c =>
                    {
                        string s = player.RemainingLetters.Contains(c)
                            ? $":regional_indicator_{c}:"
                            : ":heavy_minus_sign:";
                        if (c == 'm') s += '\n';
                        return s;
                    }
                ))
            )
            .WithColor(Globals.Colors.EmbedNone)
            .WithThumbnail(player.User.GetAvatarUrl()?.ToString());

        RestMessage sentMessage = await restClient.SendMessageAsync(
            channelId,
            new MessageProperties().WithEmbeds([promptEmbed])
        );

        Message? message = null;
        EventListener<Message> eventListener = new(async (m, listener) =>
        {
            if (m.CreatedAt <= sentMessage.CreatedAt || m.Author.Id != player.User.Id) return;
            string word = m.Content.Trim().ToLower();
            if (phrase.Matches(word))
            {
                if (!usedWords.Contains(word))
                {
                    message = m;
                    listener.Deactivate();
                    player.RemainingLetters.RemoveAll(c => word.Contains(c));
                }
                else
                {
                    await restClient.AddMessageReactionAsync(
                        channelId,
                        m.Id,
                        new ReactionEmojiProperties("\U0001F502") // :repeat_one:
                    );
                }
            }
            else
            {
                await restClient.AddMessageReactionAsync(
                    channelId,
                    m.Id,
                    new ReactionEmojiProperties("\u274C") // :x:
                );
            }
        });
        eventListener.Activate();
        await eventListener.WaitForDeactivation(10);

        bool updatePlayerIndex = true;
        var embed = new EmbedProperties();
        if (message == null)
        {
            player.Lives--;
            if (player.Lives == 0)
            {
                embed = embed.WithDescription($"**<@{player.User.Id}> is out!**")
                    .WithColor(Globals.Colors.Red);
                players.Remove(player);
                updatePlayerIndex = false;
            }
            else
            {
                embed = embed.WithDescription($"**<@{player.User.Id}> failed!** {player.Lives} lives left")
                    .WithColor(Globals.Colors.Orange);
            }
        }
        else
        {
            usedWords.Add(message.Content.Trim().ToLower());
            await restClient.AddMessageReactionAsync(
                channelId,
                message.Id,
                new ReactionEmojiProperties("\u2705") // :white_check_mark:
            );
            if (player.RemainingLetters.Count == 0)
            {
                player.ResetLetters();
                player.Lives++;
                embed = embed.WithDescription($"**<@{player.User.Id}> passed and earned an extra life!**");
            }
            else
            {
                embed = embed.WithDescription($"**<@{player.User.Id}> passed!**");
            }
            embed = embed.WithColor(Globals.Colors.Green);
        }

        var msgProperties = new MessageProperties().WithEmbeds([embed]);

        await restClient.ModifyMessageAsync(
            channelId,
            sentMessage.Id,
            m =>
            {
                m.Embeds = [promptEmbed.WithColor(
                    message == null ? Globals.Colors.Red : Globals.Colors.Green
                )];
            }
        );
        if (message == null)
        {
            sentMessage = await restClient.SendMessageAsync(
                channelId,
                new MessageProperties().WithEmbeds([embed])
            );
        }
        else
        {
            sentMessage = await message.ReplyAsync(
                new ReplyMessageProperties().WithEmbeds([embed])
            );
        }

        if (message == null)
        {
            var fail = new DatabaseObject.WordbombFail()
            {
                Game = dbGame,
                Phrase = phrase.Phrase.ToUpper(),
                UserId = player.User.Id,
                Timestamp = (ulong)sentMessage.CreatedAt.ToUnixTimeSeconds(),
                MessageId = sentMessage.Id
            };
            fail.SyncIds();
            dbGame.Fails.Add(fail);
        }
        else
        {
            var pass = new DatabaseObject.WordbombPass()
            {
                Game = dbGame,
                Phrase = phrase.Phrase.ToUpper(),
                UserId = player.User.Id,
                Word = message.Content.Trim().ToLower(),
                Timestamp = (ulong)message.CreatedAt.ToUnixTimeSeconds(),
                MessageId = message.Id
            };
            pass.SyncIds();
            dbGame.Passes.Add(pass);
        }

        if (updatePlayerIndex) currentPlayerIndex++;
        if (currentPlayerIndex == players.Count) currentPlayerIndex = 0;
    }

    public async Task Play()
    {
        dbGame = new()
        {
            StartTimestamp = (ulong)DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
            ChannelId = channelId,
            ServerId = serverId
        };
        List<WordbombPlayer> allPlayers = [.. players];

        while (players.Count != 1) await TestNextPlayer();

        User winner = players.First().User;
        string? avatarUrl = winner.GetAvatarUrl()?.ToString();
        if (avatarUrl != null)
        {
            if (avatarUrl.Contains('?')) avatarUrl = avatarUrl.Substring(0, avatarUrl.IndexOf('?'));
            avatarUrl += "?size=1024&quality=lossless";
        }
        RestMessage lastMessage = await restClient.SendMessageAsync(
            channelId,
            new MessageProperties().WithEmbeds([
                new EmbedProperties()
                    .WithTitle($"{winner.Username} is the victor! :partying_face:")
                    .WithColor(Globals.Colors.Green)
                    .WithImage(avatarUrl)
            ])
        );

        ChannelManager.MarkAsFree(channelId);

        foreach (var player in allPlayers)
        {
            var result = new DatabaseObject.WordbombResult()
            {
                Game = dbGame,
                UserId = player.User.Id,
                Victory = player.User.Id == winner.Id,
                FailCount = dbGame.Fails.Where(f => f.UserId == player.User.Id).Count(),
                PassCount = dbGame.Passes.Where(p => p.UserId == player.User.Id).Count()
            };
            result.SyncIds();
            dbGame.Results.Add(result);
        }

        dbGame.EndTimestamp = (ulong)lastMessage.CreatedAt.ToUnixTimeSeconds();
        dbGame.LastMessageId = lastMessage.Id;

        dbContext.WordbombGames.Add(dbGame);
        await dbContext.SaveChangesAsync();
    }

}