using System.Buffers.Binary;
using System.Security.Cryptography;
using System.Text.Json;
using pkNX.Structures;
using pkNX.Structures.FlatBuffers;
using pkNX.Structures.FlatBuffers.LGPE;

if (args.Length > 0 && args[0] == "field-pocket-crosscheck")
{
    if (args.Length != 2)
        throw new ArgumentException("Usage: field-pocket-crosscheck <project-root>");

    var projectRoot = Path.GetFullPath(args[1]);
    var gameRoot = Directory.GetParent(projectRoot)?.FullName
        ?? throw new InvalidOperationException("Project root has no parent game directory.");
    var ncaRoot = Path.Combine(gameRoot, "1.0.2", "2b7730a9e56498bbafac2002d4908c6b_NCA");
    var romfs = Path.Combine(ncaRoot, "1");
    var mainPath = Path.Combine(ncaRoot, "0", "main");
    var mainHash = Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(mainPath))).ToLowerInvariant();
    const string expectedMainHash = "1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8";
    if (mainHash != expectedMainHash)
        throw new InvalidDataException($"Unexpected main SHA-256: {mainHash}");

    var itemDirectory = Path.Combine(romfs, "bin", "pokelib", "item");
    var fieldPath = Path.Combine(itemDirectory, "field_pocket.dat");
    var fieldBytes = File.ReadAllBytes(fieldPath);
    var fieldHash = Convert.ToHexString(SHA256.HashData(fieldBytes)).ToLowerInvariant();
    const string expectedFieldHash = "07a1d8da834d426c8de16f3c4bd7d28307bc86a9e217ebf5170b09316797402b";
    if (fieldHash != expectedFieldHash)
        throw new InvalidDataException($"Unexpected field_pocket.dat SHA-256: {fieldHash}");

    var fieldJsonPath = Path.Combine(projectRoot, "decoded", "1.0.2", "romfs", "bin", "pokelib", "item", "field_pocket.json");
    using var fieldJson = JsonDocument.Parse(File.ReadAllBytes(fieldJsonPath));
    var fieldRawHex = fieldJson.RootElement.GetProperty("raw_hex").GetString()
        ?? throw new InvalidDataException("field_pocket.json is missing raw_hex.");
    if (!Convert.FromHexString(fieldRawHex).SequenceEqual(fieldBytes))
        throw new InvalidDataException("field_pocket JSON raw_hex does not reproduce its source.");
    var entries = fieldJson.RootElement.GetProperty("entries").EnumerateArray().ToArray();
    if (entries.Length != fieldBytes.Length)
        throw new InvalidDataException("field_pocket entry count does not match the 1.0.2 source length.");

    var mismatches = new List<object>();
    var compared = 0;
    var mismatchCount = 0;
    using var itemRecordHasher = IncrementalHash.CreateHash(HashAlgorithmName.SHA256);
    for (var index = 0; index < fieldBytes.Length; index++)
    {
        var itemPath = Path.Combine(itemDirectory, $"item{index:D3}.dat");
        var itemBytes = File.ReadAllBytes(itemPath);
        if (itemBytes.Length != Item.SIZE)
            throw new InvalidDataException($"Unexpected item record length at index {index}: {itemBytes.Length}");
        itemRecordHasher.AppendData(itemBytes);
        var pocketField = Item.FromBytes(itemBytes).PocketField;
        var rawByte = fieldBytes[index];
        var pocketBits = rawByte & 0x07;
        var entry = entries[index];
        if (entry.GetProperty("item_index").GetInt32() != index
            || entry.GetProperty("raw_byte").GetInt32() != rawByte
            || entry.GetProperty("pocket_field").GetInt32() != pocketBits
            || pocketField != pocketBits)
        {
            mismatchCount++;
            if (mismatches.Count < 16)
                mismatches.Add(new { index, pocket_field = pocketField, pocket_bits = pocketBits });
        }
        compared++;
    }
    var itemRecordsHash = Convert.ToHexString(itemRecordHasher.GetHashAndReset()).ToLowerInvariant();
    const string expectedItemRecordsHash = "c15d85a4aba08aeebdceace89ba5344cd9c5068bef78cc6f448115f462f64e0f";
    if (itemRecordsHash != expectedItemRecordsHash)
        throw new InvalidDataException($"Unexpected ordered item000.dat-item1057.dat SHA-256: {itemRecordsHash}");

    var report = new
    {
        analysis_status = compared == fieldBytes.Length && mismatchCount == 0 ? "CROSS_VALIDATED" : "MISMATCH",
        game_version = "Pokemon Let's Go Pikachu 1.0.2",
        main_sha256 = mainHash,
        field_pocket_sha256 = fieldHash,
        ordered_item000_through_item1057_sha256 = itemRecordsHash,
        pkNX_commit = "d191cd0e5c05f2af81d9a41c1f1d82e6621b351a",
        comparison = "FUN_710071d1b0 raw_byte & 0x07 versus pkNX GameManagerGG Item.PocketField",
        item_records_compared = compared,
        mismatches = mismatchCount,
        mismatch_samples = mismatches,
    };
    Console.WriteLine(JsonSerializer.Serialize(report, new JsonSerializerOptions { WriteIndented = true }));
    if (compared != fieldBytes.Length || mismatchCount != 0)
        Environment.ExitCode = 1;
    return;
}

