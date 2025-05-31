using Microsoft.EntityFrameworkCore;
using MessageLogging.DataTypes;
using NetCord.Rest;
using System.Text.RegularExpressions;

public partial class DatabaseContext : DbContext
{
    public DbSet<Attachment> Attachments { get; set; }
    public DbSet<Channel> Channels { get; set; }
    public DbSet<Message> Messages { get; set; }
    public DbSet<Reaction> Reactions { get; set; }
    public DbSet<Server> Servers { get; set; }
    public DbSet<TimeRange> TimeRanges { get; set; }
    public DbSet<User> Users { get; set; }
    public DbSet<ProfanityRecord> ProfanityRecords { get; set; }

    protected override void OnConfiguring(DbContextOptionsBuilder optionsBuilder)
        => optionsBuilder
            .UseNpgsql(Globals.Configuration.Database.ConnectionString)
            .UseUpperSnakeCaseNamingConvention();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        base.OnModelCreating(modelBuilder);
        modelBuilder.Entity<Attachment>(attachment =>
        {
            attachment.HasOne(a => a.Message).WithMany(m => m.Attachments).HasForeignKey(a => a.MessageId);
        });
        modelBuilder.Entity<Channel>(channel =>
        {
            channel.Property(obj => obj.Id).ValueGeneratedNever();
            channel.HasOne(c => c.Server).WithMany().HasForeignKey(c => c.ServerId);
            channel.HasMany(c => c.RecordedTimespans).WithOne(t => t.Channel).HasForeignKey(t => t.ChannelId);
        });
        modelBuilder.Entity<Message>(message =>
        {
            message.Property(obj => obj.Id).ValueGeneratedNever();
            message.HasOne(m => m.Server).WithMany().HasForeignKey(m => m.ServerId);
            message.HasOne(m => m.User).WithMany(u => u.Messages).HasForeignKey(m => m.UserId);
            message.HasOne(m => m.Channel).WithMany().HasForeignKey(m => m.ChannelId);
            message.HasMany(m => m.Reactions).WithOne(r => r.Message);
            message.HasMany(m => m.UsersMentioned).WithMany();
            message.HasMany(m => m.Attachments).WithOne(a => a.Message);
        });
        modelBuilder.Entity<Reaction>(reaction =>
        {
            reaction.Property(obj => obj.MessageId).ValueGeneratedNever();
            reaction.Property(obj => obj.UserId).ValueGeneratedNever();
            reaction.Property(obj => obj.EmojiName).ValueGeneratedNever();
            reaction.Property(obj => obj.ServerEmojiId).ValueGeneratedNever();
            reaction.HasIndex(r => new { r.MessageId, r.UserId, r.EmojiName, r.ServerEmojiId })
                .IsUnique();
        });
        modelBuilder.Entity<Server>(server =>
        {
            server.Property(obj => obj.Id).ValueGeneratedNever();
        });
        modelBuilder.Entity<TimeRange>(timeRange =>
        {
            timeRange.HasOne(t => t.Channel).WithMany(c => c.RecordedTimespans).HasForeignKey(t => t.ChannelId);
        });
        modelBuilder.Entity<User>(user =>
        {
            user.Property(obj => obj.Id).ValueGeneratedNever();
            user.HasMany(u => u.Messages).WithOne(m => m.User).HasForeignKey(m => m.UserId);
            user.HasMany(u => u.ProfanityRecords).WithOne(r => r.User).HasForeignKey(r => r.UserId);
            user.HasOne(u => u.MainAccount).WithMany().HasForeignKey(u => u.MainAccountId);
        });
        modelBuilder.Entity<ProfanityRecord>(record =>
        {
            record.HasKey(r => r.Id);
            record.Property(r => r.Id).ValueGeneratedOnAdd();
            record.HasOne(r => r.Server).WithMany().HasForeignKey(r => r.ServerId);
            record.HasOne(r => r.User).WithMany(u => u.ProfanityRecords).HasForeignKey(r => r.UserId);
        });
    }

    // FOR SAFETY, PREVENTING RECURSION, ETC
    // GetOrAdd should never call GetOrAdd/UpsertDb for other entities
    // UpsertDb can call GetOrAdd only for owning entities:
    //     Attachment: Message
    //     Channel: Server
    //     Message: Channel, User
    //     Reaction: Message, Channel, User
    //     Server: N/A
    //     User: N/A

    [GeneratedRegex(@"<@(\d+)>")]
    private static partial Regex UsersMentionedRegex();

    private async Task<Message> UpsertDbMessage(
        RestMessage netcordMessage, NetCord.TextChannel netcordChannel, ulong serverId
    )
    {
        Channel dbChannel = GetOrAddToDbChannel(netcordMessage.ChannelId, serverId);
        User dbUser = GetOrAddToDbUser(netcordMessage.Author);
        Message dbMessage = new()
        {
            Id = netcordMessage.Id,
            Content = netcordMessage.Content,
            Server = dbChannel.Server,
            Timestamp = (ulong)netcordMessage.CreatedAt.ToUnixTimeSeconds(),
            User = dbUser,
            Channel = dbChannel,
            JumpURL = $"https://discord.com/channels/{dbChannel.Server.Id}/{dbChannel.Id}/{netcordMessage.Id}",
            Reactions = [],
            MentionsEveryone = netcordMessage.MentionEveryone,
            RolesMentioned = [.. netcordMessage.MentionedRoleIds],
            UsersMentioned = [.. netcordMessage.MentionedUsers.Select(GetOrAddToDbUser)],
            ReplyingTo = netcordMessage.ReferencedMessage == null ?
                null : await GetOrAddToDbMessage(netcordMessage.ReferencedMessage, netcordChannel, serverId),
            Attachments = []
        };
        dbMessage.SyncIds();
        dbMessage = Messages.Upsert(dbMessage).RunAndReturn().First();

        foreach (var reaction in netcordMessage.Reactions)
        {
            var emoji = reaction.Emoji;
            if (emoji.Name == null) continue;
            ReactionEmojiProperties properties;
            if (emoji.Id == null) properties = new(emoji.Name);
            else properties = new(emoji.Name, emoji.Id.Value);
            properties.Name = Uri.EscapeDataString(properties.Name); // NetCord bug?
            foreach (var user in await netcordChannel.GetMessageReactionsAsync(netcordMessage.Id, properties).ToListAsync())
            {
                UpsertDbReaction(reaction.Emoji, dbMessage, user);
            }
        }

        foreach (var attachment in netcordMessage.Attachments)
        {
            if (attachment.ContentType == null) continue;
            Attachment dbAttachment = new()
            {
                Message = dbMessage,
                ContentType = attachment.ContentType,
                SourceURL = attachment.Url,
                ProxyURL = attachment.ProxyUrl,
                Size = attachment.Size
            };
            Attachments.Add(dbAttachment);
        }

        HashSet<ulong> mentionedUserIds = [];
        foreach (Match match in UsersMentionedRegex().Matches(dbMessage.Content))
        {
            mentionedUserIds.Add(ulong.Parse(match.Groups[1].Value));
        }
        foreach (ulong userId in mentionedUserIds)
        {
            User? user = Users.FirstOrDefault(u => u.Id == userId);
            if (user != null && !dbMessage.UsersMentioned.Any(u => u.Id == userId))
            {
                dbMessage.UsersMentioned.Add(user);
            }
        }

        return dbMessage;
    }

    private Channel UpsertDbChannel(ulong channelId, Server dbServer)
    {
        Channel dbChannel = new()
        {
            Id = channelId,
            Server = dbServer
        };
        dbChannel.SyncIds();
        return Channels.Upsert(dbChannel).RunAndReturn().First();
    }

    private Server UpsertDbServer(ulong serverId)
    {
        Server server = new()
        {
            Id = serverId
        };
        return Servers.Upsert(server).RunAndReturn().First();
    }

    private User UpsertDbUser(NetCord.User netcordUser)
    {
        User user = new()
        {
            Id = netcordUser.Id,
            Username = netcordUser.Username,
            Deleted = netcordUser.Username == "Deleted User" || netcordUser.Username.StartsWith("deleted_user_"),
            MainAccount = null
        };
        return Users.Upsert(user).RunAndReturn().First();
    }

    private Reaction? UpsertDbReaction(
        NetCord.MessageReactionEmoji emoji,
        Message dbMessage,
        NetCord.User netcordUser
    )
    {
        if (emoji.Name == null && emoji.Id == null) return null;
        Reaction dbReaction = new()
        {
            Server = dbMessage.Channel.Server,
            Message = dbMessage,
            User = GetOrAddToDbUser(netcordUser),
            EmojiName = emoji.Name,
            ServerEmojiId = emoji.Id
        };
        dbReaction.SyncIds();
        if (!dbMessage.Reactions.Any(r => r.Equals(dbReaction)))
        {
            dbReaction = Reactions.Upsert(dbReaction)
                .On(r => new { r.MessageId, r.UserId, r.EmojiName, r.ServerEmojiId })
                .RunAndReturn().First();
            dbMessage.Reactions.Add(dbReaction);
            return dbReaction;
        }
        else
        {
            return dbMessage.Reactions.First(r => r.Equals(dbReaction));
        }
    }
    private async Task<Reaction?> UpsertDbReaction(
        NetCord.MessageReactionEmoji emoji,
        RestMessage netcordMessage,
        NetCord.User netcordUser,
        NetCord.TextChannel netcordChannel,
        ulong serverId
    )
    {
        if (emoji.Name == null && emoji.Id == null) return null;
        // manual calls instead of GetOrAdd because I need to KNOW whether it gets or adds
        // if it gets, just add the reaction to existing message object
        // if it adds, don't do anything because the reaction will already have been processed
        Message? dbMessage = Messages.FirstOrDefault(m => m.Id == netcordMessage.Id);
        if (dbMessage == null)
        {
            dbMessage = await UpsertDbMessage(netcordMessage, netcordChannel, serverId);
            return dbMessage.Reactions.FirstOrDefault(r => r.Equals(netcordMessage.Id, netcordUser.Id, emoji));
        }
        return UpsertDbReaction(emoji, dbMessage, netcordUser);
    }

    public async Task<Message> GetOrAddToDbMessage(RestMessage netcordMessage, NetCord.TextChannel netcordChannel, ulong serverId)
    {
        Message? message = Messages.FirstOrDefault(m => m.Id == netcordMessage.Id);
        return message ?? await UpsertDbMessage(netcordMessage, netcordChannel, serverId);
    }

    public Channel GetOrAddToDbChannel(ulong channelId, ulong serverId)
    {
        Channel? channel = Channels.FirstOrDefault(c => c.Id == channelId);
        return channel ?? UpsertDbChannel(channelId, GetOrAddToDbServer(serverId));
    }

    public Server GetOrAddToDbServer(ulong serverId)
    {
        Server? server = Servers.FirstOrDefault(s => s.Id == serverId);
        return server ?? UpsertDbServer(serverId);
    }

    public User GetOrAddToDbUser(NetCord.User netcordUser)
    {
        User? user = Users.FirstOrDefault(u => u.Id == netcordUser.Id);
        return user ?? UpsertDbUser(netcordUser);
    }

    public async Task<Reaction?> GetOrAddToDbReaction(
        NetCord.MessageReaction netcordReaction,
        RestMessage netcordMessage,
        NetCord.User netcordUser,
        NetCord.TextChannel netcordChannel,
        ulong serverId
    )
    {
        Reaction? reaction = Reactions.FirstOrDefault(
            r => r.Message.Id == netcordMessage.Id
                && r.User.Id == netcordMessage.Author.Id
                && (
                    r.ServerEmojiId != null ?
                    (r.ServerEmojiId == netcordReaction.Emoji.Id) : (r.EmojiName == netcordReaction.Emoji.Name)
                )
        );
        return reaction ?? await UpsertDbReaction(
            netcordReaction.Emoji, netcordMessage, netcordUser, netcordChannel, serverId
        );
    }
    
    public Reaction? GetOrAddToDbReaction(
        NetCord.MessageReaction netcordReaction,
        Message dbMessage,
        NetCord.User netcordUser
    )
    {
        Reaction? reaction = Reactions.FirstOrDefault(r => r.Equals(netcordReaction));
        return reaction ?? UpsertDbReaction(netcordReaction.Emoji, dbMessage, netcordUser);
    }

}