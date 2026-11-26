using System.Reflection;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using pkNX.Containers;
using pkNX.Game;
using pkNX.Structures;

if (args.Length != 5)
{
    Console.Error.WriteLine("usage: gamemanagergg-worker <romfs> <exefs> <output-dir> <project-root> <pknx-commit>");
    return 2;
}

var romfs = Path.GetFullPath(args[0]);
var exefs = Path.GetFullPath(args[1]);
var output = Path.GetFullPath(args[2]);
var projectRoot = Path.GetFullPath(args[3]);
var pknxCommit = args[4];
if (!Directory.Exists(romfs) || !Directory.Exists(exefs))
    throw new DirectoryNotFoundException($"Expected existing RomFS and ExeFS directories: {romfs}; {exefs}");
if (!Directory.Exists(projectRoot) || string.IsNullOrWhiteSpace(pknxCommit))
    throw new DirectoryNotFoundException($"Invalid research project root or pkNX commit: {projectRoot}");
Directory.CreateDirectory(output);

var jsonOptions = new JsonSerializerOptions
{
    PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
    IncludeFields = true,
};

string RelativeSource(string path) => Path.GetRelativePath(romfs, path).Replace('\\', '/');
string Hash(byte[] data) => Convert.ToHexStringLower(SHA256.HashData(data));
var mappedInputPaths = new List<string>
{
    Path.Combine(romfs, "bin", "pokelib", "personal", "personal_total.bin"),
    Path.Combine(romfs, "bin", "pokelib", "waza", "waza_data.bin"),
    Path.Combine(romfs, "bin", "archive", "waza_oboe.gfpak"),
};
foreach (var folder in new[]
         {
             Path.Combine(romfs, "bin", "pokelib", "evolution"),
             Path.Combine(romfs, "bin", "pokelib", "mega_evolution"),
         })
{
    if (!Directory.Exists(folder))
        throw new DirectoryNotFoundException(folder);
    mappedInputPaths.AddRange(Directory.EnumerateFiles(folder, "*", SearchOption.AllDirectories));
}
if (mappedInputPaths.Any(path => !File.Exists(path) || new FileInfo(path).LinkTarget is not null))
    throw new InvalidDataException("A mapped GameManagerGG input is missing or is a symbolic link.");
mappedInputPaths = mappedInputPaths.Distinct(StringComparer.OrdinalIgnoreCase)
    .OrderBy(RelativeSource, StringComparer.Ordinal).ToList();
var inputHashes = new SortedDictionary<string, string>(StringComparer.Ordinal);
foreach (var path in mappedInputPaths)
    inputHashes.Add(RelativeSource(path), Hash(File.ReadAllBytes(path)));

// GameLocation's factory assumes a romfs/exefs wrapper and version heuristics.
// The extracted NCA uses 1/ and 0/, so construct it with the exact source dirs and
// explicit Pikachu enum. This subclass deliberately suppresses GameManagerGG's
// SetMitm redirect; all file reads therefore go directly to the given source tree.
var locationCtor = typeof(GameLocation).GetConstructor(
    BindingFlags.Instance | BindingFlags.NonPublic,
    binder: null,
    types: [typeof(string), typeof(string), typeof(GameVersion)],
    modifiers: null) ?? throw new MissingMethodException("Pinned pkNX GameLocation constructor changed.");
var location = (GameLocation)locationCtor.Invoke([romfs, exefs, GameVersion.GP]);
var manager = new ReadOnlyGameManagerGG(location, language: 2);
manager.Initialize();
if (FileMitm.Enabled)
    throw new InvalidOperationException("FileMitm must remain disabled for the read-only worker.");

var outputCounts = new SortedDictionary<string, object>(StringComparer.Ordinal);
var roundTrip = new SortedDictionary<string, object>(StringComparer.Ordinal);

