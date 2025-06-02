using NetCord;
using NetCord.Rest;
using NetCord.Services.ComponentInteractions;

namespace GlisterBot.Commands.Wordbomb;

public class WordbombQueueState
{
    public required Interaction Interaction { get; set; }
    public required WordbombDifficulty Difficulty { get; set; }
    public required WordbombLanguage Language { get; set; }
    public required List<User> Users { get; set; }
    public required ulong ChannelId { get; set; }
    public required ulong ServerId { get; set; }
}

public class WordbombQueue(RestClient restClient) : ComponentInteractionModule<ButtonInteractionContext>
{
    private static readonly Dictionary<ulong, WordbombQueueState> activeQueues = [];
    private static string? HelpDescription = null;

    public RestClient RestClient { get; set; } = restClient;

    public static InteractionMessageProperties Register(WordbombQueueState state)
    {
        ChannelManager.MarkAsBusy(state.ChannelId, TimeSpan.FromMinutes(5), () => Timeout(state));
        activeQueues[state.Interaction.Id] = state;
        return GetMessageProperties(state);
    }

    private static InteractionMessageProperties GetMessageProperties(
        WordbombQueueState state,
        bool disableButtons = false,
        bool timedOut = false
    ) {
        string desc;
        if (!timedOut)
        {
            desc = "";
            desc += $"**Difficulty:** {state.Difficulty}";
            desc += "\n**Starting Lives:** 3";
            desc += "\n**Turn Time:** 10 seconds";
            desc += $"\n**Language:** {state.Language.ToLongString()}";
            desc += $"\n### **Players:**";
            foreach (var user in state.Users)
            {
                desc += user == state.Users[0] ? $"\n<@{user.Id}> **(host)**" : $"\n<@{user.Id}>";
            }
        }
        else desc = "*Timed out.*";

        var embed = new EmbedProperties()
            .WithTitle("Word Bomb")
            .WithDescription(desc)
            .WithColor(Globals.Colors.DarkGreen)
            .WithThumbnail(new("attachment://image.png"));

        var attachment = new AttachmentProperties("image.png", new FileStream(
            $"{Configuration.FileDir}/wordbomb/bomb.png", FileMode.Open, FileAccess.Read
        ));

        ActionRowProperties actionRow = [
            new ButtonProperties($"wordbomb-start:{state.Interaction.Id}", "Start", ButtonStyle.Success),
            new ButtonProperties($"wordbomb-join:{state.Interaction.Id}", "Join", ButtonStyle.Primary),
            new ButtonProperties($"wordbomb-leave:{state.Interaction.Id}", "Leave", ButtonStyle.Danger),
            new ButtonProperties($"wordbomb-help", "Help", ButtonStyle.Secondary)
        ];

        if (disableButtons)
        {
            foreach (var button in actionRow) button.Disabled = true;
        }

        return new()
        {
            Embeds = [embed],
            Attachments = [attachment],
            Components = [actionRow]
        };
    }

    private static async Task UpdateMessage(
        WordbombQueueState state,
        bool disableButtons = false,
        bool timedOut = false
    ) {
        var properties = GetMessageProperties(state, disableButtons: disableButtons, timedOut: timedOut);
        await state.Interaction.ModifyResponseAsync(m =>
        {
            m.Embeds = properties.Embeds;
            m.Attachments = properties.Attachments;
            m.Components = properties.Components;
        });
    }

    private static async Task Timeout(WordbombQueueState state)
    {
        activeQueues.Remove(state.Interaction.Id);
        await UpdateMessage(state, disableButtons: true, timedOut: true);
    }

    [ComponentInteraction("wordbomb-start")]
    public async Task StartGame(ulong interactionId)
    {
        if (!activeQueues.TryGetValue(interactionId, out WordbombQueueState? state)) return;

        if (state.Users.Count < 2)
        {
            await Context.Interaction.SendResponseAsync(InteractionCallback.Message(
                new()
                {
                    Content = "At least 2 players are required to start the game!",
                    Flags = MessageFlags.Ephemeral
                }
            ));
            return;
        }

        if (Context.User.Id != state.Users[0].Id)
        {
            await Context.Interaction.SendResponseAsync(InteractionCallback.Message(
                new()
                {
                    Content = "Only the host can start the game!",
                    Flags = MessageFlags.Ephemeral
                }
            ));
            return;
        }

        await UpdateMessage(state, disableButtons: true);
        await Context.Interaction.SendResponseAsync(InteractionCallback.DeferredModifyMessage);
        await new WordbombGame(
            state.Difficulty,
            state.Language,
            state.Users,
            state.ChannelId,
            state.ServerId,
            RestClient
        ).Play();
    }

    [ComponentInteraction("wordbomb-join")]
    public async Task JoinGame(ulong interactionId)
    {
        if (!activeQueues.TryGetValue(interactionId, out WordbombQueueState? state)) return;
        ChannelManager.MarkAsBusy(state.ChannelId, TimeSpan.FromMinutes(5), () => Timeout(state));
        if (state.Users.Contains(Context.User))
        {
            await Context.Interaction.SendResponseAsync(InteractionCallback.Message(
                new()
                {
                    Content = "You have already joined this game!",
                    Flags = MessageFlags.Ephemeral
                }
            ));
        }
        else
        {
            state.Users.Add(Context.User);
            await Context.Interaction.SendResponseAsync(InteractionCallback.DeferredModifyMessage);
            await UpdateMessage(state);
        }
    }

    [ComponentInteraction("wordbomb-leave")]
    public async Task LeaveGame(ulong interactionId)
    {
        if (!activeQueues.TryGetValue(interactionId, out WordbombQueueState? state)) return;
        bool removed = state.Users.Remove(Context.User);
        if (!removed)
        {
            await Context.Interaction.SendResponseAsync(InteractionCallback.Message(
                new()
                {
                    Content = "You aren't part of this game!",
                    Flags = MessageFlags.Ephemeral
                }
            ));
        }
        else
        {
            await Context.Interaction.SendResponseAsync(InteractionCallback.DeferredModifyMessage);
            await UpdateMessage(state);
        }
    }

    [ComponentInteraction("wordbomb-help")]
    public async Task SendHelpMessage()
    {
        HelpDescription ??= File.ReadAllText($"{Configuration.FileDir}/wordbomb/help.md");
        await Context.Interaction.SendResponseAsync(InteractionCallback.Message(
            new()
            {
                Embeds = [
                    new EmbedProperties()
                        .WithTitle("Word Bomb for Glisterbot was adapted from https://jklm.fun/ \"BombParty\"")
                        .WithDescription(HelpDescription)
                        .WithColor(Globals.Colors.DarkGreen)
                ],
                Flags = MessageFlags.Ephemeral
            }
        ));
    }
}