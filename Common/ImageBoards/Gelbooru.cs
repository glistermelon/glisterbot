using System.Net.Http.Json;

public class Gelbooru : ImageBoard
{
    protected virtual string SiteBaseUrl { get; } = "https://gelbooru.com";
    protected override string ApiBaseUrl { get; } = "https://gelbooru.com";

    protected virtual string GetCredentialParameters()
    {
        return Globals.Configuration.Gelbooru.CredentialParameters;
    }

    private class PostsJson
    {
        public List<PostJson>? post { get; set; } = null;
    }

    protected class PostJson
    {
        public required ulong id { get; set; }
        public required string sample_url { get; set; }
    }
    
    protected string GetPostUrlById(string id)
    {
        return $"{SiteBaseUrl}/index.php?page=post&s=view&id={id}";
    }

    private new class Post(Gelbooru gelbooru, PostJson json) : ImageBoard.Post
    {
        public override string GetUrl()
        {
            return gelbooru.GetPostUrlById(json.id.ToString());
        }

        public override async Task<LocalImage> GetPreviewImage()
        {
            var request = new HttpRequestMessage(HttpMethod.Get, json.sample_url);
            request.Headers.Add("Referer", gelbooru.SiteBaseUrl);
            HttpResponseMessage response = await gelbooru.httpClient.SendAsync(request);
            MemoryStream imageStream = new();
            await response.Content.CopyToAsync(imageStream);
            imageStream.Position = 0;
            return new LocalImage()
            {
                FileExtension = Path.GetExtension(new Uri(json.sample_url).AbsolutePath)[1..],
                DataStream = imageStream
            };
        }
    }

    protected virtual async Task<List<PostJson>> GetPostsInternal(string url)
    {
        PostsJson? posts = await httpClient.GetFromJsonAsync<PostsJson>(url);
        if (posts == null || posts.post == null) return [];   
        return posts.post;
    }

    public override async Task<List<ImageBoard.Post>> GetPosts(string tags)
    {
        string url = ApiBaseUrl + "/index.php?page=dapi&s=post&q=index&json=1" + GetCredentialParameters();
        url += "&tags=" + Uri.EscapeDataString(tags + " " + GetFunctionalTagBlacklist());
        return (await GetPostsInternal(url))
            .Where(postJson => !string.IsNullOrWhiteSpace(postJson.sample_url))
            .Select(postJson => new Post(this, postJson))
            .Cast<ImageBoard.Post>()
            .ToList();
    }
}