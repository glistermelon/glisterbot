#pragma warning disable 1998

using Microsoft.EntityFrameworkCore;
using NetCord;
using NetCord.Rest;
using NetCord.Services.ApplicationCommands;
using NetCord.Services.ComponentInteractions;

namespace GlisterBot.Commands;

public partial class Config : ApplicationCommandModule<ApplicationCommandContext>
{
    public partial class AltAccount : ApplicationCommandModule<ApplicationCommandContext>
    {
        [SubSlashCommand("add", "Specify an account as an alt")]
        public async Task<InteractionMessageProperties> AddAltAccount(User alt_account)
        {
            if (Context.User.Id == alt_account.Id) return new()
            {
                Embeds = [
                    new EmbedProperties()
                        .WithColor(Globals.Colors.Red)
                        .WithDescription("You cannot mark yourself as an alt account!")
                ],
                Flags = MessageFlags.Ephemeral
            };

            DatabaseContext dbContext = new();

            MessageLogging.DataTypes.User? dbUser = await dbContext
                .Users.Where(u => u.Id == Context.User.Id).FirstOrDefaultAsync();
            if (dbUser?.MainAccountId != null) return new()
            {
                Embeds = [
                    new EmbedProperties()
                        .WithColor(Globals.Colors.Red)
                        .WithDescription("You cannot add an alt to this account because this account is marked as an alt itself.")
                ],
                Flags = MessageFlags.Ephemeral
            };

            // add alt to db so it will be available on confirm
            dbContext.GetOrAddToDbUser(alt_account);
            await dbContext.SaveChangesAsync();

            var embed = new EmbedProperties()
                .WithTitle("Alt Account Confirmation")
                .WithDescription(
                    $@"<@{alt_account.Id}>, click below to confirm that you are
                an alt account belonging to <@{Context.User.Id}>."
                )
                .WithColor(Globals.Colors.EmbedNone);
            var button = new ButtonProperties($"altauth-confirm:{Context.Interaction.Id}", "Confirm", ButtonStyle.Success);
            AltAccountAuthModule.PendingRequests[Context.Interaction.Id] = new PendingAltAuth()
            {
                MainId = Context.User.Id,
                AltId = alt_account.Id,
                Interaction = Context.Interaction,
                Embed = embed,
                Button = button
            };
            return new()
            {
                Embeds = [embed],
                Components = [new ActionRowProperties([button])]
            };
        }

        [SubSlashCommand("remove", "Un-mark an account as an alt")]
        public async Task<InteractionMessageProperties> RemoveAltAccount(
            [SlashCommandParameter(
                Description = "Leave this empty to unmark yourself account as an alt"
            )] User? alt_account = null
        )
        {
            if (alt_account != null)
            {
                DatabaseContext dbContext = new();
                var dbAlt = await dbContext.Users.Where(u => u.Id == alt_account.Id).FirstOrDefaultAsync();
                if (dbAlt == null || dbAlt.MainAccountId != Context.User.Id) return new()
                {
                    Embeds = [
                        new EmbedProperties()
                            .WithColor(Globals.Colors.Red)
                            .WithDescription($"<@{alt_account.Id}> isn't marked as your alt!")
                    ],
                    Flags = MessageFlags.Ephemeral
                };
                dbAlt.MainAccount = null;
                dbAlt.SyncIds();
                await dbContext.SaveChangesAsync();
                return new()
                {
                    Embeds = [
                        new EmbedProperties()
                            .WithColor(Globals.Colors.Green)
                            .WithDescription($"<@{alt_account.Id}> is no longer marked as an alt.")
                    ]
                };
            }
            else
            {
                DatabaseContext dbContext = new();
                var dbUser = await dbContext.Users.Where(u => u.Id == Context.User.Id).FirstOrDefaultAsync();
                if (dbUser == null || dbUser.MainAccountId == null) return new()
                {
                    Embeds = [
                        new EmbedProperties()
                            .WithColor(Globals.Colors.Red)
                            .WithDescription($"Your account isn't marked as an alt!")
                    ],
                    Flags = MessageFlags.Ephemeral
                };
                dbUser.MainAccount = null;
                dbUser.SyncIds();
                await dbContext.SaveChangesAsync();
                return new()
                {
                    Embeds = [
                        new EmbedProperties()
                            .WithColor(Globals.Colors.Green)
                            .WithDescription($"Your account is no longer marked as an alt.")
                    ]
                };
            }
        }
    }
}

public class PendingAltAuth
{
    public ulong MainId { get; set; }
    public ulong AltId { get; set; }
    public required Interaction Interaction { get; set; }
    public required EmbedProperties Embed { get; set; }
    public required ButtonProperties Button { get; set; }
}

public class AltAccountAuthModule : ComponentInteractionModule<ButtonInteractionContext>
{
    public static Dictionary<ulong, PendingAltAuth> PendingRequests { get; set; } = [];

    [ComponentInteraction("altauth-confirm")]
    public async Task Confirm(ulong interactionId)
    {
        if (!PendingRequests.TryGetValue(interactionId, out PendingAltAuth? request)) return;
        // if (Context.User.Id != request.AltId)
        // {
        //     await Context.Interaction.SendResponseAsync(InteractionCallback.Message(new()
        //     {
        //         Content = $"Only <@{request.AltId}> can confirm this!",
        //         Flags = MessageFlags.Ephemeral
        //     }));
        //     return;
        // }
        await Context.Interaction.SendResponseAsync(InteractionCallback.DeferredModifyMessage);

        DatabaseContext dbContext = new();
        var dbMain = await dbContext.Users.Where(u => u.Id == request.MainId).FirstOrDefaultAsync();
        var dbAlt = await dbContext.Users.Where(u => u.Id == request.AltId).FirstOrDefaultAsync();
        if (dbMain == null || dbAlt == null)
        {
            await Context.Interaction.SendResponseAsync(InteractionCallback.Message(
                new()
                {
                    Embeds = [
                        new EmbedProperties()
                            .WithColor(Globals.Colors.Red)
                            .WithDescription($"Something went wrong.")
                    ],
                    Flags = MessageFlags.Ephemeral
                }
            ));
            return;
        }
        dbAlt.MainAccount = dbMain;
        dbAlt.SyncIds();
        await dbContext.SaveChangesAsync();

        await request.Interaction.ModifyResponseAsync(
            m =>
            {
                m.Embeds = [
                    request.Embed
                        .WithColor(Globals.Colors.Green)
                        .WithDescription($"<@{request.AltId}> has been added as an alt account.")
                ];
                request.Button.Disabled = true;
                m.Components = [new ActionRowProperties([request.Button])];
            }
        );
        PendingRequests.Remove(interactionId);
    }
}