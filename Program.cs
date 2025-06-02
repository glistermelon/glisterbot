using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Hosting;

using NetCord.Gateway;
using NetCord.Hosting.Gateway;
using NetCord.Hosting.Services;
using NetCord.Hosting.Services.ApplicationCommands;

using GlisterBot.Commands;
using NetCord;
using NetCord.Hosting.Services.ComponentInteractions;
using NetCord.Services.ComponentInteractions;
using Events;
using GlisterBot.Commands.Wordbomb;

var builder = Host.CreateApplicationBuilder(args);

// Initialize configuration from appsettings.json

Configuration configuration = new();
Globals.Configuration = configuration;

new ConfigurationBuilder()
    .SetBasePath(Directory.GetCurrentDirectory())
    .AddJsonFile("appsettings.json", optional: false, reloadOnChange: true)
    .AddCommandLine([])
    .AddEnvironmentVariables()
    .Build()
    .Bind(configuration);

// Create dynamic data directory if it doesn't exist

if (!Directory.Exists(Configuration.DynamicFilesDir))
{
    Directory.CreateDirectory(Configuration.DynamicFilesDir);
}

// Initialize wordbomb cache

WordbombPatternManager.InitializePhraseCache();

// Initialize graph font

Globals.initializePlotFont();

// Set up database

new DatabaseContext().Database.EnsureCreated();

// Initialize profanity log

ProfanityLogHandler.Initialize();

// Set up Discord bot

builder.Services
    .AddDiscordGateway(
        options =>
        {
            options.Token = configuration.Discord.Token;
            options.Intents = GatewayIntents.Guilds
                | GatewayIntents.GuildMessages
                | GatewayIntents.MessageContent
                | GatewayIntents.GuildPresences
                | GatewayIntents.GuildUsers;
            options.Presence = new(UserStatusType.Online)
            {
                Activities = [new UserActivityProperties("2025", UserActivityType.Watching) { }]
            };
        }
    )
    .AddApplicationCommands()
    .AddGatewayEventHandlers(typeof(GuildCreateEventHandler).Assembly)
    .AddComponentInteractions<ButtonInteraction, ButtonInteractionContext>();

await builder.Build()
    .AddModules(typeof(Stats).Assembly)
    .UseGatewayEventHandlers()
    .RunAsync();