if (args.Length > 0 && args[0] == "itemhash-probe")
{
    if (args.Length != 2)
        throw new ArgumentException("Usage: itemhash-probe <item_hash_to_index.dat>");

    var path = Path.GetFullPath(args[1]);
    var bytes = File.ReadAllBytes(path);
    if (bytes.Length < sizeof(int))
        throw new InvalidDataException("Source is shorter than the candidate count header.");

    var count = BinaryPrimitives.ReadInt32LittleEndian(bytes);
    if (count <= 0 || bytes.LongLength != sizeof(int) + (long)count * 0x10)
        throw new InvalidDataException("Size does not match the pinned ItemHash8 count/0x10 stride candidate.");

    var firstWords = new List<ulong>(count);
    var secondWords = new List<int>(count);
    var zeroTailCount = 0;
    for (var i = 0; i < count; i++)
    {
        var offset = sizeof(int) + i * 0x10;
        firstWords.Add(BinaryPrimitives.ReadUInt64LittleEndian(bytes.AsSpan(offset, 8)));
        secondWords.Add(BinaryPrimitives.ReadInt32LittleEndian(bytes.AsSpan(offset + 8, 4)));
        if (BinaryPrimitives.ReadUInt32LittleEndian(bytes.AsSpan(offset + 12, 4)) == 0)
            zeroTailCount++;
    }

    // ItemHash8 is only mapped by this pinned pkNX revision for SWSH. This is
    // a cross-version format probe, not an LGPE decoder or semantic claim.
    var pknxMap = ItemHash8.GetItemHashTable(bytes);
    var duplicateSecondWords = secondWords.GroupBy(value => value)
        .Where(group => group.Count() > 1)
        .Select(group => new { value = group.Key, count = group.Count() })
        .ToArray();
    var missingSecondWords = Enumerable.Range(secondWords.Min(), secondWords.Max() - secondWords.Min() + 1)
        .Except(secondWords)
        .ToArray();
    var report = new
    {
        analysis_status = "UNKNOWN",
        applicability = "pkNX ItemHash8 candidate is SWSH-only; LGPE loader/semantics unverified",
        source = path,
        source_bytes = bytes.Length,
        source_sha256 = Convert.ToHexString(SHA256.HashData(bytes)).ToLowerInvariant(),
        candidate_count = count,
        candidate_stride = 0x10,
        size_matches_count_and_stride = true,
        candidate_u64_at_offset_0_distinct_count = firstWords.Distinct().Count(),
        candidate_u32_at_offset_8_distinct_count = secondWords.Distinct().Count(),
        candidate_u32_at_offset_8_min = secondWords.Min(),
        candidate_u32_at_offset_8_max = secondWords.Max(),
        candidate_u32_at_offset_8_zero_count = secondWords.Count(value => value == 0),
        candidate_u32_at_offset_8_duplicates = duplicateSecondWords,
        candidate_u32_at_offset_8_missing_between_min_max = missingSecondWords,
        candidate_zero_tail_count = zeroTailCount,
        pknx_swsH_itemhash8_dictionary_entries = pknxMap.Count,
        pknx_swsH_key_min = pknxMap.Keys.Min(),
        pknx_swsH_key_max = pknxMap.Keys.Max(),
    };
    Console.WriteLine(JsonSerializer.Serialize(report, new JsonSerializerOptions { WriteIndented = true }));
    return;
}

