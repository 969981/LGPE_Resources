using pkNX.Structures;

if (args.Length != 1)
    throw new ArgumentException("Pass one item_hash_to_index.dat path");

var bytes = File.ReadAllBytes(args[0]);
var table = ItemHash8.GetItemHashTable(bytes);
Console.WriteLine($"source_bytes={bytes.Length}");
Console.WriteLine($"pkNX_ItemHash8_dictionary_entries={table.Count}");
Console.WriteLine($"key_min={table.Keys.Min()} key_max={table.Keys.Max()}");
foreach (var row in table.OrderBy(pair => pair.Key).Take(12))
    Console.WriteLine($"key={row.Key} hash=0x{row.Value:x16}");
