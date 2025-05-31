#pragma warning disable 8618

namespace MessageLogging.DataTypes;

public class User
{
    public ulong Id { get; set; }
    public required string Username { get; set; }
    public required bool Deleted { get; set; }
    public User? MainAccount { get; set; }
    public ICollection<Message> Messages { get; set; } = [];
    public ICollection<ProfanityRecord> ProfanityRecords { get; set; } = [];
    public ulong? MainAccountId { get; private set; }
    public void SyncIds()
    {
        MainAccountId = MainAccount?.Id;
    }
}