if (args.Length > 0 && args[0] == "battle-pocket-probe")
{
    if (args.Length != 2)
        throw new ArgumentException("Usage: battle-pocket-probe <project-root>");

    var projectRoot = Path.GetFullPath(args[1]);
    var gameRoot = Directory.GetParent(projectRoot)?.FullName
        ?? throw new InvalidOperationException("Project root has no parent game directory.");
    var ncaRoot = Path.Combine(gameRoot, "1.0.2", "2b7730a9e56498bbafac2002d4908c6b_NCA");
    var romfs = Path.Combine(ncaRoot, "1");
    var mainPath = Path.Combine(ncaRoot, "0", "main");
    var mainHash = Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(mainPath))).ToLowerInvariant();
    const string expectedMainHash = "1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8";
    if (mainHash != expectedMainHash)
        throw new InvalidDataException($"Unexpected main SHA-256: {mainHash}");

    var itemDirectory = Path.Combine(romfs, "bin", "pokelib", "item");
    var battlePath = Path.Combine(itemDirectory, "battle_pocket.dat");
    var battleBytes = File.ReadAllBytes(battlePath);
    var battleHash = Convert.ToHexString(SHA256.HashData(battleBytes)).ToLowerInvariant();
    const string expectedBattleHash = "9e7f1132f2a67da6cd4dde7ac5bb9b96e094ca52b346d56c72544c2e885ac226";
    if (battleBytes.Length != 0x422 || battleHash != expectedBattleHash)
        throw new InvalidDataException($"Unexpected battle_pocket.dat length/hash: {battleBytes.Length}/{battleHash}");

    var battleJsonPath = Path.Combine(projectRoot, "decoded", "1.0.2", "romfs", "bin", "pokelib", "item", "battle_pocket.json");
    using var battleJson = JsonDocument.Parse(File.ReadAllBytes(battleJsonPath));
    var battleRawHex = battleJson.RootElement.GetProperty("raw_hex").GetString()
        ?? throw new InvalidDataException("battle_pocket.json is missing raw_hex.");
    if (!Convert.FromHexString(battleRawHex).SequenceEqual(battleBytes))
        throw new InvalidDataException("battle_pocket JSON raw_hex does not reproduce its source.");
    var battleEntries = battleJson.RootElement.GetProperty("entries").EnumerateArray().ToArray();
    if (battleEntries.Length != battleBytes.Length)
        throw new InvalidDataException("battle_pocket entry count does not match the 1.0.2 source length.");
    var battleOutputHash = Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(battleJsonPath))).ToLowerInvariant();

    var mismatches = new List<object>();
    var values = new SortedDictionary<byte, int>();
    var compared = 0;
    var mismatchCount = 0;
    using var itemRecordHasher = IncrementalHash.CreateHash(HashAlgorithmName.SHA256);
    for (var index = 0; index < battleBytes.Length; index++)
    {
        var itemPath = Path.Combine(itemDirectory, $"item{index:D3}.dat");
        var itemBytes = File.ReadAllBytes(itemPath);
        if (itemBytes.Length != Item.SIZE)
            throw new InvalidDataException($"Unexpected item record length at index {index}: {itemBytes.Length}");
        itemRecordHasher.AppendData(itemBytes);
        var pknxPocket = (byte)Item.FromBytes(itemBytes).PocketBattle;
        var sourceValue = battleBytes[index];
        var outputEntry = battleEntries[index];
        values[sourceValue] = values.GetValueOrDefault(sourceValue) + 1;
        if (sourceValue != pknxPocket
            || outputEntry.GetProperty("item_index").GetInt32() != index
            || outputEntry.GetProperty("raw_byte").GetInt32() != sourceValue
            || outputEntry.GetProperty("pocket_battle").GetInt32() != sourceValue)
        {
            mismatchCount++;
            if (mismatches.Count < 16)
                mismatches.Add(new { index, battle_pocket_byte = sourceValue, pknx_pocket_battle = pknxPocket });
        }
        compared++;
    }
    var itemRecordsHash = Convert.ToHexString(itemRecordHasher.GetHashAndReset()).ToLowerInvariant();
    const string expectedItemRecordsHash = "c15d85a4aba08aeebdceace89ba5344cd9c5068bef78cc6f448115f462f64e0f";
    if (itemRecordsHash != expectedItemRecordsHash)
        throw new InvalidDataException($"Unexpected ordered item000.dat-item1057.dat SHA-256: {itemRecordsHash}");

    var report = new
    {
        analysis_status = mismatchCount == 0 && compared == battleBytes.Length ? "CANDIDATE_MATCH" : "UNKNOWN",
        game_version = "Pokemon Let's Go Pikachu 1.0.2",
        applicability = "value-level pkNX match only; no exact-build battle_pocket.dat loader/accessor is established",
        main_sha256 = mainHash,
        source = "bin/pokelib/item/battle_pocket.dat",
        battle_pocket_sha256 = battleHash,
        output_sha256 = battleOutputHash,
        ordered_item000_through_item1057_sha256 = itemRecordsHash,
        pkNX_commit = "d191cd0e5c05f2af81d9a41c1f1d82e6621b351a",
        comparison = "RomFS byte at item index versus pkNX GameManagerGG Item.PocketBattle",
        item_records_compared = compared,
        mismatches = mismatchCount,
        value_counts = values,
        mismatch_samples = mismatches,
    };
    Console.WriteLine(JsonSerializer.Serialize(report, new JsonSerializerOptions { WriteIndented = true }));
    return;
}

