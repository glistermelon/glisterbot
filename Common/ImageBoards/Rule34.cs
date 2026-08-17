using System.Text.RegularExpressions;
using System.Xml.Linq;
using Newtonsoft.Json;

public class Rule34 : Gelbooru
{
    protected override string SiteBaseUrl { get; } = "https://rule34.xxx";
    protected override string ApiBaseUrl { get; } = "https://api.rule34.xxx";

    protected override string GetCredentialParameters()
    {
        return Globals.Configuration.Rule34.CredentialParameters;
    }

    protected override async Task<List<PostJson>> GetPostsInternal(string url)
    {
        using HttpResponseMessage response = await httpClient.GetAsync(url);
        string content = await response.Content.ReadAsStringAsync();
        if (string.IsNullOrWhiteSpace(content)) return [];
        return JsonConvert.DeserializeObject<List<PostJson>>(content) ?? [];
    }

    public class Comment
    {
        public required string Content { get; set; }
        public required string Author { get; set; }
        public required string PostId { get; set; }
        public required string PostUrl { get; set; }
        public LocalImage? Image { get; set; }
    }

    public async Task<Comment?> GetRandomComment()
    {
        string url = $"{ApiBaseUrl}/index.php?page=dapi&s=comment&q=index" + GetCredentialParameters();
        string response = await httpClient.GetStringAsync(url);
        XDocument document = XDocument.Parse(response);
        XElement? commentElement = document.Descendants("comment").FirstOrDefault();
        if (commentElement == null) return null;
        string postId = commentElement.Attribute("post_id")?.Value ?? "";
        Post? post = (await GetPosts("id:" + postId)).FirstOrDefault();
        LocalImage? image = post == null ? null : await post.GetPreviewImage();
        return new Comment()
        {
            Content = Regex.Replace(commentElement.Attribute("body")?.Value ?? "", @"\s+", " ").Trim(),
            Author = commentElement.Attribute("creator")?.Value ?? "Anonymous",
            PostId = postId,
            PostUrl = GetPostUrlById(postId),
            Image = image
        };
    }
}