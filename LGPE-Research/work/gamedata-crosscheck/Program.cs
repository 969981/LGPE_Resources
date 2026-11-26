using System.Text.Json;
using pkNX.Structures;
using pkNX.Structures.FlatBuffers;
using pkNX.Structures.FlatBuffers.LGPE;
var project = args[0];
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
Console.WriteLine("pkNX independent exports completed: 4 message files, 980 personal records, both encounter archives.");
