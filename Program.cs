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
using MessageLogging;

var builder = Host.CreateApplicationBuilder(args);

// Initialize configuration from appsettings.json

Configuration configuration = new Configuration();
Globals.Configuration = configuration;

new ConfigurationBuilder()
    .SetBasePath(Directory.GetCurrentDirectory())
    .AddJsonFile("appsettings.json", optional: false, reloadOnChange: true)
    .AddCommandLine([])
    .AddEnvironmentVariables()
    .Build()
    .Bind(configuration);

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
    .AddGatewayEventHandlers(typeof(GrabIP).Assembly)
    .AddComponentInteractions<ButtonInteraction, ButtonInteractionContext>();

await builder.Build()
    .AddModules(typeof(GrabIP).Assembly)
    .UseGatewayEventHandlers()
    .RunAsync();
