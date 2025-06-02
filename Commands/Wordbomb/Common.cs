using NetCord.Services.ApplicationCommands;

namespace GlisterBot.Commands.Wordbomb;

public enum WordbombDifficulty
{
    [SlashCommandChoice("easy")] Easy,
    [SlashCommandChoice("medium")] Medium,
    [SlashCommandChoice("hard")] Hard
}

public static class WordbombDifficultyExtensions
{
    public static double TargetWordFrequencyReciprocal(this WordbombDifficulty difficulty)
    {
        return difficulty switch
        {
            WordbombDifficulty.Easy => 100,
            WordbombDifficulty.Medium => 300,
            WordbombDifficulty.Hard => 500,
            _ => throw new Exception("Cannot get frequency from unrecognized difficulty")
        };
    }

    public static string ToLowerString(this WordbombDifficulty difficulty)
    {
        return difficulty switch
        {
            WordbombDifficulty.Easy => "easy",
            WordbombDifficulty.Medium => "medium",
            WordbombDifficulty.Hard => "hard",
            _ => throw new Exception("Cannot convert unrecognized difficulty to string")
        };
    }
}

public enum WordbombLanguage
{
    [SlashCommandChoice("english")] English,
    [SlashCommandChoice("español")] Spanish,
    [SlashCommandChoice("français")] French
}

public static class WordbombLanguageExtensions
{
    public static string ToShortString(this WordbombLanguage lang)
    {
        return lang switch
        {
            WordbombLanguage.English => "en",
            WordbombLanguage.Spanish => "es",
            WordbombLanguage.French => "fr",
            _ => throw new Exception("Cannot convert unrecognized language to string")
        };
    }
    public static string ToLongString(this WordbombLanguage lang)
    {
        return lang switch
        {
            WordbombLanguage.English => "English",
            WordbombLanguage.Spanish => "Español",
            WordbombLanguage.French => "Français",
            _ => throw new Exception("Cannot convert unrecognized language to string")
        };
    }
}