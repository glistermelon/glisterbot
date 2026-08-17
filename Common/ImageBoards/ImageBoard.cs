using System.Threading.RateLimiting;

public abstract class ImageBoard
{
    public static readonly Gelbooru gelbooru = new();
    public static readonly Rule34 rule34 = new();

    public static readonly string tagBlacklist = "vore gore insect insects insect* bug fart death necrophilia scat fat obese feces ai_generated";

    public static string GetFunctionalTagBlacklist()
    {
        return string.Join(" ", tagBlacklist.Split().Select(tag => "-" + tag));
    }

    protected abstract string ApiBaseUrl { get; }

    protected readonly HttpClient httpClient = new(
        new RateLimitedHttpHandler() { InnerHandler = new HttpClientHandler() }
    );

    public abstract class Post
    {
        public abstract string GetUrl();
        public abstract Task<LocalImage> GetPreviewImage();
    }

    public class LocalImage
    {
        public required string FileExtension { get; set; }
        public required MemoryStream DataStream { get; set; }
    }

    public abstract Task<List<Post>> GetPosts(string tags);
}