void RegisterInput(string path, byte[]? data = null)
{
    var bytes = data ?? File.ReadAllBytes(path);
    var relative = RelativeSource(path);
    if (!inputHashes.TryGetValue(relative, out var before) || before != Hash(bytes))
        throw new InvalidDataException($"Mapped source changed between snapshot and parse: {relative}");
}
void WriteJsonLines<T>(string name, IEnumerable<T> records)
{
    using var writer = new StreamWriter(Path.Combine(output, name), false, new UTF8Encoding(false));
    foreach (var record in records)
        writer.WriteLine(JsonSerializer.Serialize(record, jsonOptions));
}

// Personal records: pkNX parses the complete 980-entry table; every record is
// serialized back and compared byte-for-byte before it is emitted.
var personalFolder = manager.GetFilteredFolder(GameFile.PersonalStats,
    path => Path.GetFileNameWithoutExtension(path) == "personal_total");
var personalPaths = personalFolder.GetPaths().ToArray();
if (personalPaths.Length != 1)
    throw new InvalidDataException($"Expected one personal_total source, got {personalPaths.Length}.");
var personalPath = personalPaths[0];
var personalRaw = File.ReadAllBytes(personalPath);
RegisterInput(personalPath, personalRaw);
if (manager.Data.PersonalData is not IPersonalTable<PersonalInfo7GG> personalTable)
    throw new InvalidDataException("GameManagerGG returned an unexpected personal table type.");
var personalRoundTrips = 0;
var personalRows = new List<object>(personalTable.Table.Length);
for (var i = 0; i < personalTable.Table.Length; i++)
{
    var offset = checked(i * PersonalInfo7GG.SIZE);
    var raw = personalRaw.AsSpan(offset, PersonalInfo7GG.SIZE).ToArray();
    var rebuilt = ((IPersonalInfoBin)personalTable.Table[i]).Write();
    var exact = raw.AsSpan().SequenceEqual(rebuilt);
    if (!exact)
        throw new InvalidDataException($"Personal record {i} did not round-trip exactly.");
    personalRoundTrips++;
    personalRows.Add(new
    {
        schema = "pknx-gamemanagergg-personal-v1",
        sourcePath = RelativeSource(personalPath),
        sourceSha256 = inputHashes[RelativeSource(personalPath)],
        containerIndex = i,
        byteOffset = offset,
        byteLength = PersonalInfo7GG.SIZE,
        rawHex = Convert.ToHexStringLower(raw),
        parsed = personalTable.Table[i],
    });
}
if (personalRaw.Length != personalTable.Table.Length * PersonalInfo7GG.SIZE)
    throw new InvalidDataException("Personal source has trailing bytes outside pkNX records.");
WriteJsonLines("personal.jsonl", personalRows);
outputCounts["personal"] = personalTable.Table.Length;
roundTrip["personal"] = new { exact = personalRoundTrips, mismatches = 0 };

// WD BinLinker moves: the cache index remains the source index; the complete
// record bytes and pkNX Move7 round-trip are retained.
var moveContainer = manager.GetFile(GameFile.MoveStats);
if (moveContainer.FilePath is null)
    throw new InvalidDataException("pkNX did not retain the move BinLinker source path.");
var moves = manager.Data.MoveData.LoadAll();
var moveRows = new List<object>(moves.Length);
var moveRoundTrips = 0;
for (var i = 0; i < moves.Length; i++)
{
    var raw = moveContainer[i];
    var rebuilt = moves[i].Write();
    if (!raw.AsSpan().SequenceEqual(rebuilt))
        throw new InvalidDataException($"Move record {i} did not round-trip exactly.");
    moveRoundTrips++;
    moveRows.Add(new
    {
        schema = "pknx-gamemanagergg-move-v1",
        sourcePath = RelativeSource(moveContainer.FilePath),
        sourceSha256 = inputHashes[RelativeSource(moveContainer.FilePath)],
        containerIndex = i,
        rawHex = Convert.ToHexStringLower(raw),
        parsed = moves[i],
    });
}
WriteJsonLines("moves.jsonl", moveRows);
RegisterInput(moveContainer.FilePath);
outputCounts["moves"] = moves.Length;
roundTrip["moves"] = new { exact = moveRoundTrips, mismatches = 0 };

