namespace MessageLogging.DataTypes;

public class User
{
    public ulong Id { get; set; }
    public required string Username { get; set; }
    public required bool Deleted { get; set; }
    public ICollection<Message> Messages { get; set; } = [];
    public ICollection<ProfanityRecord> ProfanityRecords { get; set; } = [];
}