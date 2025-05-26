using NetCord.Rest;

public static class ListExtension
{
    public static T? FindAndRemoveFirst<T>(this List<T> list, Predicate<T> pred) where T : class
    {
        int index = list.FindIndex(pred);
        if (index == -1) return null;
        T obj = list[index];
        list.RemoveAt(index);
        return obj;
    }
}

public static class EmbedPropertiesExtension
{
    public static EmbedProperties Clone(this EmbedProperties embed)
    {
        return new EmbedProperties
        {
            Title = embed.Title,
            Description = embed.Description,
            Url = embed.Url,
            Timestamp = embed.Timestamp,
            Color = embed.Color,
            Footer = embed.Footer,
            Image = embed.Image,
            Thumbnail = embed.Thumbnail,
            Author = embed.Author,
            Fields = embed.Fields
        };
    }
}