// The folder containers define their ordering. Preserve both the exact absolute
// source-relative path and container index for each evolution and mega record.
var evolutionFolder = manager.GetFilteredFolder(GameFile.Evolutions);
var evolutions = manager.Data.EvolutionData.LoadAll();
if (evolutionFolder.Count != evolutions.Length)
    throw new InvalidDataException("Evolution folder/cache count differs.");
var evolutionRows = new List<object>(evolutions.Length);
var evolutionRoundTripMismatches = 0;
for (var i = 0; i < evolutions.Length; i++)
{
    var path = evolutionFolder.GetFileName(i);
    var raw = File.ReadAllBytes(path);
    RegisterInput(path, raw);
    var record = evolutions[i] as EvolutionSet7 ?? throw new InvalidDataException($"Evolution record {i} was not EvolutionSet7.");
    var rebuilt = record.Write();
    var exact = raw.AsSpan().SequenceEqual(rebuilt);
    if (!exact)
        evolutionRoundTripMismatches++;
    evolutionRows.Add(new
    {
        schema = "pknx-gamemanagergg-evolution-v1",
        sourcePath = RelativeSource(path),
        sourceSha256 = Hash(raw),
        containerIndex = i,
        rawHex = Convert.ToHexStringLower(raw),
        roundTripExact = exact,
        parsed = record.PossibleEvolutions.Select(entry => new
        {
            method = (int)entry.Method,
            entry.Argument,
            entry.Species,
            entry.Form,
            entry.Level,
        }).ToArray(),
    });
}
WriteJsonLines("evolution.jsonl", evolutionRows);
outputCounts["evolutionFiles"] = evolutions.Length;
roundTrip["evolution"] = new
{
    exact = evolutions.Length - evolutionRoundTripMismatches,
    mismatches = evolutionRoundTripMismatches,
    note = "pkNX EvolutionSet7 clamps negative signed form bytes while parsing; rawHex retains source bytes.",
};

var megaFolder = manager.GetFilteredFolder(GameFile.MegaEvolutions);
var megaRecords = manager.Data.MegaEvolutionData.LoadAll();
if (megaFolder.Count != megaRecords.Length)
    throw new InvalidDataException("Mega-evolution folder/cache count differs.");
var megaRows = new List<object>(megaRecords.Length);
var megaRoundTripMismatches = 0;
var megaEntryCount = 0;
for (var i = 0; i < megaRecords.Length; i++)
{
    var path = megaFolder.GetFileName(i);
    var raw = File.ReadAllBytes(path);
    RegisterInput(path, raw);
    var records = megaRecords[i];
    megaEntryCount += records.Length;
    var rebuilt = MegaEvolutionSet.WriteArray(records);
    var exact = raw.AsSpan().SequenceEqual(rebuilt);
    if (!exact)
        megaRoundTripMismatches++;
    megaRows.Add(new
    {
        schema = "pknx-gamemanagergg-mega-evolution-v1",
        sourcePath = RelativeSource(path),
        sourceSha256 = Hash(raw),
        containerIndex = i,
        rawHex = Convert.ToHexStringLower(raw),
        roundTripExact = exact,
        parsed = records.Select(entry => new
        {
            entry.ToForm,
            entry.Method,
            entry.Argument,
            rawHex = Convert.ToHexStringLower(entry.Write()),
        }).ToArray(),
    });
}
WriteJsonLines("mega-evolution.jsonl", megaRows);
outputCounts["megaEvolutionFiles"] = megaRecords.Length;
outputCounts["megaEvolutionEntries"] = megaEntryCount;
roundTrip["megaEvolution"] = new { exact = megaRecords.Length - megaRoundTripMismatches, mismatches = megaRoundTripMismatches };

// GFPack exposes stable numeric entry indices and hash metadata, but does not
// expose unhashed internal paths. Keep that path state explicit as UNKNOWN.
var learnsetPack = manager.GetFile(GameFile.Learnsets) as GFPack
    ?? throw new InvalidDataException("GameManagerGG did not return a GFPack for learnsets.");
if (learnsetPack.FilePath is null)
    throw new InvalidDataException("Learnset GFPack has no source file path.");
var learnsets = manager.Data.LevelUpData.LoadAll();
if (learnsets.Length != learnsetPack.Count)
    throw new InvalidDataException("Learnset cache and GFPack counts differ.");