var project = args.Length == 0 ? Directory.GetCurrentDirectory() : args[0];
var source = Path.Combine(Directory.GetParent(project)!.FullName,"1.0.2/2b7730a9e56498bbafac2002d4908c6b_NCA/1");
var output = Path.Combine(project,"work/gamedata-crosscheck");
foreach (var language in new[]{"English","Simp_Chinese"}) foreach(var name in new[]{"common/bag","script/master_trainer"}) {
 var path = Path.Combine(source,"bin/message",language,name+".dat");
 var file = new TextFile(File.ReadAllBytes(path), new TextConfig(GameVersion.GP));
 File.WriteAllText(Path.Combine(output,language+"_"+Path.GetFileName(name)+".json"),JsonSerializer.Serialize(new { lines=file.Lines, flags=file.Flags, bytes=file.LineData.Select(Convert.ToHexString).ToArray(),variables=new TextConfig(GameVersion.GP).GetVariableList() }));
}
var personal = new PersonalTable7GG(File.ReadAllBytes(Path.Combine(source,"bin/pokelib/personal/personal_total.bin")));
File.WriteAllText(Path.Combine(output,"personal.json"),JsonSerializer.Serialize(personal.Table));
foreach(var version in new[]{"p","e"}) {
 var archive=FlatBufferConverter.DeserializeFrom<EncounterArchive>(Path.Combine(source,"bin/field/param/encount/encount_data_"+version+".bin"));
 File.WriteAllText(Path.Combine(output,"encount_"+version+".json"),JsonSerializer.Serialize(archive));
}
var itemRaw = File.ReadAllBytes(Path.Combine(source,"bin/pokelib/item/item001.dat"));
var trainerDataRaw = File.ReadAllBytes(Path.Combine(source,"bin/trainer/trainer_data/trainer_data_001.bin"));
var trainerPokeRaw = File.ReadAllBytes(Path.Combine(source,"bin/trainer/trainer_poke/trainer_poke_001.bin"));
var trainerTypeRaw = File.ReadAllBytes(Path.Combine(source,"bin/trainer/trainer_type/trainer_type_001.bin"));
var trainerData = new TrainerData7b(trainerDataRaw);
var trainerSample = new {
    item = Item.FromBytes(itemRaw),
    itemRaw = Convert.ToHexString(itemRaw),
    trainerData,
    trainerDataRaw = Convert.ToHexString(trainerDataRaw),
    trainerParty = TrainerPoke7b.ReadTeam(trainerPokeRaw, trainerData),
    trainerPokeRaw = Convert.ToHexString(trainerPokeRaw),
    trainerClass = new TrainerClass7b(trainerTypeRaw),
    trainerTypeRaw = Convert.ToHexString(trainerTypeRaw),
};
File.WriteAllText(Path.Combine(output,"pknx-trainer-item-sample.json"),JsonSerializer.Serialize(trainerSample));
var item002Raw = File.ReadAllBytes(Path.Combine(source,"bin/pokelib/item/item002.dat"));
var trainerData002Raw = File.ReadAllBytes(Path.Combine(source,"bin/trainer/trainer_data/trainer_data_002.bin"));
var trainerPoke002Raw = File.ReadAllBytes(Path.Combine(source,"bin/trainer/trainer_poke/trainer_poke_002.bin"));
var trainerType002Raw = File.ReadAllBytes(Path.Combine(source,"bin/trainer/trainer_type/trainer_type_002.bin"));
var trainerData002 = new TrainerData7b(trainerData002Raw);
var trainerSample002 = new {
    item = Item.FromBytes(item002Raw),
    itemRaw = Convert.ToHexString(item002Raw),
    trainerData = trainerData002,
    trainerDataRaw = Convert.ToHexString(trainerData002Raw),
    trainerParty = TrainerPoke7b.ReadTeam(trainerPoke002Raw, trainerData002),
    trainerPokeRaw = Convert.ToHexString(trainerPoke002Raw),
    trainerClass = new TrainerClass7b(trainerType002Raw),
    trainerTypeRaw = Convert.ToHexString(trainerType002Raw),
};
File.WriteAllText(Path.Combine(output,"pknx-trainer-item-sample-002.json"),JsonSerializer.Serialize(trainerSample002));
var evo001Raw = File.ReadAllBytes(Path.Combine(source,"bin/pokelib/evolution/evo_001.bin"));
var evo002Raw = File.ReadAllBytes(Path.Combine(source,"bin/pokelib/evolution/evo_002.bin"));
var mega001Raw = File.ReadAllBytes(Path.Combine(source,"bin/pokelib/mega_evolution/mega_001.bin"));
var mega002Raw = File.ReadAllBytes(Path.Combine(source,"bin/pokelib/mega_evolution/mega_002.bin"));
var megaSample = (byte[] raw) => MegaEvolutionSet.ReadArray(raw).Select(x => new {
    x.ToForm, x.Method, x.Argument, raw = Convert.ToHexString(x.Write()),
});
File.WriteAllText(Path.Combine(output,"pknx-evolution-sample.json"),JsonSerializer.Serialize(new {
    evolution001 = new EvolutionSet7(evo001Raw).PossibleEvolutions,
    evolution001Raw = Convert.ToHexString(evo001Raw),
    evolution002 = new EvolutionSet7(evo002Raw).PossibleEvolutions,
    evolution002Raw = Convert.ToHexString(evo002Raw),
    mega001 = megaSample(mega001Raw), mega001Raw = Convert.ToHexString(mega001Raw),
    mega002 = megaSample(mega002Raw), mega002Raw = Convert.ToHexString(mega002Raw),
}));
var staticRaw = File.ReadAllBytes(Path.Combine(source,"bin/script_event_data/event_encount.bin"));
var giftRaw = File.ReadAllBytes(Path.Combine(source,"bin/script_event_data/add_poke.bin"));
var tradeRaw = File.ReadAllBytes(Path.Combine(source,"bin/script_event_data/field_trade_data.bin"));
var staticSample = Enumerable.Range(0,staticRaw.Length/EncounterStatic7b.SIZE).Select(i => {
    var raw = staticRaw.AsMemory(i*EncounterStatic7b.SIZE,EncounterStatic7b.SIZE);
    return new { record = new EncounterStatic7b(raw), raw = Convert.ToHexString(raw.Span) };
}).ToArray();
var giftSample = Enumerable.Range(0,giftRaw.Length/EncounterGift7b.SIZE).Select(i => {
    var raw = giftRaw.Skip(i*EncounterGift7b.SIZE).Take(EncounterGift7b.SIZE).ToArray();
    return new { record = new EncounterGift7b(raw), raw = Convert.ToHexString(raw) };
}).ToArray();
var tradeSample = Enumerable.Range(0,tradeRaw.Length/EncounterTrade7b.SIZE).Select(i => {
    var raw = tradeRaw.Skip(i*EncounterTrade7b.SIZE).Take(EncounterTrade7b.SIZE).ToArray();
    return new { record = new EncounterTrade7b(raw), raw = Convert.ToHexString(raw) };
}).ToArray();
File.WriteAllText(Path.Combine(output,"pknx-encounter-records-sample.json"),JsonSerializer.Serialize(new {
    staticRecords = staticSample, staticRaw = Convert.ToHexString(staticRaw),
    giftRecords = giftSample, giftRaw = Convert.ToHexString(giftRaw),
    tradeRecords = tradeSample, tradeRaw = Convert.ToHexString(tradeRaw),
}));
var moveRaw = File.ReadAllBytes(Path.Combine(source,"bin/pokelib/waza/waza_data.bin"));
var moveLinker = BinLinkerAccessor.Get(moveRaw,"WD");
var moveRecords = new List<Move7>();
var moveRecordRaw = new List<string>();
for(var i=0;i<moveLinker.Length;i++) {
    var raw = moveLinker[i].ToArray();
    moveRecords.Add(new Move7(raw));
    moveRecordRaw.Add(Convert.ToHexString(raw));
}
File.WriteAllText(Path.Combine(output,"pknx-move-sample.json"),JsonSerializer.Serialize(new {
    identifier = moveLinker.Identifier, count = moveLinker.Length,
    moveRaw = Convert.ToHexString(moveRaw), records = moveRecords, recordRaw = moveRecordRaw,
}));
var learnsetRoot = Path.Combine(project,"decoded/1.0.2/romfs/bin/archive/waza_oboe.gfpak.contents");
var learnsetSamples = Directory.EnumerateFiles(learnsetRoot,"*",SearchOption.AllDirectories)
    .Where(path => Path.GetExtension(path).Length == 0)
    .OrderBy(path => path,StringComparer.OrdinalIgnoreCase)
    .Select(path => {
        var raw = File.ReadAllBytes(path);
        var learnset = new Learnset6(raw);
        return new {
            internalPath = Path.GetRelativePath(learnsetRoot,path).Replace('\\','/'),
            count = learnset.Count, moves = learnset.Moves, levels = learnset.Levels,
            raw = Convert.ToHexString(raw), roundTrip = Convert.ToHexString(learnset.Write()),
        };
    }).ToArray();
File.WriteAllText(Path.Combine(output,"pknx-learnsets.json"),JsonSerializer.Serialize(learnsetSamples));
Console.WriteLine("pkNX exports completed: messages, personal, move, wild/static/gift/trade encounters, items, trainers, evolution, and learnsets.");
