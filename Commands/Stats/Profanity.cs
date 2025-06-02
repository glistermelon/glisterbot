using NetCord;
using NetCord.Rest;
using NetCord.Services.ApplicationCommands;

namespace GlisterBot.Commands;

public partial class Stats
{
    [SubSlashCommand("profanity", "Expose how terrible and awful someone is")]
    public async Task<InteractionMessageProperties> ExecuteProfanity(
        [SlashCommandParameter(Name = "user")] User user
    )
    {
        if (Context.Guild == null) return "";
        var dbContext = new DatabaseContext();
        var dbUser = dbContext.GetOrAddToDbUser(user);
        var dbServer = dbContext.GetOrAddToDbServer(Context.Guild.Id);
        UserProfanityInfo data = await new ProfanityLogHandler(dbContext).GetProfanity(dbUser, dbServer)
            ?? throw new Exception($"Failed to get profanity data for user {user.Id}");

        var baseEmbed = new EmbedProperties()
            .WithTitle($"{user.Username}'s Profanity Usage")
            .WithColor(Globals.Colors.DarkGreen);

        List<EmbedProperties> embeds = [];
        List<EmbedFieldProperties> fields = [];
        int lines = 0;
        foreach (var pair in data.TotalCounts.OrderByDescending(pair => pair.Value))
        {
            string category = pair.Key;
            int totalCount = pair.Value;
            EmbedFieldProperties field = new()
            {
                Name = $"{category} - {totalCount}",
                Value = string.Join(
                    "\n",
                    data.Counts[category]
                        .OrderByDescending(pair2 => pair2.Value)
                        .Select(pair2 => $"{pair2.Key} - {pair2.Value}")
                )
            };
            lines += 1 + data.Counts[category].Count;
            if (lines > 15)
            {
                embeds.Add(baseEmbed.Clone().WithFields(fields));
                fields = [];
                lines = 0;
            }
            fields.Add(field);
        }
        if (fields.Count != 0) embeds.Add(baseEmbed.Clone().WithFields(fields));

        if (embeds.Count == 0) {
            return new()
            {
                Embeds = [baseEmbed.WithDescription(
                    "This user has never used any profanity ever. WTF? <:Mewhen3:932086577721667624>"
                )]
            };
        }

        (var embed, var actionRow) = EmbedPaginator.Register(new(embeds, 0, Context.Interaction));

        return new()
        {
            Embeds = [embed],
            Components = [actionRow]
        };

    }
}