var packRaw = File.ReadAllBytes(learnsetPack.FilePath);
RegisterInput(learnsetPack.FilePath, packRaw);
var learnsetRows = new List<object>(learnsets.Length);
var learnsetRoundTrips = 0;
var learnsetMoveCount = 0;
for (var i = 0; i < learnsets.Length; i++)
{
    var raw = learnsetPack[i];
    var rebuilt = learnsets[i].Write();
    if (!raw.AsSpan().SequenceEqual(rebuilt))
        throw new InvalidDataException($"Learnset GFPack entry {i} did not round-trip exactly.");
    learnsetRoundTrips++;
    learnsetMoveCount += learnsets[i].Moves.Length;
    var packed = learnsetPack.FileTable[i];
    learnsetRows.Add(new
    {
        schema = "pknx-gamemanagergg-learnset-v1",
        sourcePath = RelativeSource(learnsetPack.FilePath),
        sourceSha256 = inputHashes[RelativeSource(learnsetPack.FilePath)],
        containerIndex = i,
        internalPath = (string?)null,
        internalPathStatus = "UNKNOWN_HASH_ONLY",
        absolutePathHashFnv1a64 = learnsetPack.HashAbsolute[i].HashFnv1aPathFull.ToString("x16"),
        compressionType = (int)packed.Type,
        compressedSize = packed.SizeCompressed,
        decompressedSize = packed.SizeDecompressed,
        rawHex = Convert.ToHexStringLower(raw),
        parsed = learnsets[i],
    });
}
WriteJsonLines("learnsets.jsonl", learnsetRows);
outputCounts["learnsetEntries"] = learnsets.Length;
outputCounts["learnsetMoves"] = learnsetMoveCount;
roundTrip["learnsets"] = new { exact = learnsetRoundTrips, mismatches = 0 };

var inputHashesAfter = new SortedDictionary<string, string>(StringComparer.Ordinal);
foreach (var path in mappedInputPaths)
    inputHashesAfter.Add(RelativeSource(path), Hash(File.ReadAllBytes(path)));
var changedPaths = inputHashes.Keys.Union(inputHashesAfter.Keys, StringComparer.Ordinal)
    .Where(path => !inputHashes.TryGetValue(path, out var before)
                   || !inputHashesAfter.TryGetValue(path, out var after)
                   || before != after)
    .OrderBy(path => path, StringComparer.Ordinal).ToArray();
var sourceUnchanged = changedPaths.Length == 0;

var receipt = new
{
    schema = "lgpe-gamemanagergg-worker-v1",
    sourceVersion = "Let's Go Pikachu 1.0.2",
    gameVersionEnum = "GP",
    pknxCommit,
    worker = "scripts/gamemanagergg-worker",
    readOnly = true,
    fileMitmEnabled = FileMitm.Enabled,
    saveAllCalled = false,
    researchProjectRoot = projectRoot,
    sourceRoot = romfs,
    inputFileCount = inputHashes.Count,
    sourceUnchanged,
    changedPaths,
    inputHashesBefore = inputHashes.Select(entry => new { sourcePath = entry.Key, sha256 = entry.Value }).ToArray(),
    inputHashesAfter = inputHashesAfter.Select(entry => new { sourcePath = entry.Key, sha256 = entry.Value }).ToArray(),
    outputCounts,
    roundTrip,
};
File.WriteAllText(Path.Combine(output, "receipt.json"), JsonSerializer.Serialize(receipt, new JsonSerializerOptions(jsonOptions) { WriteIndented = true }));
Console.WriteLine(JsonSerializer.Serialize(new
{
    status = sourceUnchanged ? "DECODED" : "SOURCE_CHANGED",
    outputDirectory = output,
    inputFiles = inputHashes.Count,
    sourceUnchanged,
    changedPaths,
    outputCounts,
    roundTrip,
}));

return sourceUnchanged ? 0 : 5;

sealed class ReadOnlyGameManagerGG(GameLocation location, int language) : GameManagerGG(location, language)
{
    protected override void SetMitm() => FileMitm.Disable();
}
