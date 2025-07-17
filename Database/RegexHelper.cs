using System.Text.RegularExpressions;

public static class RegexHelper
{
    public static string GetPhraseRegex(string phrase)
    {
        return phrase.All(char.IsLetter) ? $@"\y(?:{phrase})\y" : $@"(?<=\s|^){Regex.Escape(phrase)}(?=\s|$)";
    }
}