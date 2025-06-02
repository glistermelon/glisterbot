using Newtonsoft.Json;

namespace GlisterBot.Commands.Wordbomb;

public class WordbombPattern(string pattern, List<string> words)
{
    public string Phrase { get; set; } = pattern;
    private List<string> Words { get; set; } = words;

    public bool Matches(string word)
    {
        return Words.Contains(word);
    }
}

public class WordbombPatternManager
{
    private List<string> patterns;
    WordbombDifficulty difficulty;
    WordbombLanguage language;

    private static void UpdatePhraseCache(string langShort)
    {
        string json = File.ReadAllText($"{Configuration.StaticFilesDir}/wordbomb/words/{langShort}.json");
        var words = JsonConvert.DeserializeObject<List<string>>(json)
            ?? throw new Exception($"Failed to update pattern cache for language {langShort}");

        if (!Directory.Exists($"{Configuration.DynamicFilesDir}/wordbomb"))
        {
            Directory.CreateDirectory($"{Configuration.DynamicFilesDir}/wordbomb");
        }
        if (!Directory.Exists($"{Configuration.DynamicFilesDir}/wordbomb/words"))
        {
            Directory.CreateDirectory($"{Configuration.DynamicFilesDir}/wordbomb/words");
        }

        string directory = $"{Configuration.DynamicFilesDir}/wordbomb/words/{langShort}";
        if (Directory.Exists(directory))
        {
            Directory.Delete(directory, true);
            Directory.CreateDirectory(directory);
        }

        Dictionary<string, long> counts = [];
        foreach (string word in words)
        {
            for (int patternLen = 2; patternLen <= 3; patternLen++)
            {
                for (int i = 0; i <= word.Length - patternLen; i++)
                {
                    string pattern = word.Substring(i, patternLen);
                    counts[pattern] = counts.GetValueOrDefault(pattern, 0) + 1;
                }
            }
        }
        foreach (WordbombDifficulty difficulty in Enum.GetValues<WordbombDifficulty>())
        {
            Directory.CreateDirectory($"{directory}/{difficulty.ToLowerString()}");
            var maxFreqReciprocal = difficulty.TargetWordFrequencyReciprocal();
            foreach ((string pattern, long count) in counts)
            {
                if (words.Count / count > maxFreqReciprocal) continue;
                List<string> matches = [.. words.Where(w => w.Contains(pattern))];
                using var streamWriter = new StreamWriter($"{directory}/{difficulty.ToLowerString()}/{pattern}.json");
                using var jsonWriter = new JsonTextWriter(streamWriter);
                new JsonSerializer().Serialize(jsonWriter, matches);
            }
        }
    }

    public static void InitializePhraseCache()
    {
        foreach (var file in Directory.GetFiles($"{Configuration.StaticFilesDir}/wordbomb/words"))
        {
            if (!file.EndsWith(".json")) continue;
            string lang = file.Substring(file.Length - 7, 2);
            if (!Directory.Exists($"{Configuration.DynamicFilesDir}/wordbomb/words/{lang}"))
            {
                // Right now I'm too lazy to set up an ILogger
                Console.WriteLine($"Updating phrase cache for language {lang}");
                UpdatePhraseCache(lang);
            }
        }
    }

    public WordbombPatternManager(WordbombDifficulty difficulty, WordbombLanguage language)
    {
        this.difficulty = difficulty;
        this.language = language;
        patterns = Directory.GetFiles($"{Configuration.DynamicFilesDir}/wordbomb/words/{language.ToShortString()}/{difficulty.ToLowerString()}")
            .Where(file => file.EndsWith(".json"))
            .Select(file => file.Substring(file.Length - 7, 2))
            .ToList();
    }

    public WordbombPattern GetRandomPattern()
    {
        string pattern = patterns[new Random().Next(patterns.Count - 1)];
        string json = File.ReadAllText($"{Configuration.DynamicFilesDir}/wordbomb/words/{language.ToShortString()}/{difficulty.ToLowerString()}/{pattern}.json");
        var words = JsonConvert.DeserializeObject<List<string>>(json)
            ?? throw new Exception($"Failed to initialize pattern manager with args {difficulty.ToLowerString()} {language}");
        return new(pattern, words);
    }
}

