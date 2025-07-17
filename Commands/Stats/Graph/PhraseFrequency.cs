#pragma warning disable 8618

using System.Text.RegularExpressions;
using Microsoft.EntityFrameworkCore;
using NetCord;
using NetCord.Rest;
using NetCord.Services.ApplicationCommands;
using Npgsql;
using ScottPlot;

namespace GlisterBot.Commands;

class PhraseFrequencyGraphQueryResult {
    public string TimeWindow { get; set; }
    public int Count { get; set; }
}

public partial class Stats
{
    public partial class Graph
    {
        [SubSlashCommand("phrase-frequency", "How many times a phrase has been said over time.")]
        public async Task ExecutePhraseFrequencyGraph(
            string phrase,
            TimeUnit timeUnit,
            [SlashCommandParameter(Name = "user", Description = "Only check messages from a specific user")]
            User? user = null
        )
        {
            if (Context.Guild == null) return;

            phrase = phrase.Trim();

            if (phrase.Length > 100)
            {
                await Context.Interaction.SendResponseAsync(InteractionCallback.Message(
                    new InteractionMessageProperties()
                    {
                        Content = "That phrase is too long! Please pick a shorter phrase.",
                        Flags = MessageFlags.Ephemeral
                    }
                ));
                return;
            }

            await Context.Interaction.SendResponseAsync(InteractionCallback.DeferredMessage());

            DatabaseContext dbContext = new();

            string userSql1, userSql2;
            if (user == null)
            {
                userSql1 = "";
                userSql2 = "";
            }
            else
            {
                var dbUser = dbContext.GetOrAddToDbUser(user);
                userSql1 = @"JOIN ""USERS"" ON ""MESSAGES"".""USER_ID"" = ""USERS"".""ID""";
                userSql2 = $@"
                    AND (
                        ""USER_ID""={dbUser.Id}
                        OR ""USERS"".""MAIN_ACCOUNT_ID""={dbUser.Id}
                    )";
            }
            string rawSql = $@"
                WITH phrase_matches AS (
                    SELECT
                        LOWER(match) AS phrase,
                        to_char(to_timestamp(""TIMESTAMP""), '{timeUnit.ToSqlString()}') AS time_window
                    FROM (
                        SELECT unnest(
                            regexp_matches(
                                ""CONTENT"",
                                @regex,
                                'gi'
                            )
                        ) AS match,
                            ""TIMESTAMP""
                        FROM ""MESSAGES""
                        {userSql1}
                        WHERE ""SERVER_ID""={Context.Guild.Id} {userSql2}
                    )
                )
                SELECT time_window, COUNT(*) AS count
                FROM phrase_matches
                GROUP BY phrase, time_window
                ORDER BY time_window, phrase";
            var regexParam = new NpgsqlParameter("regex", RegexHelper.GetPhraseRegex(phrase));
            var results = await dbContext.Database
                .SqlQueryRaw<PhraseFrequencyGraphQueryResult>(rawSql, regexParam)
                .ToListAsync();

            // remove last result if its the current
            // time window, which has not fully elasped yet
            var latestTime = timeUnit switch
            {
                TimeUnit.Day => DateTime.Now.AddDays(-1),
                TimeUnit.Week => DateTime.Now.AddDays(-7),
                TimeUnit.Month => new DateTime(DateTime.Now.Year, DateTime.Now.Month, 1).AddDays(-1),
                TimeUnit.Year => new DateTime(DateTime.Now.Year, 1, 1).AddDays(-1),
                _ => throw new Exception("Cannot get latest time with unrecognized TimeUnit")
            };
            results.RemoveAll(r => timeUnit.ParseString(r.TimeWindow) > latestTime);

            var baseEmbed = new EmbedProperties()
                .WithTitle($"\"{phrase}\" Usage Frequency")
                .WithColor(Globals.Colors.DarkGreen)
                .WithAuthor(new()
                {
                    IconUrl = user?.GetAvatarUrl()?.ToString(),
                    Name = user == null ? "All users" : user.Username
                });

            if (results.Count == 0)
            {
                await Context.Interaction.SendFollowupMessageAsync(new InteractionMessageProperties()
                {
                    Embeds = [baseEmbed.WithDescription(
                        "That phrase has never been said before! You could be the first... <:Smoothtroll:960789594658451497>"
                    )]
                });
                return;
            }

            var graph = DrawGraph(results, timeUnit, latestTime);

            await Context.Interaction.SendFollowupMessageAsync(new InteractionMessageProperties()
            {
                Embeds = [baseEmbed.WithImage(new("attachment://image.png"))],
                Attachments = [new AttachmentProperties("image.png", graph)]
            });
        }

        private static MemoryStream DrawGraph(List<PhraseFrequencyGraphQueryResult> queryResults, TimeUnit timeUnit, DateTime latestTime)
        {
            if (queryResults.Count == 0)
            {
                throw new Exception("Cannot draw a graph with no data!");
            }

            Dictionary<DateTime, int> data = queryResults
                .ToDictionary(r => timeUnit.ParseString(r.TimeWindow), r => r.Count);
            foreach (var t in timeUnit.GetAllTimesBetween(data.Keys.First(), latestTime))
            {
                if (!data.ContainsKey(t)) data[t] = 0;
            }
            List<DateTime> dataX = [];
            List<int> dataY = [];
            foreach ((DateTime t, int c) in data.OrderBy(p => p.Key))
            {
                dataX.Add(t);
                dataY.Add(c);
            }

            Plot plot = new();
            var line = plot.Add.Scatter(dataX, dataY);

            // Configure horizontal labels
            var tickGen = new ScottPlot.TickGenerators.DateTimeFixedInterval(
                timeUnit == TimeUnit.Year ?
                    new ScottPlot.TickGenerators.TimeUnits.Year()
                    : new ScottPlot.TickGenerators.TimeUnits.Month(),
                timeUnit == TimeUnit.Year ? 1 : 3
            );
            tickGen.LabelFormatter = timeUnit == TimeUnit.Year ? (t => t.ToString("yyyy")) : (t => t.ToString("MMM yyyy"));
            tickGen.GetIntervalStartFunc = _ => dataX.First();
            plot.Axes.DateTimeTicksBottom().TickGenerator = tickGen;
            plot.Axes.Bottom.TickLabelStyle.Rotation = -90;
            plot.Axes.Bottom.TickLabelStyle.OffsetY = timeUnit == TimeUnit.Year ? 15 : 30;
            plot.Axes.Bottom.TickLabelStyle.AntiAliasText = true;
            plot.Axes.Bottom.TickLabelStyle.FontSize = 10;

            // Configure vertical labels
            plot.Axes.Left.TickGenerator = new ScottPlot.TickGenerators.NumericAutomatic()
            {
                MinimumTickSpacing = 25
            };
            plot.Axes.Left.TickLabelStyle.FontSize = 10;
            plot.Axes.Left.Min = 0;

            // White axes
            plot.Axes.Left.FrameLineStyle.Color = Colors.White;
            plot.Axes.Left.TickLabelStyle.ForeColor = Colors.White;
            plot.Axes.Left.MajorTickStyle.Color = Colors.White;
            plot.Axes.Bottom.FrameLineStyle.Color = Colors.White;
            plot.Axes.Bottom.TickLabelStyle.ForeColor = Colors.White;
            plot.Axes.Bottom.MajorTickStyle.Color = Colors.White;

            // Hide unwanted axes
            plot.Axes.Right.FrameLineStyle.IsVisible = false;
            plot.Axes.Top.FrameLineStyle.IsVisible = false;

            // Hide unwanted ticks
            plot.Axes.Left.MinorTickStyle.Color = Globals.Colors.Graph.Invisible;
            plot.Axes.Left.MinorTickStyle.Width = 0;
            plot.Axes.Bottom.MinorTickStyle.Color = Globals.Colors.Graph.Invisible;
            plot.Axes.Bottom.MinorTickStyle.Width = 0;

            // Set line color
            line.Color = Globals.Colors.Graph.Blue;
            line.LineWidth = 2;
            line.MarkerSize = 0;

            // Set background colors
            plot.DataBackground.Color = Globals.Colors.Graph.LightGrey;
            plot.FigureBackground.Color = Globals.Colors.Graph.DarkGrey;

            // Anti-aliasing
            plot.Axes.AntiAlias(true);

            // Configure background grid
            plot.Grid.XAxisStyle.MajorLineStyle.IsVisible = false;
            plot.Grid.YAxisStyle.MajorLineStyle.Width = 1;
            plot.Grid.YAxisStyle.MajorLineStyle.Color = Globals.Colors.Graph.LighterGrey;

            // Label vertical axis
            plot.Axes.Left.Label.Text = "Messages";
            plot.Axes.Left.Label.ForeColor = Colors.White;
            plot.Axes.Left.Label.FontSize = 12;
            plot.Axes.Left.Label.Bold = false;
            plot.Axes.Left.Label.OffsetX = -10;

            // Configure padding
            plot.Layout.Fixed(new PixelPadding(
                61 + int.Max(dataY.Max().ToString().Length - 3, 0) * 8,
                15,
                timeUnit == TimeUnit.Year ? 45 : 68,
                15
            ));

            // Set font
            plot.Axes.Left.Label.FontName = Globals.GraphFontName;
            plot.Axes.Left.TickLabelStyle.FontName = Globals.GraphFontName;
            plot.Axes.Bottom.TickLabelStyle.FontName = Globals.GraphFontName;

            var imageBytes = plot.GetImageBytes(400, 300, ScottPlot.ImageFormat.Png);
            return new MemoryStream(imageBytes);
        }

    }
}