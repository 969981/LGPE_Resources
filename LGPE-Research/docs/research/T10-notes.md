# T10 - LGPE 1.0.2 main static analysis

## Target identity and reproducibility

- Target: Let's Go Pikachu 1.0.2, ExeFS path 0/main from NCA folder 2b7730a9e56498bbafac2002d4908c6b_NCA.
- Input SHA-256: 1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8.
- Ghidra: 12.2 PUBLIC; Nintendo Switch Binary loader from Ghidra-Switch-Loader commit 5d80d195bf284f8ad5f2f9b66c3bdd5c67dd66a6, extension build SHA-256 361b30c46ca41fc3ec479f34857d7fa8d0ae15caefffe1ba64687f38ef0c7cbe.
- Build runtime: Temurin JDK 25.0.5+8 and Gradle 9.1.0. Ghidra 12.2 required Java 25 and Gradle 9.1+. The pinned loader source's legacy Gradle calls were locally adapted in the ignored tools/src clone to build against this installed Ghidra; no upstream source change was committed.
- Exact imported program is main in the ignored Ghidra project work/ghidra-main/project/LGPE102-main. Headless automatic analysis completed and saved successfully. The explicit loader option was rejected by this loader; automatic loader selection chose the Switch Binary loader and recognized NSO.
- The source main file was opened read-only by Ghidra; its recorded input hash still matches.

## Loaded segments

| Segment | Start | End (exclusive) |
|---|---:|---:|
| .text | 0x7100000000 | 0x7100d2fa78 |
| .rodata | 0x7100d33000 | 0x7100d33060 |
| .rodata.1 | 0x7100ef90eb | 0x710152617c |
| .data | 0x7101527000 | 0x71015f8f58 |
| .data.1 | 0x71015f90e8 | 0x71015f9138 |
| .data.2 | 0x710160c020 | 0x710160c030 |
| .bss | 0x710160d000 | 0x7101ee06f8 |

## String and cross-reference evidence

The post-analysis script scripts/ghidra/FindDataLoaderStrings.java searched defined strings for data paths and C++ RTTI markers. Results are saved in the ignored run log logs/ghidra-main-xrefs.log; the run summary is 20 matching strings and 9 references.

| Exact string | Address | Referencing function entry | Evidence |
|---|---:|---:|---|
| bin/field/param/encount/encount_data_p.bin | 0x7100efdbe8 | 0x710012a730 | Two code references at 0x710012b8a0 and 0x710012b908 |
| bin/pokelib/personal | 0x7100f02955 | 0x71001d3730 | One reference at 0x71001d3f58 |
| bin/pokelib/personal/monsname_hash_param.bin | 0x7100f02a59 | 0x71001d7210 | One reference at 0x71001d72b8 |
| personal_total.bin | 0x7100f1f4ab | 0x710073b330 | One reference at 0x710073b3ac |
| common/bag.dat | 0x7100f1fd13 | 0x7100776e60 | One reference at 0x7100776f4c |

These are version-specific addresses in this imported Let's Go Pikachu 1.0.2 main. The evidence establishes string references and containing function entries only; it does not establish call semantics, runtime loading behavior, table layouts, field meanings, catch/RNG behavior, or that all referenced paths are consumed by these functions. Function names remain Ghidra defaults. No addresses from another game or build were imported.

## RTTI observations and limits

Ghidra emitted demangled-address-table labels for C++ ABI support tables including __class_type_info, __si_class_type_info, and __vmi_class_type_info; defined strings include _ZTVN10__cxxabiv117__class_type_infoE at 0x7100ef3f58 and _ZTVN10__cxxabiv120__si_class_type_infoE at 0x7100ef3f7e. SDK/runtime strings also appear in the script output. These labels are leads for future typeinfo/vtable mapping, not recovered game-class layouts. No class fields or game-specific RTTI hierarchy is claimed.

## Commands

The full import used the local Ghidra headless analyzer with the Switch Loader extension and automatic loader detection. The follow-up cross-reference run reused the saved project and ran:

    analyzeHeadless.bat <project-dir> LGPE102-main -process main -noanalysis -scriptPath <repo>\scripts\ghidra -postScript FindDataLoaderStrings.java

Detailed import and cross-reference logs are kept under ignored logs/; project database and analysis caches remain under ignored work/. Reproduce the source hash first and do not substitute another version's main.


## Instruction and decompiler follow-up

The saved Ghidra database for this exact main was reopened with -noanalysis and two local scripts. Logs are ignored artifacts at logs/ghidra-main-decomp.log, logs/ghidra-main-data-refs.log and logs/ghidra-main-loader-helpers.log. Scripts are scripts/ghidra/InspectLoaderFunctions.java and InspectDataReferences.java. The input main hash remains 1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8.

Confirmed code-level observations:

- Function 0x710012a730 contains the two references to the exact string bin/field/param/encount/encount_data_p.bin. At 0x710012b894-0x710012b8a8 it materializes the pointer to that string and calls 0x7100d2fca8; at 0x710012b908 the string pointer is stored into a stack structure and the code calls 0x7100135960 at 0x710012b90c. The function calls 0x7100135960 at multiple other sites as well. Its decompilation manipulates a byte pointer and opaque object/handle fields; no field semantics or file I/O contract are established by that alone.
- Function 0x71001d3730 contains the literal paths common/monsname.dat, bin/pokelib/personal, and bin/pokelib/evolution. The direct directory-string reference from 0x71001d3f58 stores a pointer into a structure.
- Function 0x71001d7210 passes the exact path bin/pokelib/personal/monsname_hash_param.bin to 0x71000a6140 at 0x71001d72c0. The helper branches on a global string prefix and delegates to other opaque helpers.
- Function 0x710073b330 constructs a path with snprintf("%s%s%s", ..., "personal_total.bin"); the path literal reference is at 0x710073b3ac and the call is at 0x710073b3b8.
- Function 0x7100776e60 contains common/bag.dat, common/iteminfo.dat, and common/iteminfo_short.dat. The data pointers are packaged with constants and passed to 0x71001afb60, which forwards to 0x71001afb70 with mode value 10.

These are exact string references, instruction addresses, call destinations, and Ghidra decompiler output for the recorded 1.0.2 main only. They establish code relationships to path strings and helper calls, not proof that a file was opened at runtime, data structure field meaning, or encounter/catch/RNG behavior. No cross-version addresses were used.

Additional helper decompilation evidence from the same database:

- `0x7100135960` reads a byte pointer from its second argument, branches on the first byte, then accesses opaque object offsets `+0x58`, `+0x60`, and `+0x68` and invokes indirect methods at vtable offsets `+0x10` and `+0x18`. It stores the third argument in an output structure and calls `0x7100025900`. The object type and these fields' meanings remain unknown.
- `0x71000a6140` compares its second argument against a global prefix using `strncmp`; its two paths call `0x71000a6320`/`0x7100027060` or `0x710000b660`, then use the same opaque-object offsets and indirect methods. This is a call/data-flow lead only; it does not establish a filename open or a table schema.

The original instructions, decompiler text, and incoming-call lists are in `logs/ghidra-main-loader-helpers.log`. They were produced by `InspectLoaderFunctions.java` against the saved `main` program, whose hash is listed above. The follow-up call-chain traces are recorded below.

## Comparative PokeLDN reference

The [PokeLDN Let's Go page](https://decryptu.github.io/pokeldn/lgpe_session.html) describes offsets into the decompressed Let's Go Pikachu 1.0.2 `main` and names NCA content ID `2b7730a9e56498bbafac2002d4908c6b`, which matches this local NCA directory. The page does not provide a SHA-256 for its decompressed `main`; its offsets are comparison leads only. No PokeLDN function address or field meaning has been imported into the evidence above. The claims in this note remain limited to the locally hashed `main`, the saved Ghidra database, and the recorded local instruction/decompiler references. No network secrets or key material are copied into the project.

I ran `scripts/ghidra/VerifyReferenceOffsets.java` against the saved local program, whose image base is `0x7100000000`. For each comparison-only offset below, adding that base lands on an actual function entry in this exact local 1.0.2 `main`; the script recorded instruction bytes/disassembly and incoming calls. This verifies address mapping and code presence, not the external page's semantic labels:

| PokeLDN offset | Local Ghidra address | Local evidence |
|---:|---:|---|
| `main+0x116f30` | `0x7100116f30` | Function entry, 272-byte body; two incoming call sites at `0x71004d9510` and `0x71004d9558`. |
| `main+0x1171d0` | `0x71001171d0` | Function entry, 1,004-byte body; three incoming call sites recorded. |
| `main+0x349200` | `0x7100349200` | Function entry; first instructions load `[x19+0x68]`, subtract 3, compare with 6 and branch when out of range. The field meaning is not named. |
| `main+0x34a3d0` | `0x710034a3d0` | Function entry; instructions read bytes `[x19+0x271]` and `[x19+0x272]`, then a word at `[x19+0x74]`; their meanings are not named. |
| `main+0x520c30` | `0x7100520c30` | Function entry; checks a word at `+0x38` and byte at `+0x110`. Called from `0x710051c110`. |
| `main+0x520ce0` | `0x7100520ce0` | Function entry; checks pointers at `+0xb0`/`+0xb8` and compares word `+0x10c` with an argument. Called from `0x710051c110`. |
| `main+0x520d30` | `0x7100520d30` | Function entry; repeats the pointer checks and `+0x10c` comparison, then branches to `0x710051e810`. Called from `0x710051c110`. |

The full local trace is in ignored `logs/ghidra-ref-offsets.log` and `logs/ghidra-ref-offsets-script.log`; the reusable script and project are under `scripts/ghidra/` and ignored `work/`. Reproduction from this checkout: `cmd.exe /c 'D:\Tool\ghidra\ghidra_12.2_PUBLIC\support\analyzeHeadless.bat work\ghidra-main\project LGPE102-main -process main -noanalysis -scriptPath scripts\ghidra -postScript VerifyReferenceOffsets.java -scriptlog logs\ghidra-ref-offsets-script.log -log logs\ghidra-ref-offsets.log'`. The offsets are retained as `main+offset` alongside the actual Ghidra addresses; no offset from another title or build is used.

## Personal data path and buffer handoff — 2026-10-29

I reopened the saved Ghidra program and expanded the function references using
`InspectLoaderFunctions.java`. The program image path still resolves to the
recorded `0/main`; all addresses below are from the Let's Go Pikachu 1.0.2
program with base `0x7100000000` and source SHA-256
`1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8`.

| Local address | `main+offset` | Observed relation |
|---:|---:|---|
| `0x710071d800` | `main+0x71d800` | Guarded initialization; calls the path builder at `0x710071d838`, then passes its result to `FUN_71000adc70` at `0x710071d878`. |
| `0x710073b330` | `main+0x73b330` | Constructs a path ending in `personal_total.bin`, then calls `FUN_71001d88b0` at `0x710073b3c8`. |
| `0x71001d88b0` | `main+0x1d88b0` | Checks a global `data/` prefix; in the non-prefix branch it calls `FUN_71001d89e0` and `FUN_7100027060`, otherwise it calls `FUN_710000b660` and builds an opaque result object. |
| `0x71000adc70` | `main+0xadc70` | Calls `FUN_71000a63a0` with the path/request arguments and stores the resulting object in the caller's structure. |
| `0x71000a63a0` | `main+0xa63a0` | Locks a mutex, checks/updates an indexed cache, creates a request object, and dispatches through `FUN_71000276e0`; the underlying file I/O worker remains unidentified. |

In `FUN_710071d800`, Ghidra's decompilation reads a quantity from the returned
opaque object at `local_188 + 0x160` and a data pointer at `local_188 + 0x170`.
It computes `(__n / 0x54) * 0x54`, requests a buffer of that size, then copies
`__n` bytes from the data pointer. The source `1/bin/pokelib/personal/
personal_total.bin` is **82,320 bytes (`0x14190`)**, exactly **980 × 0x54**,
with SHA-256
`0bd93e9122b1148f5ea844a5fe35334d17680430d9164bce799dd08f6cf3cddf`. The
existing pkNX-backed export has 980 records at 84 bytes each and output SHA-256
`80e4b1a7674146e07b864a1c48ac4101fce18bf9ab3306b049d80d2a1668ad9a`; the
pinned `PersonalInfo7GG.SIZE` is also `0x54` (see T07). This is a strong static
and data-size cross-check for the loader's stride. It does not name the opaque
object fields, show that this code executed at runtime, or prove the lower
resource worker opened a physical file.

The per-function Ghidra call/decompilation log is ignored at
`logs/ghidra-main-loader-chain-v3-app.log`; the saved project's main hash is
unchanged. Reproduce with:

```powershell
cmd.exe /c 'D:\Tool\ghidra\ghidra_12.2_PUBLIC\support\analyzeHeadless.bat work\ghidra-main\project LGPE102-main -process main -noanalysis -scriptPath scripts\ghidra -postScript InspectLoaderFunctions.java -scriptlog logs\ghidra-main-loader-chain-v3-script.log -log logs\ghidra-main-loader-chain-v3-app.log'
```

The encounter loader remains a separate lead: `FUN_710013b650` calls
`FUN_710012a730` at `main+0x13bd3c`, and that function contains the exact
`encount_data_p.bin` string reference. Its opaque request/data structures have
not yet been resolved to an encounter table or runtime behavior.

## Encounter resource registration trace — 2026-10-29

The follow-up used the same saved Ghidra program and rechecked the source image
hash (`1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8`).
The corrected `InspectEncounterLoader.java` script emitted the full 54,119
character decompilation of `FUN_710012a730` (`main+0x12a730`) without the
16,000-character truncation in the earlier general report. The exact string
`bin/field/param/encount/encount_data_p.bin` is at `0x7100efdbe8`; references
inside that function occur at `0x710012b8a0` and `0x710012b908`. The local
disassembly at `main+0x12b880`–`main+0x12b90c` and decompilation show:

1. `0x710012b8a0` supplies the path literal to `strncmp` at `0x710012b8a8`,
   comparing it with the `data/` prefix held in a global pointer.
2. In the matching branch, the literal is placed in a temporary request
   structure and passed to `FUN_7100135960` at `0x710012b90c`.
3. The resulting object is passed to `FUN_71000adc70` at `0x710012b92c`, with
   the first-argument expression `param_1 + 0x3c` in Ghidra's `undefined8 *`
   decompilation. Its member semantics remain unknown.
4. `FUN_71000adc70` calls `FUN_71000a63a0`; that helper's observed dispatch to
   `FUN_71000276e0` is at `0x71000a6a8c`. The separate full decompilation of
   `FUN_71000276e0` shows mutex-protected request bookkeeping and condition
   variable signaling. It does **not** expose the lower-level file worker or
   prove a physical file open.

The unique incoming call to `FUN_710012a730` in the saved analysis is from
`FUN_710013b650` at `main+0x13bd3c`. The caller allocates a `0x1120`-byte
object immediately before that call, initializes it, and stores it in its own
structure. These are static setup and request-registration
observations; they do not prove this code ran during gameplay.

The corresponding read-only RomFS source exists at
`1/bin/field/param/encount/encount_data_p.bin`: 27,848 bytes, SHA-256
`3dac771dffee508ff8fea41d255326640aefb67c88c2d96fd1ecda7b82b1ce46`. The
existing actual decode is `decoded/1.0.2/romfs/bin/field/param/encount/
encount_data_p.json` (70 tables, 1,820 slots including padding), independently
cross-checked against pinned pkNX in T07. The byte-level table schema evidence
is documented there; this Ghidra trace only links the path into an opaque
request member and does not assign those fields runtime meanings.

The complete decompilation and dispatcher trace are reproducible with:

```powershell
cmd.exe /c 'D:\Tool\ghidra\ghidra_12.2_PUBLIC\support\analyzeHeadless.bat work\ghidra-main\project LGPE102-main -process main -noanalysis -scriptPath scripts\ghidra -postScript InspectEncounterLoader.java -scriptlog logs\ghidra-encounter-loader-script.log -log logs\ghidra-encounter-loader-app.log'
cmd.exe /c 'D:\Tool\ghidra\ghidra_12.2_PUBLIC\support\analyzeHeadless.bat work\ghidra-main\project LGPE102-main -process main -noanalysis -scriptPath scripts\ghidra -postScript InspectResourceDispatcher.java -scriptlog logs\ghidra-resource-dispatch-script.log -log logs\ghidra-resource-dispatch-app.log'
```

Both commands exited successfully against the saved project. The reusable
scripts are tracked under `scripts/ghidra/`; generated logs and the Ghidra
database remain ignored local artifacts. T10 stays `IN_PROGRESS`: the lower
file-read worker, encounter consumer, RNG/catch/trade/GO Park paths, and runtime
execution evidence remain open.

## Queue consumer and file API boundary — 2026-10-29

The next trace followed `nn::os::WaitConditionVariable` references in this
same image. `FUN_7100020f30` (`main+0x20f30`) waits on a condition variable,
removes request pointers from a queue, and invokes `FUN_710001d3c0` at
`0x7100020f8c`. The latter iterates callback objects and calls
`FUN_710001d430`; neither function's full decompilation shows a direct
`nn::fs::OpenFile` or `nn::fs::ReadFile` call. This supports an asynchronous
request/completion path, not a demonstrated filesystem read for the encounter
request.

Separate version-specific references establish that the image contains
filesystem wrappers: `FUN_71000238e0` calls the named `nn::fs::OpenFile` at
`0x7100023940` and then `nn::fs::GetFileSize`; `FUN_7100023990` calls
`nn::fs::ReadFile` at `0x71000239e8`. Those helpers use fields from opaque
objects and have multiple callers. `FUN_71006777e0` also constructs a path and
calls `nn::fs::OpenFile`, but its current incoming-reference chain is through
`FUN_7100675770`, separate from the encounter path trace. A scan of named
filesystem functions found 18 SDK/import symbols, including these open/read
entries. No direct cross-reference or recovered vtable edge yet connects the
specific `encount_data_p.bin` request object to these generic open/read
helpers. That was the boundary of this earlier trace; the focused follow-up
below first resolved a conditional request-to-`OpenFile` edge. The additional
vtable-target trace at the end of that follow-up now resolves its `+0x40`
method to the `ReadFile` helper as well; runtime execution remains unverified.

The request-creation link is visible in the saved decompilation of
`FUN_71000a63a0`: it initializes a request object with `FUN_7100023680`, stores
the sixth argument at object offset `+0x148` through `FUN_71000237c0`, and
enqueues that object through `FUN_71000276e0` at `0x71000a6a8c`. For the
encounter callsite, the fifth argument to `FUN_71000adc70` is zero, so this
offset should not be described as holding the path itself. The path is carried
through the other copied request fields; their type and exact consumer remain
unresolved.

These additional successful headless runs use the same database and exact
`main` identity:

```powershell
cmd.exe /c 'D:\Tool\ghidra\ghidra_12.2_PUBLIC\support\analyzeHeadless.bat work\ghidra-main\project LGPE102-main -process main -noanalysis -scriptPath scripts\ghidra -postScript FindConditionWaiters.java -scriptlog logs\ghidra-condition-waiters-script.log -log logs\ghidra-condition-waiters-app.log'
cmd.exe /c 'D:\Tool\ghidra\ghidra_12.2_PUBLIC\support\analyzeHeadless.bat work\ghidra-main\project LGPE102-main -process main -noanalysis -scriptPath scripts\ghidra -postScript FindFilesystemFunctions.java -scriptlog logs\ghidra-filesystem-functions-script.log -log logs\ghidra-filesystem-functions-app.log'
cmd.exe /c 'D:\Tool\ghidra\ghidra_12.2_PUBLIC\support\analyzeHeadless.bat work\ghidra-main\project LGPE102-main -process main -noanalysis -scriptPath scripts\ghidra -postScript InspectResourceWorker.java -scriptlog logs\ghidra-resource-worker-v4-script.log -log logs\ghidra-resource-worker-v4-app.log'
```

This extends the static request chain but does not change file decoder counts
or establish live execution. T10 remains `IN_PROGRESS`; the resource consumer,
encounter runtime semantics, and catch/RNG/trade/GO Park paths remain open.

## Encounter request to conditional OpenFile dispatch — 2026-10-29

This follow-up used the same saved Ghidra program and rechecked the exact
Let's Go Pikachu 1.0.2 `main` identity above. The read-only headless runs
`InspectResourceWorker.java` v11/v12, `InspectResourceVtables.java` v2, and
`FindVirtualSlot38Calls.java` completed successfully. Their ignored output logs
are `logs/ghidra-resource-worker-v11-app.log`,
`logs/ghidra-resource-worker-v12-app.log`,
`logs/ghidra-resource-vtables-v2-app.log`, and `logs/ghidra-slot38-app.log`.
The reusable Ghidra scripts are tracked in `scripts/ghidra/`.

The static chain is now connected through the open call on one conditional
dispatch path:

| Local address | `main+offset` | Locally observed evidence |
|---:|---:|---|
| `0x7100efdbe8` | `.rodata.1` | Exact string `bin/field/param/encount/encount_data_p.bin`; in `FUN_710012a730` it is passed to `FUN_7100135960` at `0x710012b90c`. |
| `0x710001dd60` | `main+0x1dd60` | Copies the path to a buffer at object `+0x70`, stores its pointer at `+0x60`, length at `+0x68`, and computes the path hash. |
| `0x7100135960` | `main+0x135960` | Calls `FUN_710001e080` for the exact nonempty path and returns that cached path object in the request descriptor. |
| `0x71000adc70` | `main+0xadc70` | Encounter callsite passes the descriptor to `FUN_71000a63a0`. |
| `0x71000a63a0` | `main+0xa63a0` | `FUN_7100023680` copies descriptor field 0 to request `+0x60`; then assigns request vptr `PTR_DAT_71015fb380 + 0x10` and passes the request to `FUN_71000276e0` at `0x71000a6a8c`. |
| `0x71000276e0` | `main+0x276e0` | The submitted request is `param_2`. When `FUN_7100022c40(param_1)` is true, control reaches the indirect call through `(*param_2 vptr)+0x38` at `0x71000278f4`–`0x71000278fc`. Otherwise this function stores the request in its queue and signals a condition variable. |
| `0x7101528830` | `.data` vtable slot | Global `0x71015fb380` contains pointer `0x71015287e8`; the request vptr is `0x71015287f8`; its slot `+0x38` at `0x7101528830` contains `0x7100026070` (`FUN_7100026070`). |
| `0x7100026070` | `main+0x26070` | Calls `FUN_71000238e0`, then virtual slot `+0x40`, then `FUN_7100023970`. |
| `0x7101528838` | `.data` vtable slot | Request vtable slot `+0x40` contains `0x7100026610`; this target was not previously defined as a function and was disassembled separately. |
| `0x71000238e0` | `main+0x238e0` | Reads the path object pointer from request `+0x60`, then the string pointer from path object `+0x60`, and passes that string to `nn::fs::OpenFile` at `0x7100023940`; on success it calls `nn::fs::GetFileSize`. |

This statically connects the exact encounter path to the request object's
conditional virtual dispatch and to the `OpenFile`/`GetFileSize` helper. It
does not establish that the predicate selected the immediate-dispatch branch
at runtime, that the open succeeded, or that the queued alternative completed
the same path. The next subsection resolves the subsequent virtual `+0x40`
operation to the read helper. No live game execution or encounter behavior is
claimed.

Reproduce the focused runs from this checkout with:

```powershell
cmd.exe /c 'D:\Tool\ghidra\ghidra_12.2_PUBLIC\support\analyzeHeadless.bat work\ghidra-main\project LGPE102-main -process main -noanalysis -scriptPath scripts\ghidra -postScript InspectResourceWorker.java -scriptlog logs\ghidra-resource-worker-v12-script.log -log logs\ghidra-resource-worker-v12-app.log'
cmd.exe /c 'D:\Tool\ghidra\ghidra_12.2_PUBLIC\support\analyzeHeadless.bat work\ghidra-main\project LGPE102-main -process main -noanalysis -scriptPath scripts\ghidra -postScript InspectResourceVtables.java -scriptlog logs\ghidra-resource-vtables-v2-script.log -log logs\ghidra-resource-vtables-v2-app.log'
cmd.exe /c 'D:\Tool\ghidra\ghidra_12.2_PUBLIC\support\analyzeHeadless.bat work\ghidra-main\project LGPE102-main -process main -noanalysis -scriptPath scripts\ghidra -postScript FindVirtualSlot38Calls.java -scriptlog logs\ghidra-slot38-script.log -log logs\ghidra-slot38-app.log'
```

The path from the encounter string to the conditional static `OpenFile`
dispatch is established for this exact local build. The following subsection
resolves the `ReadFile` path; runtime branch and I/O verification, encounter
weights and appearance rules, catch/RNG/PID/EC/shiny generation,
trade/GO Park/save interfaces, and broader RTTI/function-field recovery remain
open.

## Resolve the request's read virtual — 2026-10-29

The raw vtable dump at `logs/ghidra-resource-vtables-v3-app.log` records
`0x7100026610` in the request vtable slot at `0x7101528838` (`vptr + 0x40`).
The method was not previously defined as a Ghidra function. The read-only
`InspectVtableTarget.java` run disassembled that exact vtable target in the
saved project and decompiled it as `FUN_7100026610`; it did not modify the
source `main`. The evidence is in the ignored
`logs/ghidra-vtable-target-app.log`.

`FUN_7100026610` obtains/allocates a buffer using request fields `+0x158`,
`+0x160`, and `+0x170`, then directly calls `FUN_7100023990` at
`0x7100026694` with the request pointer, buffer, and requested size. That
helper calls `nn::fs::ReadFile` at `0x71000239e8` when its cache branch does
not satisfy the read. For this encounter request, `FUN_71000adc70` receives a
zero fifth argument at `main+0x12b92c`; `FUN_71000a63a0` forwards that value to
`FUN_71000237c0`, which stores it at request `+0x148`. Thus the cache pointer
tested by `FUN_7100023990` is statically zero for this call path, selecting its
direct `ReadFile` call if control reaches the `+0x40` method.

Combined with the preceding section, the exact local static chain is now:
encounter path literal → cached path object → queued request `+0x60` →
conditional request vtable `+0x38` (`FUN_7100026070`) →
`FUN_71000238e0` (`OpenFile`/`GetFileSize`) → vtable `+0x40`
(`FUN_7100026610`) → `FUN_7100023990` → `nn::fs::ReadFile`. This is a
version-specific code path, not runtime proof: branch selection, successful
open/read, byte contents at runtime, and the behavior of the queued alternative
remain unverified.

The final read-only headless checks were:

```powershell
cmd.exe /c 'D:\Tool\ghidra\ghidra_12.2_PUBLIC\support\analyzeHeadless.bat work\ghidra-main\project LGPE102-main -process main -noanalysis -scriptPath scripts\ghidra -postScript InspectResourceVtables.java -scriptlog logs\ghidra-resource-vtables-v3-script.log -log logs\ghidra-resource-vtables-v3-app.log'
cmd.exe /c 'D:\Tool\ghidra\ghidra_12.2_PUBLIC\support\analyzeHeadless.bat work\ghidra-main\project LGPE102-main -process main -noanalysis -scriptPath scripts\ghidra -postScript InspectVtableTarget.java -scriptlog logs\ghidra-vtable-target-script.log -log logs\ghidra-vtable-target-app.log'
```

The path to both file-open and file-read helpers is now statically connected
for the conditional immediate-dispatch branch. T10 remains `IN_PROGRESS`:
runtime branch and successful-I/O verification, encounter weights and appearance rules,
catch/RNG/PID/EC/shiny generation, trade/GO Park/save interfaces, and broader
RTTI/function-field recovery remain open.

## Reliable-message and trade-state paths — 2026-10-29

I used the [PokeLDN Let's Go 1.0.2 page](https://decryptu.github.io/pokeldn/lgpe_session.html)
only to select comparison offsets and message labels. Every address below was
then inspected in the local `main` with image base `0x7100000000` and the SHA-256
at the start of this note. No address from another title or executable was
used. The local code evidence is recorded in the ignored
`logs/ghidra-reference-functions-app.log` and
`logs/ghidra-trade-network-app.log`.

### Message queue framing and ordering

- `FUN_7100116f30` (`main+0x116f30`) validates a request/context, writes a
  fixed `0x10`-byte header into object `+0x288`, copies the supplied body after
  it, and passes header plus body to `FUN_71005dd0c0`. The header stores the
  caller-supplied 32-bit identifier at `+0x288`, body length at `+0x28c`, a
  sequence value derived from object `+0x274` at `+0x290`, two one-byte
  arguments at `+0x294/+0x295`, and zero at `+0x296`.
- `FUN_7100117040` (`main+0x117040`), called from that function, wraps the
  identifier and body in a queue allocation of `body_length + 8` bytes and
  copies the payload. The local decompilation establishes the queue structure;
  protocol names remain comparison labels.
- `FUN_71001171d0` (`main+0x1171d0`) searches queued records by the requested
  identifier, checks per-identifier monotonically increasing sequence values,
  filters on record bytes at `+0x14/+0x15`, checks output capacity, and copies
  the body from `+0x18`. Its wrapper `FUN_71001171b0` is called by the
  trade-state receive helper `FUN_71004d9570`.

### Trade-state and offer update evidence

The local function `FUN_7100349200` (`main+0x349200`) is a switch-driven state
machine over a 32-bit field at object `+0x68`. It creates a `0x168`-byte body
in state 5, waits through `FUN_71004d94e0`, receives `0x168`-byte records
through `FUN_71004d9570` in state 7, passes each record to
`FUN_71001c9fe0`, and advances only after two records have been counted. Its
state-3 path initializes/registers a message helper through
`FUN_71004d9030` and `FUN_71004d9450`. The latter calls `FUN_7100116e80` and
stores its returned integer at helper `+0x60`.

`FUN_71004d94e0` directly calls `FUN_7100116f30` with the registered integer,
provided body, length, and trailing values `0, 0xff`. `FUN_71004d9570` routes
receive requests to `FUN_71001171b0`, which reaches the queue parser described
above. The local caller list shows `FUN_7100344370` and
`FUN_7100344450` invoking the `0x349200` state machine.

`FUN_71008f8d70` indexes a record array by its selection argument and, under
its local state checks, calls `FUN_710034a3d0` at `main+0x8f8fb0` with the
selected record. `FUN_710034a3d0` checks state bytes at `+0x271/+0x272`, uses
the word at `+0x74` and helper `FUN_710011b5c0`, then updates a body from
`+0xa0` through `thunk_FUN_7100724770` and sets byte `+0x270`. This is a local
selection/update chain; the description of the object as a trade offer is the
comparison with the linked PokeLDN analysis, not a field name inferred from
these offsets.

### Clone-message dispatch cross-check

The local `FUN_710051c110` (`main+0x51c110`) dispatches on byte values including
`0x81`, `0x83`, `0x84`, `0x91`, and `0xa2`. It calls `FUN_7100520c30` for the
`0x81` path, `FUN_7100520d30` for `0x91`, and `FUN_7100520ce0` for `0xa2`.
Locally, `FUN_7100520c30` advances a sequence-related field at `+0x10c`;
`FUN_7100520ce0` calls `FUN_710051e810` and sets byte `+0x110` when its
argument matches that field; `FUN_7100520d30` calls the same helper under its
pointer and equality checks without setting `+0x110`. These are direct local
references and data flows. PokeLDN's clone-message names are retained only as
an external comparison and are not needed to establish the local switch cases.

These static traces add evidence for the exchange-communication portion of
T10. They do not establish that network code ran on hardware, prove protocol
interoperability, or cover capture/RNG/encounter behavior. Reproduce both
read-only Ghidra passes with:

```powershell
cmd.exe /c 'D:\Tool\ghidra\ghidra_12.2_PUBLIC\support\analyzeHeadless.bat work\ghidra-main\project LGPE102-main -process main -noanalysis -scriptPath scripts\ghidra -postScript InspectReferenceFunctions.java -scriptlog logs\ghidra-reference-functions-script.log -log logs\ghidra-reference-functions-app.log'
cmd.exe /c 'D:\Tool\ghidra\ghidra_12.2_PUBLIC\support\analyzeHeadless.bat work\ghidra-main\project LGPE102-main -process main -noanalysis -scriptPath scripts\ghidra -postScript InspectTradeNetworkFunctions.java -scriptlog logs\ghidra-trade-network-script.log -log logs\ghidra-trade-network-app.log'
```

The original extracted `0/main` remains read-only. Source-wide file counts are
unchanged; T10 remains `IN_PROGRESS` while encounter runtime semantics,
capture/RNG/PID/EC/shiny generation, GO Park and save interfaces, and live
execution evidence remain unverified.

## GO Park resource paths and save-data mount — 2026-10-29

These findings are from the same Let's Go Pikachu 1.0.2 `main` (image base
`0x7100000000`, SHA-256 above). `FindSaveCaptureParkStrings.java` emitted only
matched keyword labels, addresses, and references; it found 204 strings and
129 references. The follow-up local decompilation is in ignored logs
`logs/ghidra-game-transfer-app.log` and `logs/ghidra-save-data-app.log`.

`FUN_7100930060` (`main+0x930060`) and `FUN_7100959950`
(`main+0x959950`) each construct a data request whose path is
`common/go_park.dat`, then call `FUN_71001afb60` with flag `1`. That wrapper
forwards to `FUN_71001afb70` with mode `10` and the low flag bit. This shows
both functions route that localized message table to the data-loading helper;
it does not establish a live open/read or a GO Park transfer operation. The
actual English RomFS pair is present at
`bin/message/English/common/go_park.dat` and `.tbl`. Its existing decoded
output is the path-mirrored
`decoded/1.0.2/romfs/bin/message/English/common/go_park.json`: source/table/
output SHA-256 values are respectively
`78968ab65e8a9855b5f4e94f96f335695449dcb689d8bfa57a02482e28f66f61`,
`b8017314f3dc1aca7703b012e50492d8396974e799394aecc42bd3e8712726b4`, and
`6b2a4bb60ad47d6284175abdc2c0c2ea357a4aef387bf2aabf752febb075b6d3`.
The JSON contains 92 unique IDs; its decode receipt records one unpaired
label. A read-only rehash of all ten localized `go_park.dat` rows found all
ten marked `DECODED` and zero source, companion, or output receipt mismatches.

`FUN_710025aa30` (`main+0x25aa30`) also prepares request records for two
`bin/app/gogopark/particle/...ptcl` paths and passes them to the local resource
helper. `FUN_7100b29280` (`main+0xb29280`) tests an input path for the
`gogo_park` token and, in that branch, builds a field archive path under
`bin/archive/field/` with a `.gfpak` suffix. These are resource/path-selection
observations, not evidence for the GO Park communication or Pokémon-transfer
rules. A separate candidate at `main+0x14cc90` builds an
`nn::prepo::PlayReport`; its Go Park string references are telemetry labels,
not proof of transfer logic.

The save-data search found one direct callsite for the imported
`nn::fs::MountSaveData` in the named-function reference list:
`FUN_7100024d70` (`main+0x24d70`). That worker obtains a queued index under a
mutex, calls `FUN_7100027200`, checks `nn::fs::IsSaveDataExisting` on its
`Uid*` argument, then calls `nn::fs::MountSaveData` only on the existing-save
branch. It records status `3` for the absent branch and `2` after a successful
mount; a nonzero mount result reaches an abort helper. For ordinary indices,
`FUN_7100027200` formats a `save%d` name; index `0xffffffff` follows a separate
global-object branch. This proves a save-data mount in this worker, but its
caller/owner and relation to the player's main save remain unidentified. No
player save record layout or write/commit operation is claimed.

Reproduce the focused passes against the saved Ghidra project with:

```powershell
cmd.exe /c 'D:\Tool\ghidra\ghidra_12.2_PUBLIC\support\analyzeHeadless.bat work\ghidra-main\project LGPE102-main -process main -noanalysis -scriptPath scripts\ghidra -postScript FindSaveCaptureParkStrings.java -scriptlog logs\ghidra-save-capture-park-script.log -log logs\ghidra-save-capture-park-app.log'
cmd.exe /c 'D:\Tool\ghidra\ghidra_12.2_PUBLIC\support\analyzeHeadless.bat work\ghidra-main\project LGPE102-main -process main -noanalysis -scriptPath scripts\ghidra -postScript InspectGameTransferFunctions.java -scriptlog logs\ghidra-game-transfer-script.log -log logs\ghidra-game-transfer-app.log'
cmd.exe /c 'D:\Tool\ghidra\ghidra_12.2_PUBLIC\support\analyzeHeadless.bat work\ghidra-main\project LGPE102-main -process main -noanalysis -scriptPath scripts\ghidra -postScript InspectSaveDataFunctions.java -scriptlog logs\ghidra-save-data-script.log -log logs\ghidra-save-data-app.log'
```

Both function-inspection scripts found all requested targets without
decompiler errors; all three headless passes saved the analysis project.
At the time of this static-analysis pass, before the later T08 R16 retry,
source-wide counts were **SCANNED 27,824; DECODED 20,991; FAILED 1; UNKNOWN
6,755; PENDING 0; UNSUPPORTED 77**. No source binary or decoder output was
modified in this research pass. T10 remains `IN_PROGRESS`: actual save ownership/write calls,
GO Park transfer logic, runtime behavior, and capture/RNG/PID/EC/shiny paths
remain open.

## RNG core and capture script entry points — 2026-10-29

The focused Ghidra passes below used this same saved `main` at image base
`0x7100000000`; its source SHA-256 remains
`1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8`.
`InspectRandomCallers.java` decompiled the core at `0x71004e0150` and its
wrappers. It maintains `0x270` (624) state words plus an index, twists using
word offset `0x18d` (397), and applies tempering shifts/masks
`>> 11`, `0x13a58ad << 7`, `0x1df8c << 15`, and `>> 18`. These constants and
the recurrence match an MT19937-compatible generator (algorithm identification
is an inference from the local instructions and constants). The integer
wrapper `0x71004e0040` lazily seeds this state from
`nn::os::GenerateRandomBytes` and falls back to `0x1105` for a zero seed; the
float wrapper `0x71004e02c0` draws with bound `0x10000` and scales the result.

One caller path, `0x7100cfd450` → `0x7100cfda50`, makes a float comparison
against an opaque member at `+0x24`, optionally draws an integer bounded by
another opaque member at `+0x20`, adds a value at `+0x1c`, then calls
`0x7100d030d0`. Its other observed callers are `0x7100ce67e0` and
`0x7100d004f0`. This is a random selector/callback path, but no local evidence
connects its object fields or callers to Pokémon encounters or capture.
Additional direct callers use the RNG in opaque message/object setup and
helper paths; their fields remain unnamed. They do not establish PID, EC,
shiny, capture probability, or encounter-weight generation.

The script-visible strings `CaptureCall` and `GetCaptureResult` have adjacent
function-pointer entries at `0x710153c880` → `0x71001a61e0` and
`0x710153c890` → `0x71001a64c0`, with string addresses `0x7100f01ba2` and
`0x7100f01bae`. The Ghidra decompilation of `0x71001a61e0` forwards opaque
state to `0x710028fa10`; the getter at `0x71001a64c0` reads opaque globals
and calls `0x71001aae40` / `0x7100672cc0`; the latter stores its 32-bit second
argument at offset `+0xa4` of its first argument. The field meaning remains
unknown. Neither trace exposes a catch formula or a direct call to the RNG
core. The registry-shaped table and
function/string pairing are observed; the surrounding VM semantics are not
fully recovered.

A separate `"PID="` string reference reaches `0x7100500b20`, whose local
decompilation formats `ClientProtocolRequestBroker` endpoint fields `CID`,
`PID`, and `URL`. It is network endpoint logging, not evidence of a Pokémon
PID. This false lead is explicitly excluded from Pokémon PID conclusions.

Reproduce both successful headless passes from the repository root:

```powershell
cmd.exe /c 'D:\Tool\ghidra\ghidra_12.2_PUBLIC\support\analyzeHeadless.bat work\ghidra-main\project LGPE102-main -process main -noanalysis -scriptPath scripts\ghidra -postScript InspectCaptureApiFunctions.java -scriptlog logs\ghidra-capture-api-v6-script.log -log logs\ghidra-capture-api-v6-app.log'
cmd.exe /c 'D:\Tool\ghidra\ghidra_12.2_PUBLIC\support\analyzeHeadless.bat work\ghidra-main\project LGPE102-main -process main -noanalysis -scriptPath scripts\ghidra -postScript InspectRandomCallers.java -scriptlog logs\ghidra-rng-callers-v3-script.log -log logs\ghidra-rng-callers-v3-app.log'
```

Both runs report `Save succeeded for processed file: /main`; the detailed
decompilation and xref output is kept in ignored `logs/`, while the reusable
Ghidra scripts are tracked in `scripts/ghidra/`. The original extracted
`0/main` was not modified. These results narrow one generic RNG path and two
script entry points but leave capture probability, Pokémon PID/EC/shiny
generation, and gameplay/runtime reachability unresolved. Source coverage is
unchanged at **SCANNED 27,824; DECODED 21,068; FAILED 1; UNKNOWN 6,755;
PENDING 0; UNSUPPORTED 0**.

## Capture request-dispatch follow-up — 2026-10-29

The expanded pass followed the `CaptureCall` / `GetCaptureResult` functions
through the request helper and one shared state machine. In the saved Ghidra
reference database, each entry has an incoming reference from its function
pointer slot at `0x710153c880` / `0x710153c890`; no direct code-call reference
was recovered. Because a function table can be dispatched indirectly, this
does not rule out runtime script invocation.

`0x710028fa10` builds a request record and copies `0x99` bytes into pending
request state. Its two branches (`0x710028fd60` and `0x710028fed0`) attach
opaque objects, lock their mutexes, forward two opaque values through
`0x710001c9a0`, and update reference-held state with `0x710013a5e0` or
`0x710013a6b0`. The follow-up decompilation of `0x7100001b80` shows a separate
state machine whose case 3 calls generic wrappers `0x710028f910` or
`0x710028fc10`; it does not directly call either capture-named table entry.
This supports classifying the traced layer as request/state orchestration.
It does not identify the request consumer or establish how a capture result
is computed. `0x7100672cc0` only stores its second argument (`0x0c` at these
sites) at `+0xa4` of its first argument; that field's meaning is unknown.

The expanded pass completed and saved the exact same `main`. Reproduce it
with:

```powershell
cmd.exe /c 'D:\Tool\ghidra\ghidra_12.2_PUBLIC\support\analyzeHeadless.bat work\ghidra-main\project LGPE102-main -process main -noanalysis -scriptPath scripts\ghidra -postScript InspectCaptureApiFunctions.java -scriptlog logs\ghidra-capture-api-v7-script.log -log logs\ghidra-capture-api-v7-app.log'
```

The input hash and source-wide coverage remain unchanged. The capture
probability path, result consumer, RNG linkage, and Pokémon PID/EC/shiny
generation are still unverified.

## Encounter owner and generic RNG selector cross-check — 2026-10-29

These read-only headless passes used the saved Ghidra 12.2 project for the
exact local `0/main`, image base `0x7100000000`, SHA-256
`1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8`. The
post-run Windows `Get-FileHash` returned the same SHA-256 for the original
`0/main`. Both scripts completed without `DECOMPILE_FAILED`, and the analyzer
reported `Save succeeded for processed file: /main`.

The exact encounter-path owner is `FUN_710013b650` (`main+0x13b650`). Its only
direct code xref in the saved project is the call from `FUN_7100005bd0` at
`0x7100005e74`. In the constructor, `0x710013bd3c` allocates a `0x1120`-byte
object and passes it to `FUN_710012a730`, the path-specific request initializer
for `encount_data_p.bin`; the resulting pointer is stored at
`param_1[0x13]` (byte offset `+0x98`). The constructor then calls
`FUN_710013bfa0` at `0x710013bf70`. That helper only links other opaque objects
under mutexes; it reads parent slots `0xa` through `0xd` and does not read the
new encounter-object slot `+0x98`. No encounter record/table access or RNG call
is shown in these functions. This narrows the path to object construction and
registration, but does not identify the encounter consumer.

The RNG follow-up decompiled the immediate parents of the previously found
selector chain:

| Local address | `main+offset` | Local code evidence |
|---:|---:|---|
| `0x7100ce4e90` | `+0xce4e90` | Checks a global flag and timer-like value, traverses linked entries, passes two opaque values to `FUN_7100ce67e0`, and updates the timer-like field. Direct callers are at `0x7100ce4c40` and `0x7100ce4cf8` in `FUN_7100ce4b70`. |
| `0x7100ce67e0` | `+0xce67e0` | Calls `FUN_7100cfd450` at `0x7100ce6844`, then invokes an object callback at vtable offset `+0x38` when the selector succeeds. |
| `0x7100cfd450` | `+0xcfd450` | Walks and updates linked callback entries; calls `FUN_7100cfda50` at `0x7100cfd570` for one entry. |
| `0x7100cfda50` | `+0xcfda50` | Reads opaque fields at `+0x24`, `+0x20`, and `+0x1c`; compares the first value with `FUN_71004e02c0(1.0)`, optionally calls bounded RNG `FUN_71004e0040`, combines the returned value with the `+0x1c` value, and passes it to `FUN_7100d030d0`. |
| `0x7100d030d0` | `+0xd030d0` | Inserts a callback record into an opaque linked collection. The called helper names and object-field meanings remain unresolved. |

The `FUN_7100cfd450` selector also has a separate caller at `0x7100d0051c`
inside `FUN_7100d004f0`, after a state check. This establishes an exact local
RNG-to-callback path, but its fields and owner are not tied to Pokémon
encounters. The two inspected code families contain no direct string reference
to `encount_data_p.bin`, and no static data or call edge joins the selector to
the object created at `+0x98`. Treat its threshold comparison and bounded draw
as generic opaque behavior; they do not support encounter-weight, capture,
PID, EC, or shiny claims.

Reproduce the successful passes from the repository root:

```powershell
cmd.exe /c 'D:\Tool\ghidra\ghidra_12.2_PUBLIC\support\analyzeHeadless.bat work\ghidra-main\project LGPE102-main -process main -noanalysis -scriptPath scripts\ghidra -postScript InspectRngSelectionParents.java -scriptlog logs\ghidra-rng-selection-parents-script.log -log logs\ghidra-rng-selection-parents-app.log'
cmd.exe /c 'D:\Tool\ghidra\ghidra_12.2_PUBLIC\support\analyzeHeadless.bat work\ghidra-main\project LGPE102-main -process main -noanalysis -scriptPath scripts\ghidra -postScript InspectEncounterConsumer.java -scriptlog logs\ghidra-encounter-consumer-v2-script.log -log logs\ghidra-encounter-consumer-v2-app.log'
```

Generated decompilation logs and the Ghidra database remain local ignored
artifacts; the reusable scripts are tracked. Source files and the extracted
`0/main` were not changed. T10 remains `IN_PROGRESS`; the encounter consumer,
encounter weights, live resource behavior, capture result consumer/formula,
and Pokémon PID/EC/shiny generation remain unresolved.

## Script API registry xref follow-up — 2026-10-29

`InspectScriptFunctionRegistry.java` was run in Ghidra 12.2 headless against
the saved exact-build `main` program (image base `0x7100000000`; original
`0/main` SHA-256
`1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8`). The
existing function/name pairs at `0x710153c870`, `0x710153c880`, and
`0x710153c890` resolve respectively to `MapChangeCore_` →
`0x71001a5e80`, `CaptureCall` → `0x71001a61e0`, and `GetCaptureResult` →
`0x71001a64c0`; the latter names are also stored at `0x7100f01ba2` and
`0x7100f01bae`.

The new script searched direct references to the page base and every 4-byte
address in `0x710153c870..0x710153c8ff` (144 bytes), and decompiled the four
functions associated with observed page references. It found one direct
instruction reference into the table range: `0x71001a61d4` computes
`0x710153c878`. Its containing function, `0x71001a61d0`, decompiles to a
return of `&PTR_s_MapChangeCore__710153c878`; this is the `MapChangeCore_`
name pointer. No direct instruction reference to the `CaptureCall` or
`GetCaptureResult` function-pointer entry addresses, and no direct code-call
reference to those function entries, was recovered in this bounded search.
The 14 unique references reported include page-base references outside the
table range. Follow-up context windows for page-base references with no
assigned function show instruction sequences materializing neighboring
page-relative offsets such as `+0xec8`, `+0xf10`, `+0xf58`, and `+0xfa0`,
then storing those addresses in object fields. They do not show an indexed
walk of `0x710153c870..0x710153c8ff`; the mixed/unassigned context at
`0x71001a7e54` is left unclassified.

This is evidence about recovered direct xrefs, not proof that the APIs are
unused: a generic registry walk, indexed lookup, or indirect function-pointer
dispatch may not create a direct reference to an individual entry. The
dispatcher, registration/lookup algorithm, and runtime call site remain
unresolved. The v5 successful run reported `Save succeeded for processed
file: /main`, with no `DECOMPILE_FAILED` records. Its full output is the
ignored `logs/ghidra-script-function-registry-v5-app.log`.

Reproduce from the repository root:

```powershell
cmd.exe /c 'D:\Tool\ghidra\ghidra_12.2_PUBLIC\support\analyzeHeadless.bat work\ghidra-main\project LGPE102-main -process main -noanalysis -scriptPath scripts\ghidra -postScript InspectScriptFunctionRegistry.java -scriptlog logs\ghidra-script-function-registry-v5-script.log -log logs\ghidra-script-function-registry-v5-app.log'
```

The run modified only the ignored Ghidra project; the extracted game files
were not edited. Source coverage is unchanged: **SCANNED 27,824; DECODED
21,068; FAILED 1; UNKNOWN 6,755; PENDING 0; UNSUPPORTED 0; 76,984 registered
outputs**. T10 remains `IN_PROGRESS`.

## Capture helper caller-context follow-up — 2026-10-29

Ghidra's normal full-program analysis was run against the existing saved
`LGPE102-main` project before repeating the incoming-reference query. It
completed and saved `/main`; it emitted multiple constructor-recovery and
unread-address diagnostics, so the changed analysis result is not treated as
complete function recovery. The original extracted `0/main` was rehashed on
Windows afterward and remains
`1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8`.

The updated reference query recovered six additional direct code calls to
`FUN_710028fa10` at `0x710028ab24`, `0x710028ac1c`, `0x7100325390`,
`0x7100327ae0`, `0x7100327f94`, and `0x7100328444`. Ghidra's existing
function map did not assign owners to these call instructions. A follow-up
script scanned up to 512 preceding instructions for frame-prologue
candidates, created local candidate boundaries in the Ghidra database, and
verified that five decompiled candidate bodies include all six calls:

| Candidate entry | Callsite(s) in body | Local decompilation evidence |
|---:|---|---|
| `0x710028a5e0` | `0x710028ab24`, `0x710028ac1c` | State cases pass the 6-byte literal `area01` or 7-byte literal `t001r01` into the shared helper with distinct opaque 64-bit values. |
| `0x7100325054` | `0x7100325390` | State case 5 passes the 7-byte literal `s001r01` with `0xd14712b9aa6e6669`. |
| `0x71003277a4` | `0x7100327ae0` | A parallel state case passes `s001r01` with the same 64-bit value. |
| `0x7100327e68` | `0x7100327f94` | A guarded state branch passes `s001r01` with the same 64-bit value. |
| `0x7100328328` | `0x7100328444` | A guarded state branch passes `s001r01` with the same 64-bit value. |

The literal tokens also occur in the independently extracted 1.0.2 resource
manifest: `area01.gfpak` (179 members), `s001r01.gfpak` (228 members), and
`t001r01.gfpak` (210 members) are all `DECODED`; the `s001r01` and `t001r01`
tokens also appear in their model-directory paths. This confirms the literals
match real ROMFS resource names. It does not prove how the opaque helper
interprets them or establish any request-record field layout.

The helper's local builder `FUN_7100210e20` was also checked in the v7
decompilation. Relative to its destination buffer, it copies one input
64-bit value to `+0x00`, a scalar argument to `+0x08`, two opaque 64-bit pairs
to `+0x20/+0x28` and `+0x30/+0x38`, and copies a source string to `+0x40` with
a `strncpy` bound of `0x40` bytes. These are copy offsets only; no slot meaning
or wider record schema is asserted. The helper later copies `0x99` bytes from
a stack-built region into request state, but that size alone does not identify
the fields or consumer.

The observed literals and call shape show that the helper is shared by more
than the `CaptureCall` wrapper. They do not identify the requests' semantics,
and they do not establish that these other state machines implement capture
or encounter behavior. The first candidate's Ghidra decompilation reports a
type-propagation warning; no `DECOMPILE_FAILED` record occurred. No result
consumer or catch formula was found. These local function boundaries are
analysis aids, not imported symbols. The Ghidra project was changed; the game
source was not.

Reproduce the full automatic analysis and the candidate-parent pass from the
repository root:

```powershell
cmd.exe /c 'D:\Tool\ghidra\ghidra_12.2_PUBLIC\support\analyzeHeadless.bat work\ghidra-main\project LGPE102-main -process main -scriptPath scripts\ghidra -postScript InspectCaptureRequestReferences.java -scriptlog logs\ghidra-capture-request-references-autoanalysis-script.log -log logs\ghidra-capture-request-references-autoanalysis-app.log'
cmd.exe /c 'D:\Tool\ghidra\ghidra_12.2_PUBLIC\support\analyzeHeadless.bat work\ghidra-main\project LGPE102-main -process main -noanalysis -scriptPath scripts\ghidra -postScript InspectCaptureCallsiteParents.java -scriptlog logs\ghidra-capture-callsite-parents-v1-script.log -log logs\ghidra-capture-callsite-parents-v1-app.log'
```

No source coverage changed: **SCANNED 27,824; DECODED 21,068; FAILED 1;
UNKNOWN 6,755; PENDING 0; UNSUPPORTED 0; 76,984 registered outputs**. T10
remains `IN_PROGRESS`. The Python regression suite was rerun after this work:
**82/82 passed**; those tests do not execute Ghidra scripts.

## Capture request byte-span cross-check — 2026-10-29

`InspectOpaqueRequestBuilder.java` was run in Ghidra 12.2 headless with
`-noanalysis` against the saved exact-build `main` (image base `0x7100000000`).
It decompiled the initializer `FUN_7100210de0`, field copier
`FUN_7100210e20`, one-qword wrapper `FUN_710024a4a0`, and request helper
`FUN_710028fa10`; no `DECOMPILE_FAILED` was recorded and the project save
succeeded. The original `0/main` remains the read-only input. The deliberately
excluded `FUN_71002fab90` is a 5,412-byte function whose decompilation expands
to about 58 KB; earlier inspection had already recorded its direct calls to
the same helpers, so omitting that body keeps this reproduction's output
manageable without losing the smaller builder evidence.

The decompiler presents the source of the `memcpy(..., 0x99)` in
`FUN_710028fa10` as `&local_100`. Its visible stack-local sequence is an
8-byte `local_100`, a 4-byte `local_f8`, 16 qwords (`auStack_f0`, 0x80 bytes),
then `local_70`, `local_6e`, `local_6c`, and `local_68`, spanning offsets
`+0x90..+0x98`. The qword array starts at source offset `+0x10`; the final
copy length is 0x99 bytes. This is a compiler/decompiler storage view, not a
recovered C++ request type, and the shown code does not explicitly initialize
every byte in the copied span.

Within that array, the initializer sets qwords `[0]` and `[1]` to
`0xcbf29ce484222645`, writes zero to the low 32 bits of `[2]`, zeros `[4]` and
`[5]`, copies two globals into `[6]` and `[7]`, and zeros `[8]` through `[15]`.
It does not explicitly write `[2]`'s upper 32 bits or `[3]`. The copier then
overwrites `[0]` with one input qword, `[1]` with a scalar argument, `[4]/[5]`
with one input pair, and `[6]/[7]` with another input pair. It copies a string
with `strncpy` bound `0x40` to array offset `+0x40` (slots `[8]..[15]`). These
are observed byte-copy and initialization operations only; none of the
positions is assigned a semantic field name.

At the outer source-span level, `local_100` is first initialized to the same
64-bit constant and later replaced by the qword returned from
`FUN_710024a4a0`; that wrapper zero-initializes one local qword, calls
`FUN_710024a230(&local, 1)`, and returns it. `local_f8` is later assigned the
four-byte `param_7`. The tail stores `0x101` in `local_70`, then updates it
from `param_8` through `CONCAT11(... ) & 0x1ff`; `local_6e` becomes
`param_9 & 1`, `local_6c` is `0xffffffff`, and `local_68` is zero. The
decompiler shows the 0x99-byte span copied either to `lVar7 + 0x40` on the
conditional state branch or to unresolved label `DAT_00000090` on the
fallback branch. This identifies the copy envelope and individual observed
writes, not the consumer's interpretation or API semantics.

Reproduce from the repository root:

```powershell
cmd.exe /c 'D:\Tool\ghidra\ghidra_12.2_PUBLIC\support\analyzeHeadless.bat work\ghidra-main\project LGPE102-main -process main -noanalysis -scriptPath scripts\ghidra -postScript InspectOpaqueRequestBuilder.java -scriptlog logs\ghidra-opaque-request-builder-v2-script.log -log logs\ghidra-opaque-request-builder-v2-app.log'
```

The successful v2 app log reports `Save succeeded for processed file: /main`;
generated logs and the Ghidra database are ignored local artifacts. Source
coverage is unchanged: **SCANNED 27,824; DECODED 21,068; FAILED 1; UNKNOWN
6,755; PENDING 0; UNSUPPORTED 0; 76,984 registered outputs**. This remains a
static exact-build trace; request semantics, dispatch, consumer, and runtime
behavior are unresolved. T10 remains `IN_PROGRESS`.

## Capture-result entry write-path follow-up — 2026-10-29

`InspectCaptureApiFunctions.java` was rerun in Ghidra 12.2 headless (`-noanalysis`)
against the same saved 1.0.2 `main`. The function paired with the registry name
`GetCaptureResult` at `0x71001a64c0` does not return a computed value in its
C-level return; its decompilation returns zero. It reads one qword from
`param_2 + 8`, obtains an opaque state object through `FUN_71001aae40`, then
stores that qword at object-relative `+0xc8` and clears a 16-bit value at
`+0xd0` on the selected-object path. When no selected object is available, the
decompiler instead shows writes to `_DAT_000000c8` and `_DAT_000000d0`.
Finally it calls `FUN_7100672cc0(param_1, 0x0c)`, which stores the 32-bit value
`0x0c` at `param_1 + 0xa4`, and returns zero. These are observed data writes
behind a table entry with that name; they do not prove a result format,
capture-probability calculation, or runtime caller.

The v8 run decompiled this wrapper and its two helpers without a
`DECOMPILE_FAILED` record and saved `/main`. Reproduce from the repository
root:

```powershell
cmd.exe /c 'D:\Tool\ghidra\ghidra_12.2_PUBLIC\support\analyzeHeadless.bat work\ghidra-main\project LGPE102-main -process main -noanalysis -scriptPath scripts\ghidra -postScript InspectCaptureApiFunctions.java -scriptlog logs\ghidra-capture-api-v8-script.log -log logs\ghidra-capture-api-v8-app.log'
```

The exact-build SHA-256 remains
`1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8`.
Source-wide counts remain **SCANNED 27,824; DECODED 21,068; FAILED 1; UNKNOWN
6,755; PENDING 0; UNSUPPORTED 0; 76,984 registered outputs**. T10 remains
`IN_PROGRESS`.

## Pinned PokeLDN RTTI inventory and Ghidra cross-check — 2026-10-29

The public PokeLDN repository was cloned as source only to ignored
`tools/src/pokeldn`, checked out at commit
`0afe6f61f25464767e55b909eef6b260a372bb34`, and its root `LICENSE` identifies
GNU AGPL version 3. The reference page describes Let's Go Pikachu 1.0.2 and
the same NCA content ID as the local dump; its address claims were treated as
leads, not as evidence. No other-build address or field label was imported.

`tools/switch/nso_read.py` read the original local `0/main` without modifying
it. Before and after the run its SHA-256 was
`1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8`. The
script reported NSO segments text `(mem=0x0, size=0xd32ba8)`, rodata
`(mem=0xd33000, size=0x7f317c)`, and data
`(mem=0x1527000, size=0xe5030)`. Its decompressed output is
`work/pokeldn/lgpe-1.0.2-main.bin`, 0x160c030 bytes, SHA-256
`32ff708cc634829aeb2e39a5f39eb156d20e16237c5996f5e1299a905ffe68e9`.
`scripts/research/pokeldn_rtti_inventory.py` independently re-read the NSO
segments with the same pinned parser and checked byte-for-byte equality with
that output before generating the local-only JSONL and Ghidra TSV.

`rtti_names.py` reported 1,365 type_info records, 6,643 named virtual
functions across all namespaces, and 269 `nn::pia` classes with 2,112 named
`nn::pia` virtual-function targets. The local inventory preserves 276
`nn::pia` type_info records (including repeated class names), 472 associated
vtable headers, and 2,729 method-pointer slots. Results retain class/type-info
names and decompressed-main offsets only; they contain no main bytes.

I ran `scripts/ghidra/VerifyPokeLdnRtti.java` against the saved Ghidra 12.2
program for this exact main. The script itself hashed the executable path and
confirmed the expected SHA-256 and image base `0x7100000000`. It matched
276/276 mangled-name strings and relocated name pointers, 472/472 vtable
type_info pointers, and 2,729/2,729 method pointers (`bad=0`). The 2,112
unique method targets include 611 exact function entries and 2,592 decoded
instruction starts in the saved Ghidra program; the remaining entries still
matched their mapped pointer targets, but this pass did not create or infer
function boundaries for them. This validates the RTTI relocation inventory,
not the semantic names of class fields or runtime execution.

The successful command was run through Ghidra 12.2 PUBLIC, JDK 25, and the
installed Switch Loader against `work/ghidra-main/project/LGPE102-main`:

```powershell
python tools\src\pokeldn\tools\switch\nso_read.py `
  ..\1.0.2\2b7730a9e56498bbafac2002d4908c6b_NCA\0\main `
  work\pokeldn\lgpe-1.0.2-main.bin
python scripts/research/pokeldn_rtti_inventory.py `
  ..\1.0.2\2b7730a9e56498bbafac2002d4908c6b_NCA\0\main `
  work\pokeldn\lgpe-1.0.2-main.bin `
  --jsonl manifests\pokeldn-rtti-lgpe-1.0.2.jsonl `
  --ghidra-tsv work\pokeldn\rtti-ghidra.tsv
powershell -File scripts\Run-PokeLdnRttiCheck.ps1
```

The final command invokes `VerifyPokeLdnRtti.java`; the reproducible summary is
in ignored `logs/ghidra-pokeldn-rtti.log` and
`logs/ghidra-pokeldn-rtti-script.log`. The source-revision registry and both
PowerShell/WSL fetch scripts pin PokeLDN at the commit above. This adds static
type-name and vtable relationships to T10. It does not advance capture
probability, encounter consumption, PID/EC/shiny, or runtime claims. Current
source coverage is unchanged: **SCANNED 27,824; DECODED 21,075; FAILED 1;
UNKNOWN 6,748; PENDING 0; UNSUPPORTED 0; 77,696 registered outputs**.

## NEX RTTI and method-pointer follow-up — 2026-10-29

The same pinned PokeLDN RTTI parser was run with prefix `nn::nex` on the same
read-only, exact-hash 1.0.2 main. It identified 269 `nn::nex` class names and
1,388 unique named virtual-function targets. The generated local-only view
contains 324 type-info records, 500 vtable headers, and 2,128 method-pointer
slots. The PowerShell runner accepts `-Prefix nn::nex`; the local Ghidra check
independently matched all 324 name pointers/strings, 500 vtable RTTI pointers,
and 2,128 method pointers with `bad=0`. The program source SHA-256 and image
base were rechecked by the script.

The Ghidra report lists 1,389 unique pointer targets across the NEX vtable
slots although the parser assigned 1,388 `nn::nex` function labels. The single
extra target is `main+0xccf5b0`: PokeLDN's global first-name-wins mapping
labels it `nn::pia::nex::NexNatRelayInterface::vfunc0`, while it also appears
in an `nn::nex` vtable. This is a cross-namespace shared pointer, not a failed
verification and not a recovered semantic method name. Among the 1,388 named
NEX targets, 424 are exact Ghidra function entries with 2,032 decoded
instruction starts; the other targets' pointer values still match mapped
program addresses, but this pass does not assign them function boundaries.

Commands (after `nso_read.py` has produced the expanded image):

```powershell
python scripts/research/pokeldn_rtti_inventory.py `
  ..\1.0.2\2b7730a9e56498bbafac2002d4908c6b_NCA\0\main `
  work\pokeldn\lgpe-1.0.2-main.bin `
  --prefix nn::nex `
  --jsonl manifests\pokeldn-rtti-lgpe-1.0.2-nex.jsonl `
  --ghidra-tsv work\pokeldn\rtti-nex-ghidra.tsv
powershell -File scripts\Run-PokeLdnRttiCheck.ps1 -Prefix nn::nex
```

The generated JSONL and TSV are ignored local artifacts; the successful
Ghidra run summary is in `logs/ghidra-pokeldn-nex-rtti-script.log`. Source
coverage remains **SCANNED 27,824; DECODED 21,075; FAILED 1; UNKNOWN 6,748;
PENDING 0; UNSUPPORTED 0; 77,696 registered outputs**. These names support
exact-build networking-library navigation but do not identify game object
fields or prove that any service executed during play.

## RTTI-named NEX dispatch and trade-offset separation — 2026-10-29

I used the locally generated `nn::nex` inventory to choose three vtable
targets, then checked each vtable slot, code pointer, incoming reference, and
instruction in the same saved Ghidra program. `::vfuncN` below is PokeLDN's
synthetic vtable slot label, not a recovered source method name.

| RTTI slot label | Vtable address point and slot | Target | Local code evidence |
|---|---|---|---|
| `nn::nex::MatchmakeExtensionClient::vfunc8` | `main+0x15ddda8`, slot at `main+0x15dddf0` | `main+0xb36610` | Calls `main+0xb402f0` at `main+0xb36624`, then calls `main+0x50d730` at `main+0xb36638`. |
| `nn::nex::MatchMakingClient::vfunc8` | `main+0x15de260`, slot at `main+0x15de2a8` | `main+0xb402f0` | Calls `main+0x50d730` twice, passing object-relative pointers `+0x20` and `+0xb0`. |
| `nn::nex::SecureConnectionProtocolClient::vfunc23` | `main+0x1589e30`, slot at `main+0x1589ef0` | `main+0x50d730` | Decompilation reads/writes a pointer at `param_1+0x88`, updates a 32-bit value at the referenced object's `+8` using exclusive-monitor atomic sequences, and on one branch sets byte `+0xc`, calls the object's vtable slot at `+8`, then clears the pointer. |

The corresponding incoming DATA references and direct CALL edges are in
`logs/ghidra-pokeldn-method-targets-script.log` and
`logs/ghidra-nex-matchmaking-script.log`; full decompiler output is in
`logs/ghidra-nex-matchmaking-app.log`. These facts establish a static chain
among the RTTI-derived vtable slots and one reference-count-like pointer
update. They do not identify the pointed-to object, its semantic field names,
or a gameplay/trade caller.

This pass also separates two nearby offsets that could otherwise be confused:
PokeLDN's `nn::pia::clone::CloneProtocol::vfunc2` table target is
`main+0x51c100`. In the local database that address contains a `ret` instruction
and has a DATA reference from its vtable slot at `main+0x158aaa8`. The earlier
trade/clone switch is a separate Ghidra function at `main+0x51c110`, sixteen
bytes later, with direct callers at `main+0x51caf8`, `main+0x51cb34`, and
`main+0x51cd14`. The target address is not evidence that this switch is that
virtual method.

Reproduce the version-guarded, read-only passes from the repo root:

```powershell
cmd.exe /c 'D:\Tool\ghidra\ghidra_12.2_PUBLIC\support\analyzeHeadless.bat work\ghidra-main\project LGPE102-main -process main -noanalysis -scriptPath scripts\ghidra -postScript InspectPokeLdnMethodTargets.java -scriptlog logs\ghidra-pokeldn-method-targets-script.log -log logs\ghidra-pokeldn-method-targets.log'
cmd.exe /c 'D:\Tool\ghidra\ghidra_12.2_PUBLIC\support\analyzeHeadless.bat work\ghidra-main\project LGPE102-main -process main -noanalysis -scriptPath scripts\ghidra -postScript InspectNexMatchmakingChain.java -scriptlog logs\ghidra-nex-matchmaking-script.log -log logs\ghidra-nex-matchmaking-app.log'
```

Both scripts re-read and enforce the exact local `main` SHA-256. Source
coverage remains unchanged: **SCANNED 27,824; DECODED 21,075; FAILED 1;
UNKNOWN 6,748; PENDING 0; UNSUPPORTED 0; 77,696 registered outputs**.

## Encounter request-object setup follow-up — 2026-10-29

I used a new version-guarded Ghidra pass to inspect the exact 1.0.2 request
owner, its registration helper, and the helper targets called while configuring
the `0x1120`-byte object. The script checked program base `0x7100000000`, the
local NCA directory identity, and the original `0/main` SHA-256
`1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8`. It
completed with zero decompilation failures and saved `/main` in Ghidra 12.2.

In `FUN_710013b650` (`main+0x13b650`), the code allocates `0x1120` bytes,
calls `FUN_710012a730` (`main+0x12a730`), and stores the resulting pointer at
`param_1[0x13]` (byte offset `+0x98`). A later setup path calls
`FUN_7100146250` (`main+0x146250`), which writes zero to offsets `+0x54`,
`+0x70`, `+0x58`, `+0x60`, and `+0x68` of its argument. The code then loads
two nested pointers from `*(request+0x58)+0xe8` and `*(request+0x58)+0xf0`.
For the first, `FUN_71000a8780` reads a pointer from the source object's
`+0x38a8` subobject at `+0x60`; for the second, `FUN_71000a8790` reads the
`+0x68` pointer. `FUN_71000abb30` and `FUN_71000abb50` copy those pointers and,
when non-null, invoke the pointed object's vtable slot at `+0x10`. The local
setters `FUN_71001ca170` and `FUN_71001c2f30` store the resulting pointers at
child-object `+0x58`; `FUN_71001ca150` and `FUN_71001c2f10` conditionally write
small state bytes at child offsets `+0xe0` and `+0xb0`. The path then calls
`FUN_710013bfa0` (`main+0x13bfa0`). These are observed pointer and state writes;
the fields remain unnamed.

This adds a reproducible setup/registration chain around the request pointer.
It does not identify the pointed objects, decode encounter records, or find a
consumer for the request contents. The pre-existing encounter path also
contains conditional file-I/O helper edges; this follow-up does not establish
which branch runs or whether a runtime read succeeds. No capture, encounter
weight, PID/EC, or shiny semantics are inferred.

Reproduce with the installed Ghidra 12.2 headless analyzer from the repository
root:

```powershell
cmd.exe /c 'D:\Tool\ghidra\ghidra_12.2_PUBLIC\support\analyzeHeadless.bat work\ghidra-main\project LGPE102-main -process main -noanalysis -scriptPath scripts\ghidra -postScript InspectEncounterResourceHelpers.java -scriptlog logs\ghidra-encounter-resource-helpers-script.log -log logs\ghidra-encounter-resource-helpers-app.log'
```

The successful run wrote `PROGRAM` with the expected SHA-256, all requested
functions decompiled, and `Save succeeded for processed file: /main`. Logs are
ignored under `logs/`; the reusable guarded script is tracked. Source coverage
is unchanged at **SCANNED 27,824; DECODED 21,076; FAILED 0; UNKNOWN 6,748;
PENDING 0; UNSUPPORTED 0; 77,697 registered outputs**. T10 remains
`IN_PROGRESS`.

## Encounter read completion and consumer boundary — 2026-10-29

A second version-guarded pass followed the exact encounter request past the
previous `nn::fs::ReadFile` boundary. It used Ghidra 12.2 on the saved local
program with image base `0x7100000000`, NCA identity
`2b7730a9e56498bbafac2002d4908c6b`, and source `main` SHA-256
`1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8`.
Every address below is an offset in this exact Let's Go Pikachu 1.0.2 `main`.

| Address | Locally observed operation |
|---|---|
| `main+0x12b8a0`, `main+0x12b908` | `FUN_710012a730` compares/uses the literal `bin/field/param/encount/encount_data_p.bin`. |
| `main+0x12b90c` | Calls `FUN_7100135960` to produce the path/request descriptor. |
| `main+0x12b92c` | Calls `FUN_71000adc70(param_1 + 0x3c, ..., 0, local_70, 0)`. |
| `main+0x0adc70` | Calls request creation `FUN_71000a63a0`, stores the returned request at callback-subobject `+8` (owner offset `+0x1e8`), optionally registers a completion callback, then waits through `FUN_7100023880`. |
| `main+0x238e0` | Calls `nn::fs::OpenFile` with the path stored through the request object and then calls `nn::fs::GetFileSize`. |
| `main+0x26070` | Calls the open/size helper, then the request's virtual `+0x40` method, then `FUN_7100023970`. |
| `main+0x26610` | Allocates/replaces the read buffer at request `+0x170` and calls `FUN_7100023990`. |
| `main+0x23990` | Uses `nn::fs::ReadFile` when the optional cache does not satisfy the read. The encounter call passes zero for the cache pointer, so this is the direct-read branch if dispatch reaches this method. |
| `main+0x23970` | Calls `nn::fs::CloseFile` when the request's close-state byte permits it; it does not parse the buffer. |

The callback subobject starts at owner offset `+0x1e0` and uses the vtable
address point `0x7101527768`. Its first two slots point to `main+0x93b0` and
`main+0x93d0`, generic wrappers that invoke function objects stored at
subobject offsets `+0x10` and `+0x90`. In the encounter constructor,
corresponding owner fields `param_1[0x3e]` and `param_1[0x4e]` are initialized
to zero and no write to them was found before the `main+0x12b92c` call. The
callback gate in `FUN_71000adc70` therefore does not register a per-request
callback for this construction path; the path waits for request completion.
The request handle is retained at owner offset `+0x1e8`; its read buffer is in
the request object at `+0x170`.

This advances static evidence through allocation, direct-read selection, and
file close, but not to a record consumer. `FUN_710012cee0`, which follows this
configuration routine, loops over `0x93` placement-resource entries and
registers their request/callback objects; that is setup evidence, not proof of
encounter-table parsing. I have not found a function that dereferences this
request's `+0x170` buffer as encounter records, and no live game execution or
successful runtime I/O is claimed. Configuration/loading and record parsing
remain separate in the research ledger.

Reproduce from the repo root with the installed Ghidra 12.2 headless analyzer:

```powershell
cmd.exe /c 'D:\Tool\ghidra\ghidra_12.2_PUBLIC\support\analyzeHeadless.bat work\ghidra-main\project LGPE102-main -process main -noanalysis -scriptPath scripts\ghidra -postScript InspectEncounterReadPath.java -scriptlog logs\ghidra-encounter-read-path-v8-script.log -log logs\ghidra-encounter-read-path-v8-app.log'
```

The tracked script fails closed unless the saved program has the expected base,
NCA path identity, and source hash. The final run reported the expected hash,
zero `DECOMPILE_FAILED` markers, and `Save succeeded for processed file:
/main`. Its logs are ignored under `logs/`. Source/output coverage is unchanged
at **SCANNED 27,824; DECODED 21,076; FAILED 0; UNKNOWN 6,748; PENDING 0;
UNSUPPORTED 0; 77,697 registered outputs**. T10 remains `IN_PROGRESS`.

## Encounter-buffer consumer candidate follow-up — 2026-10-29

This follow-up used Ghidra 12.2 on the same local Let's Go Pikachu 1.0.2
`0/main` (base `0x7100000000`, NCA identity
`2b7730a9e56498bbafac2002d4908c6b`, SHA-256
`1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8`). The
source `main` hash was checked before each script, and the original ExeFS file
still has that hash.

An exact-build instruction scan for the common offsets `+0x1e0`, `+0x1e8`,
`+0x1f0`, `+0x270`, and `+0x170` produced 7,288 matches in 2,217 functions;
this broad result is noisy and does not identify a consumer. Filtering for
non-stack load uses of both `+0x1e8` and `+0x170` reduced the manual review set
to 22 functions. The version-guarded decompiler pass processed all 22 plus the
new direct caller below (23 functions total) with no `DECOMPILE_FAILED`
markers.

| Address | Observed static evidence |
|---|---|
| `main+0x2f8a50` | Directly calls `FUN_71002fdf90` at `main+0x2fdf90` from callsite `main+0x2f8e2c`, after a preceding helper returns zero. The function then calls `FUN_7100300e40`; later calls are gated by opaque state bits. This establishes the local call edge, not runtime reachability. |
| `main+0x2fdf90` | Reads `lVar65 = *(long *)(*param_2 + 0x98)`, then reads the buffer pointer at `*(long *)(lVar65 + 0x1e8) + 0x170`. It traverses offset-based records and calls `FUN_71003154a0` while updating state at `param_1 + 0x80/+0x88`. Ghidra warns that its type-propagation algorithm does not settle. |
| `main+0x13b650` / `main+0x5bd0` | The separate construction trace shows `FUN_7100005bd0` calling `FUN_710013b650`; that constructor allocates the `0x1120`-byte object initialized by `FUN_710012a730` and stores it at its owner's byte offset `+0x98`. `FUN_710012a730` contains the exact `encount_data_p.bin` path and retains a request at object `+0x1e8`, with its buffer at request `+0x170`. |

The actual local `encount_data_p.bin` was read-only checked against the pointer
math in the candidate. Its first four bytes give root offset `0x0c`; at that
root table the signed vtable displacement is `6`, the first vtable field
offset is `4`, and the uoffset stored in that field is `4`, yielding a vector
at file offset `0x14` whose length is `70`. The candidate computes these same
steps from `*buffer`, the root table, its first vtable field, and the vector
length before iterating the vector's 32-bit table offsets. The 70-element root
vector also matches the locally decoded `EncounterArchive` output and pinned
pkNX schema recorded in T07. This is a strong algorithm/schema cross-check for
the candidate, but it does not prove the live buffer passed at `*param_2+0x98`
is this file: the root object identity and runtime branch remain unresolved.

The row loop adds a field-level match. For each 32-bit vector element offset,
the candidate computes the table and its vtable, reads the vtable length at
`vtable+0`, reads the first field offset at `vtable+4`, then reads a 64-bit
value at `table+field0` and compares it with `lVar41`. In the actual first
encounter row, this yields table `0x6b18`, vtable `0x6ac0`, vtable length
`0x58`, object size `0x44`, first field offset `0x38`, and value
`0x8702ad7e67f535c3`; the JSON row has that same value as `ZoneID`. T07's
pinned `wild.fbs` schema names the first field `ZoneID`. This supports an
EncounterArchive lookup candidate at the field level, while the ownership
link and runtime path remain open.

Repeat the read-only source/output check from the repository root with WSL
Python:

```bash
python3 - <<'PY'
import json, struct
from pathlib import Path
src = Path('../1.0.2/2b7730a9e56498bbafac2002d4908c6b_NCA/1/bin/field/param/encount/encount_data_p.bin')
out = Path('decoded/1.0.2/romfs/bin/field/param/encount/encount_data_p.json')
data = src.read_bytes()
root = struct.unpack_from('<I', data, 0)[0]
soffset = struct.unpack_from('<i', data, root)[0]
vtable = root - soffset
field0 = struct.unpack_from('<H', data, vtable + 4)[0]
uoffset = struct.unpack_from('<I', data, root + field0)[0]
vector = root + field0 + uoffset
count = struct.unpack_from('<I', data, vector)[0]
tables = json.loads(out.read_text(encoding='utf-8'))['tables']
assert (root, vtable, field0, uoffset, vector, count) == (12, 6, 4, 4, 20, 70)
assert len(tables) == count
entry = vector + 4
row = entry + struct.unpack_from('<I', data, entry)[0]
row_vtable = row - struct.unpack_from('<i', data, row)[0]
row_vtable_len, row_size = struct.unpack_from('<HH', data, row_vtable)
row_field0 = struct.unpack_from('<H', data, row_vtable + 4)[0]
zone_id = struct.unpack_from('<Q', data, row + row_field0)[0]
assert (row, row_vtable, row_vtable_len, row_size, row_field0) == (0x6b18, 0x6ac0, 0x58, 0x44, 0x38)
assert zone_id == tables[0]['ZoneID'] == 0x8702ad7e67f535c3
print('root/vector/ZoneID cross-check passed:', root, vector, count, row, row_vtable, row_field0, hex(zone_id))
PY
```

The `+0x98 → +0x1e8 → +0x170` chain in `FUN_71002fdf90` matches the
encounter object's registered-buffer layout. However, the candidate obtains
its root from `*param_2`, and this pass did not establish that value as the
owner created by `FUN_710013b650`. The candidate has no direct path-string
reference to `encount_data_p.bin`; its immediate caller has no incoming
reference listed by the saved Ghidra database. An initialized-memory scan for
absolute qword references to the four candidate/helper targets found none;
the same scan found the known `main+0x5bd0` pointer at `0x7101527458`.
Follow-up dword heuristics reported seven candidate occurrences. Five
`.rodata.1` hits point to function starts and have FDE-style range records.
For `main+0x2f8a50`, `main+0x2fdf90`, `main+0x315260`, and `main+0x3154a0`,
the following dword equals the target function's Ghidra body length (`0x41c`,
`0x2ea4`, `0x240`, and `0x16c`). The fifth `.rodata.1` hit is the `5bd0`
positive control and has the same record shape. The remaining two occurrences
are the known `main+0x5bd0` value in `.rela.dyn` and the low dword of its
`.data` pointer. These are metadata/value matches, not dispatch-table
references. The checks found no dispatch-table reference in the tested
absolute-qword and relative-dword forms. At this pointer-scan stage,
`FUN_71002fdf90` remained an **unconfirmed parser candidate**. The later helper
cross-check below confirms a direct static call path into encounter-data
accessors, but not runtime reachability or the identity of the candidate's own
root buffer. No probability weights or broader gameplay semantics are
inferred.

Reproduce from the repository root with the installed Ghidra 12.2 headless
analyzer:

```powershell
cmd.exe /c 'D:\Tool\ghidra\ghidra_12.2_PUBLIC\support\analyzeHeadless.bat work\ghidra-main\project LGPE102-main -process main -noanalysis -scriptPath scripts\ghidra -postScript ScanEncounterFieldOffsetUses.java -scriptlog logs\ghidra-encounter-offset-scan-script.log -log logs\ghidra-encounter-offset-scan-app.log'
cmd.exe /c 'D:\Tool\ghidra\ghidra_12.2_PUBLIC\support\analyzeHeadless.bat work\ghidra-main\project LGPE102-main -process main -noanalysis -scriptPath scripts\ghidra -postScript InspectEncounterHandleCandidates.java -scriptlog logs\ghidra-encounter-handle-candidates-v2-script.log -log logs\ghidra-encounter-handle-candidates-v2-app.log'
cmd.exe /c 'D:\Tool\ghidra\ghidra_12.2_PUBLIC\support\analyzeHeadless.bat work\ghidra-main\project LGPE102-main -process main -noanalysis -scriptPath scripts\ghidra -postScript InspectEncounterRootConstruction.java -scriptlog logs\ghidra-encounter-root-construction-script.log -log logs\ghidra-encounter-root-construction-app.log'
cmd.exe /c 'D:\Tool\ghidra\ghidra_12.2_PUBLIC\support\analyzeHeadless.bat work\ghidra-main\project LGPE102-main -process main -noanalysis -scriptPath scripts\ghidra -postScript ScanEncounterVirtualTargetPointers.java -scriptlog logs\ghidra-encounter-pointer-representations-v3-script.log -log logs\ghidra-encounter-pointer-representations-v3-app.log'
```

The final three runs reported the expected source hash and saved `/main`;
their logs and the earlier offset-scan log are ignored under `logs/`. This
follow-up adds no decoded resource outputs. Coverage remains **SCANNED 27,824;
DECODED 21,076; FAILED 0; UNKNOWN 6,748; PENDING 0; UNSUPPORTED 0; 77,697
registered outputs**. T10 remains `IN_PROGRESS`; the record consumer and
runtime load/selection behavior are unresolved.

## Encounter candidate call-argument follow-up — 2026-10-29

`TraceEncounterCandidateArguments.java` was run with Ghidra 12.2 headless,
`-noanalysis`, against the saved program for the exact local 1.0.2 `main`
(same base, NCA identity, and source hash above). The script checked the source
hash itself, decompiled the parser candidate and its caller, counted direct
incoming references, and printed the callsite instructions. Both
decompilations completed and Ghidra saved `/main`.

The candidate `FUN_71002fdf90` has one direct incoming reference in the saved
Ghidra program: `main+0x2f8e2c`, from `FUN_71002f8a50`. The caller's own direct
incoming-reference count is zero. Its decompilation shows the candidate is
called with the same `param_1` and `param_2` arguments after
`FUN_71002fd8a0(param_1,param_2)` returns zero, followed by
`FUN_7100300e40(param_1,param_2)`. The callsite instructions move `x20` to
`x0` and `x19` to `x1` before the direct branch-and-link. This confirms the
local argument flow into the candidate, but does not identify the caller's
entry/dispatch source or prove the live `*param_2+0x98` object is the
`FUN_710013b650` owner.

The decompiler reuses `lVar41` across disjoint code regions, so its assignment
at line 269 is not the source of the later row-loop comparison. In the path
leading to that lookup, the last displayed assignment before the buffer walk
is `lVar41 = plVar61[0x78]` (byte offset `+0x3c0`); the adjacent mode value is
`iVar38 = (int)plVar61[0x7a]` (byte offset `+0x3d0`). The row loop compares
`lVar41` to the first table field, which the actual archive and pinned schema
identify as `ZoneID`. The later helper call passes that key and flags derived
from `iVar38 == 2` / `iVar38 == 3`. These are observed code/data correspondences;
the opaque object's semantic field names and live identity remain unproven.

Reproduce the version-guarded decompilation and call-argument pass from the
repository root:

```powershell
cmd.exe /c 'D:\Tool\ghidra\ghidra_12.2_PUBLIC\support\analyzeHeadless.bat work\ghidra-main\project LGPE102-main -process main -noanalysis -scriptPath scripts\ghidra -postScript TraceEncounterCandidateArguments.java -scriptlog logs\ghidra-encounter-candidate-arguments-v4-script.log -log logs\ghidra-encounter-candidate-arguments-v4-app.log'
```

The successful run reported the expected source SHA-256, one direct incoming
reference to the candidate, zero to its caller, no `DECOMPILE_FAILED` marker,
and `Save succeeded for processed file: /main`. Logs remain ignored under
`logs/`; no source resources or decoded outputs changed. Coverage remains
**SCANNED 27,824; DECODED 21,076; FAILED 0; UNKNOWN 6,748; PENDING 0;
UNSUPPORTED 0; 77,697 registered outputs**. T10 remains `IN_PROGRESS`.

## Encounter lookup helper cross-check — 2026-10-29

`InspectEncounterLookupHelpers.java` was run with Ghidra 12.2 headless and
`-noanalysis` against the same SHA-guarded 1.0.2 program. It decompiled both
direct callees from the candidate with no failures and saved `/main`.
`FUN_7100315260` has one direct incoming call from the candidate at
`main+0x300bf0`. `FUN_71003154a0` has two direct incoming calls: the candidate
at `main+0x2fe3c0` and `FUN_7100300e40` at `main+0x301210`.

Both helpers load the registered resource through
`PTR_DAT_71015fad08 → +0x98 → +0x1e8 → +0x170`, traverse the root vector, and
compare each row's first field to their second argument. The exact `wild.fbs`
schema at pinned pkNX commit `d191cd0e5c05f2af81d9a41c1f1d82e6621b351a`
identifies that first field as `EncounterTable.ZoneID`. Normalizing the
decompiler's row-base expression (the actual vtable begins four bytes after
its local row-base variable), the selected fields are:

| Helper | Default flags | `param_3` / mode 2 | `param_4` / mode 3 |
|---|---|---|---|
| `FUN_7100315260` | vtable `+0x0e`: `GroundSpawnDuration` (field 5; decompiler offset `+0x12`) | `+0x1e`: `WaterSpawnDuration` (field 13; `+0x22`) | `+0x4c`: `SkySpawnDuration` (field 36; `+0x50`) |
| `FUN_71003154a0` | vtable `+0x10`: `GroundTableEncounterRate` (field 6; decompiler offset `+0x14`) | `+0x20`: `WaterTableEncounterRate` (field 14; `+0x24`) | `+0x4e`: `SkyTableEncounterRate` (field 37; `+0x52`) |

This establishes a static helper-backed consumer of the loaded encounter
archive and exact spawn-duration / encounter-rate field selection. It does not prove the
candidate's own `*param_2+0x98` pointer is the same registered owner, nor that
the orphaned caller `FUN_71002f8a50` is reached at runtime. Therefore the
candidate remains a **static encounter consumer candidate** with runtime
reachability unverified; weights, spawn probabilities, timing, and selection
semantics are not inferred.

The source-to-output field check is reproducible with:

```bash
python3 scripts/research/check_encounter_lookup_fields.py
```

It rehashes the actual source and existing decoded JSON, then checks all 70
tables' `ZoneID`, ground/water/sky spawn durations, and ground/water/sky table
encounter rates, applying FlatBuffers' zero default for absent fields. Result:
**490/490 comparisons matched**;
source SHA-256 `3dac771dffee508ff8fea41d255326640aefb67c88c2d96fd1ecda7b82b1ce46`,
JSON SHA-256 `23e429a0470a356cffe44e323e8977db0e29c94c09937758676051980df077a2`,
and pinned `wild.fbs` SHA-256
`0f1e114b4ef92986bb674c341dfe75e418d257f5d4a2eb6997c8b9ca629e2a1b`.
The helper decompilation command is:

```powershell
cmd.exe /c 'D:\Tool\ghidra\ghidra_12.2_PUBLIC\support\analyzeHeadless.bat work\ghidra-main\project LGPE102-main -process main -noanalysis -scriptPath scripts\ghidra -postScript InspectEncounterLookupHelpers.java -scriptlog logs\ghidra-encounter-lookup-helpers-v1-script.log -log logs\ghidra-encounter-lookup-helpers-v1-app.log'
```

No game resources or registered outputs changed. Coverage remains
**SCANNED 27,824; DECODED 21,076; FAILED 0; UNKNOWN 6,748; PENDING 0;
UNSUPPORTED 0; 77,697 registered outputs**. T10 remains `IN_PROGRESS`.

## Encounter slot selection candidate follow-up — 2026-10-29

A later SHA-guarded Ghidra 12.2 pass expanded the saved exact-hash 1.0.2
program evidence around `FUN_71002fdf90` and decompiled two directly related
helpers. `FUN_7100307010` appends 16-byte records by copying two qwords. In the
parser candidate, the FlatBuffer slot reads map by the pinned `wild.fbs`
schema and binary cross-check: each selected Ground/Water/Sky vector contains
`EncounterSlot` entries; the candidate reads `Species`, `Probability`, and
`Form`, and puts the probability in the second 32-bit word of the packed
candidate record. The later loop begins at `local_100 + 1`, advances four
32-bit words per candidate, accumulates those second words, and compares them
to an RNG-derived sum modulo 100. This is a static implementation observation
from the exact 1.0.2 executable, not proof that this function is active in a
live encounter or that it fully represents the game's encounter probabilities.

The same function reads the Ground, Water, or Sky slot vector according to its
mode branch and reads level-min/max fields from the parent table. An opaque
helper `FUN_71001c4840` supplies `iVar19`; its result 2 changes the candidate's
level handling. The helper checks shorts at `param_1+0x11f8` and `+0x11fa`, but
their meanings and runtime context are not established, so they remain raw
offset observations.

The read-only checker `scripts/research/check_encounter_lookup_fields.py` now
parses the real source FlatBuffer's root vector, every row's Ground/Water/Sky
slot vectors, all 16 checked row scalars, and each slot's Probability, Species,
and Form. It compares those to the existing JSON and the pinned pkNX schema.
The expanded run passed **5,110 scalar comparisons** over **70 zone rows** and
**1,330 slot rows**, plus **210 checks** that each vector’s summed `Probability`
matched its parent `*TableRandChanceTotal`. All matched: Ground totals were 100
for 53 rows and 0 for 17; Water 100 for 21 and 0 for 49; Sky 100 for 41 and
0 for 29. The hashes remain source
`3dac771dffee508ff8fea41d255326640aefb67c88c2d96fd1ecda7b82b1ce46`, decoded
JSON `23e429a0470a356cffe44e323e8977db0e29c94c09937758676051980df077a2`, and
schema `0f1e114b4ef92986bb674c341dfe75e418d257f5d4a2eb6997c8b9ca629e2a1b`.
`python3 -m py_compile scripts/research/check_encounter_lookup_fields.py` also
passed. The full WSL suite passed 102/102 with
`UV_PROJECT_ENVIRONMENT=/tmp/lgpe-research-t07-venv uv run python -m unittest discover -s tests -v`.

Reproduce the decompilation from the repository root:

```powershell
cmd.exe /c 'D:\Tool\ghidra\ghidra_12.2_PUBLIC\support\analyzeHeadless.bat work\ghidra-main\project LGPE102-main -process main -noanalysis -scriptPath scripts\ghidra -postScript TraceEncounterCandidateArguments.java -scriptlog logs\ghidra-encounter-candidate-arguments-v7-script.log -log logs\ghidra-encounter-candidate-arguments-v7-app.log'
```

The command exited 0, checked the expected `main` SHA-256, had no
`DECOMPILE_FAILED` entries, and saved `/main`. Ghidra shows one direct incoming
reference to the candidate at `main+0x2f8e2c` from `main+0x2f8a50`; that caller
has no direct incoming references in the saved database. The candidate's
`*param_2+0x98` root remains unconnected to the registered encounter request
owner, so runtime reachability and active encounter semantics remain open. No
source resources or registered decoded outputs changed; coverage remains
**SCANNED 27,824; DECODED 21,076; FAILED 0; UNKNOWN 6,748; PENDING 0;
UNSUPPORTED 0; 77,697 outputs**. T10 stays `IN_PROGRESS`.


### T10 encounter caller range-record cross-check — 2026-10-29

The SHA-guarded `ScanEncounterVirtualTargetPointers.java` Ghidra pass also
found relative-dword candidates in `.rodata.1` for four exact-build functions:
`main+0x13c3040 → main+0x2f8a50`, `main+0x13c3268 → main+0x2fdf90`,
`main+0x13c45b8 → main+0x315260`, and
`main+0x13c45e0 → main+0x3154a0`. At each entry, the next dword is respectively
`0x41c`, `0x2ea4`, `0x240`, and `0x16c`, matching the four Ghidra function
body byte counts (1052, 11,940, 576, and 364). That adjacency identifies these
hits as function-range metadata candidates, not evidence of an indirect call
or runtime dispatch. Ghidra still reports zero direct incoming references to
`FUN_71002f8a50`; the parser has one direct call from that function. This
rechecks and narrows the earlier relative-pointer scan without changing the
reachability caveat. Reproduce with the existing `ScanEncounterVirtualTargetPointers.java`
headless command in this note and inspect
`logs/ghidra-encounter-pointer-representations-v3-script.log`.

No source files or decoded outputs changed. Coverage remains **SCANNED 27,824;
DECODED 21,076; FAILED 0; UNKNOWN 6,748; PENDING 0; UNSUPPORTED 0;
77,697 registered outputs**. T10 remains `IN_PROGRESS`.

### Derived candidate roll-interval report — 2026-10-29

`UV_PROJECT_ENVIRONMENT=/tmp/lgpe-research-t07-venv uv run lgpe encounter-weights`
ran on the local 1.0.2 inputs and wrote the ignored report files
`manifests/encounter-weight-intervals.csv` and
`manifests/encounter-weight-intervals.json`. The command requires exact SHA-256
matches for `encount_data_p.bin`
(`3dac771dffee508ff8fea41d255326640aefb67c88c2d96fd1ecda7b82b1ce46`), its
mirrored JSON (`23e429a0470a356cffe44e323e8977db0e29c94c09937758676051980df077a2`),
pkNX `wild.fbs`
(`0f1e114b4ef92986bb674c341dfe75e418d257f5d4a2eb6997c8b9ca629e2a1b`, commit
`d191cd0e5c05f2af81d9a41c1f1d82e6621b351a`), and the exact `0/main`
(`1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8`). It
parses the source again and requires the full decoded object to equal the
existing JSON before deriving anything. It also rehashes the source, JSON,
schema, and `main` after processing.

The CSV has **1,330 rows**, one per source slot, including zero-probability
slots. It records the source SHA-256, pkNX commit/schema hash, exact-build
candidate/caller/callsite addresses, zone/table/mode/slot identifiers, each
raw FlatBuffer byte offset, `Probability`, and the half-open candidate roll
interval `[start,end)`. The JSON reports 70 tables, 210 mode/table groups, 95
zero-total groups, and per-mode totals Ground 53×100/17×0, Water 21×100/49×0,
Sky 41×100/29×0. The CSV SHA-256 is
`5fa6e10403634d79d46c822bbfb8fedc622126f0510c332e5094a59528a32b4d`. The CLI
then reopened the CSV and verified **1,330/1,330 rows** and all **210/210
mode/table groups** for contiguous intervals, slot indexes, and matching
probability sums.

This calculation is bounded to the static code at `main+0x2fdf90`: it derives
what each slot's weight maps to if this candidate's `%100` cumulative selector
runs. The caller at `main+0x2f8a50` still has no direct incoming references in
the saved Ghidra database, and the candidate root is not connected to the
constructed encounter resource owner. The report therefore marks every row
`UNVERIFIED_RUNTIME`; it does not claim observed game behavior or a complete
encounter probability model. The separate binary/JSON/schema checker passed
5,110 named field comparisons over 70 tables and 1,330 slots, plus 210
probability-total checks. The report's full parsed JSON comparison covered
7,982 scalar leaves. The full WSL suite passed **105/105**. Source coverage
remains **SCANNED 27,824; DECODED 21,076; FAILED 0; UNKNOWN 6,748; PENDING 0;
UNSUPPORTED 0; 77,697 registered outputs**; this analysis adds no source
decode receipts. T10 remains `IN_PROGRESS`.

### Exact-build encounter mode helper follow-up — 2026-10-29

`InspectEncounterModeHelper.java` was run read-only in Ghidra 12.2 against
the saved program for the local LGPE 1.0.2 `0/main`. The script verifies the
NCA path, image base `0x7100000000`, and full source SHA-256
`1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8` before
using any address. The helper is at `main+0x1c4840` (`0x71001c4840`), has a
68-byte Ghidra body, and decompiled without errors. This pass made no changes
to `main`, the Ghidra project, source resources, or decoded outputs.

The helper reads two signed shorts at opaque byte offsets `+0x11fa` and
`+0x11f8`. Its observed return logic is: return 0 if the value at `+0x11fa`
is below 1; otherwise return 1 when the `+0x11f8` value is 76, 77, or 79;
return 2 when it is 900, 901, or 902; return 0 for other values. These are
direct translations of the decompiler's signed-short loads and unsigned
range checks; neither offset is assigned a field name. A nearby block stores
halfwords into `+0x11fa` and `+0x11f8` at `main+0x1c4824` and
`main+0x1c4828`; the source values and their higher-level meaning were not
traced.

Ghidra reports eight direct incoming references to this helper: callsites at
`main+0x2f6714`, `+0x2f69ac`, `+0x2fe198`, `+0x306720`, and `+0x3153ec`, plus
three references inside regions not assigned a containing function by the
saved database (`main+0x195898`, `+0x1958b8`, `+0x31ce38`). In the static
encounter parser candidate `main+0x2fdf90`, the result is compared with 1 and
2; the `== 2` path adds record-relative checks in three branches and changes
a small selector at the common tail. This ties the helper to candidate parser
control flow but supplies no semantic names for the shorts or records. The
candidate caller still has no direct incoming references and its local root
buffer is still not tied to the constructed encounter owner, so runtime
reachability and gameplay meaning remain unverified.

The guarded script also found 14 instructions whose disassembly text contains
`0x11f8` or `0x11fa`. Nine are in the helper/sibling-function neighborhood;
the rest are separate locations and were not treated as field evidence. The
run decompiled the helper and four callers with zero failures. Reproduce from
the project root in PowerShell 7 with
`powershell.exe -ExecutionPolicy Bypass -File scripts/ghidra/Run-InspectEncounterModeHelper.ps1`.
The script uses the installed Ghidra/Java paths (override parameters if the
local installation differs), reopens `work/ghidra-main/project` with
`-readOnly`, and writes `logs/ghidra-encounter-mode-helper-v1-script.log` plus
the Ghidra application log. It verifies the exact program before printing
decompiler evidence.

No resource decode receipts changed. Current coverage remains **SCANNED
27,824; DECODED 21,076; FAILED 0; UNKNOWN 6,748; PENDING 0; UNSUPPORTED 0;
77,697 registered outputs**. T10 remains `IN_PROGRESS`.

### T10 encounter mode field writer trace — 2026-10-29

The same exact-hash Ghidra script was extended to inspect the function
containing the stores at `main+0x1c4824/+0x1c4828`, then rerun read-only on
the saved LGPE 1.0.2 `main` (SHA-256
`1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8`). The
stores belong to `FUN_71001c47d0` (`main+0x1c47d0`, 100-byte body). Its second
argument is whitelisted to exactly six integers; accepted values are stored
as a signed short at `param_1+0x11f8`, while a paired short is written at
`param_1+0x11fa`:

| Input integer | Stored `+0x11fa` | Setter result |
|---:|---:|---:|
| 76 | 200 | 1 |
| 77 | 200 | 1 |
| 79 | 100 | 1 |
| 900 | 100 | 1 |
| 901 | 200 | 1 |
| 902 | 250 | 1 |
| all other values | unchanged | 0 |

The setter has one direct incoming reference in Ghidra, at
`main+0x1957fc`; Ghidra has not assigned that instruction a containing
function. At the callsite, the instructions load `w1` from `[x20+8]`, move
`x21` into `x0`, and call the setter. The adjacent instructions load `x21`
from `[x8+0x80]` and invoke a vtable method first. This establishes a raw
argument/object flow into the setter, but the source object and the six values
have no verified semantic labels. The helper at `main+0x1c4840` then classifies
the stored short pair into its observed 0/1/2 return values. The parser
candidate's runtime reachability remains unproven.

The modified `scripts/ghidra/InspectEncounterModeHelper.java` still guards the
exact main SHA and the installed runner opens the Ghidra project with
`-readOnly`. A fresh run completed with zero decompile failures and found the
writer/callsite above. The current logged output is
`logs/ghidra-encounter-mode-helper-v1-script.log`; reproduce with
`powershell.exe -ExecutionPolicy Bypass -File scripts/ghidra/Run-InspectEncounterModeHelper.ps1`.
`UV_PROJECT_ENVIRONMENT=/tmp/lgpe-research-t07-venv uv run lgpe coverage`
confirmed SCANNED 27,824; DECODED 21,076; FAILED 0; UNKNOWN 6,748; PENDING 0;
UNSUPPORTED 0; 77,697 output receipts. The full test suite passed **105/105**.
No source resource or decode receipt changed. T10 remains `IN_PROGRESS`.

### T10 encounter auxiliary item cross-check — 2026-10-29

The follow-up extended the same read-only Ghidra script to inspect the code
around the setter call, the adjacent function-name registry slots, and the
registered remaining-step-count method. It again verified the exact LGPE
Pikachu 1.0.2 `0/main` SHA-256
`1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8` and image
base `0x7100000000`. The run completed with exit code 0, emitted the script
`SUMMARY` marker, and reported no decompiler failures. The runner now treats a
missing summary or Ghidra script/decompiler error as failure because earlier
headless compile errors could otherwise be accompanied by a zero process exit
code. The development retry that exposed checked `CancelledException` errors
was fixed by propagating the exception from the new inspection methods; the
successful rerun is the evidence cited below.

Ghidra's raw pointer/name pairs in `.data` link these exact-build entries:

| Registry slot | Function entry | Adjacent registered name |
|---:|---:|---|
| `main+0x153b950` | `main+0x195780` | `UseEncountAuxItem_` |
| `main+0x153b960` | `main+0x1957a0` | `GetEncountAuxState_` |
| `main+0x153b970` | `main+0x195840` | `GetRemainingEncountAuxStepCount_` |

At `main+0x1957f4`, the code loads the integer at `[x20+8]`; `main+0x1957f8`
passes `x21` as the first argument and `main+0x1957fc` calls
`FUN_71001c47d0`. The latter accepts only 76, 77, 79, 900, 901, or 902,
stores the accepted value at `+0x11f8`, writes the associated value below at
`+0x11fa`, and returns success. The nearby `GetRemainingEncountAuxStepCount_`
entry at `main+0x195840` is present in the same registry and its disassembly
calls the encounter-state classifier. Ghidra still does not assign functions
to the `main+0x1957a0`/`main+0x195840` regions, and the setter callsite has no
direct incoming references of its own.

The actual English message and item files provide an independent value
cross-check. `itemname.dat` and `itemname.tbl` are 33,196 and 24,427 bytes,
with SHA-256 `9df661cc9c203e42a24f03d61d34067278fa23f4c7f2a9a2435cb05d57326f01`
and `a1d590c0b6a04d881d0265a229857b830e8531e3a6637460518da5e36cc79250`.
Their decoded, path-mirrored output
`decoded/1.0.2/romfs/bin/message/English/common/itemname.json` has 1,058
lines, one unpaired label, and SHA-256
`c0491b5a9cfb2b0676bb2b697bfeb65e72f4891e07ad40fa9b00d6dc7ab04376`. Its
indices line up as follows:

| Raw setter value / item file | English decoded item name | Paired short written at `+0x11fa` |
|---:|---|---:|
| 76 / `item076.dat` | Super Repel | 200 |
| 77 / `item077.dat` | Max Repel | 200 |
| 79 / `item079.dat` | Repel | 100 |
| 900 / `item900.dat` | Lure | 100 |
| 901 / `item901.dat` | Super Lure | 200 |
| 902 / `item902.dat` | Max Lure | 250 |

All six source `.dat` files exist locally and each has a corresponding
`decoded/1.0.2/romfs/bin/pokelib/item/itemNNN.json` with `record_size: 36`,
`format: LGPE Item`, and retained `raw_hex`. Their per-file source/output
SHA-256 values and `DECODED` status are recorded in `manifests/gamedata.jsonl`
and `manifests/outputs.jsonl`; the recorded decoder is
`lgpe_research.gamedata_decode/items` using pkNX commit
`d191cd0e5c05f2af81d9a41c1f1d82e6621b351a`. The English message receipt records
the corresponding DAT/TBL hashes, output hash, decoder, and 1,058-line count.
`python3 scripts/research/check_aux_item_crosswalk.py` rehashed the six source
and JSON files, compared each 36-byte JSON `raw_hex` value with the exact source
bytes, and checked all six English labels and manifest receipts; all checks
passed. The script also passed `python3 -m py_compile`.

Taken together, the adjacent registry names and matching item-name indices
strongly associate the six accepted integers with encounter auxiliary items
(the three Repels and three Lures). The name `GetRemainingEncountAuxStepCount_`
and the positive check on the paired short suggest that `+0x11fa` tracks
remaining steps, but this is still an interpretation, not a recovered field
declaration: the decrement/write lifecycle and virtual-call targets are not
fully traced. Neither this static association nor the item-name match proves
that the unassigned code executes in gameplay. No source or decoded files were
modified by this analysis.

Reproduce the Ghidra pass with
`powershell.exe -ExecutionPolicy Bypass -File scripts/ghidra/Run-InspectEncounterModeHelper.ps1`.
Reproduce the local source/decoder cross-check with
`python3 scripts/research/check_aux_item_crosswalk.py`.
The script log is `logs/ghidra-encounter-mode-helper-v1-script.log`; it
contains the exact-hash guard, writer decompilation, instruction window,
registry pointers/names, and helper references. Refreshed coverage reported
**SCANNED 27,824; DECODED 21,076; FAILED 0; UNKNOWN 6,748; PENDING 0;
UNSUPPORTED 0; 77,697 registered outputs**. The WSL test suite passed
**105/105**. T10 remains `IN_PROGRESS`.

### T10 encounter auxiliary countdown and expiry trace — 2026-10-29

The next read-only, exact-hash Ghidra pass expanded the same script to the
field accessors, countdown helper, expiry clear, and direct caller. It verified
`main` SHA-256
`1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8`, emitted
the expected summary marker, and had zero script/decompiler errors. All
addresses below refer only to this Let's Go Pikachu 1.0.2 image at base
`0x7100000000`.

The field lifecycle is now visible in the local decompilation:

| Exact-build function | Directly observed behavior |
|---|---|
| `FUN_71001c4890` (`main+0x1c4890`) | Returns the signed short at `param_1+0x11f8`. |
| `FUN_71001c48a0` (`main+0x1c48a0`) | Returns the signed short at `param_1+0x11fa`. |
| `FUN_71001c48b0` (`main+0x1c48b0`) | Reads the signed short at `+0x11fa`; when it is positive, writes the value minus one back and returns the new value. |
| `FUN_71001c48d0` (`main+0x1c48d0`) | Clears the 32-bit word at `+0x11f8`, clearing both adjacent shorts. |

`FUN_71003066d0` (`main+0x3066d0`) is the only direct caller of the decrement
helper at `main+0x30672c`, and the only direct caller of the clear helper at
`main+0x3067b0`. It first classifies the state with `FUN_71001c4840`; a zero
classification skips the decrement, and a nonzero decrement result also
returns through the non-expiry branch. When the decrement reaches zero, it
reads the stored item ID with `FUN_71001c4890`, calls `FUN_71001c95f0` with that
ID and another object, clears the 32-bit state word with `FUN_71001c48d0`, then
passes the ID and another result to `FUN_710017abb0` with constant
`0x7664902f29cfbdeb`. The meanings of those downstream helper calls and the
constant are not recovered here.

The callsite chain found in this pass is:

```text
main+0x2fae4c -> FUN_7100303580 (main+0x303580)
main+0x30387c -> FUN_71003066d0 (main+0x3066d0)
main+0x30672c -> FUN_71001c48b0 (main+0x1c48b0)
```

`FUN_7100303580` has one direct incoming call reference in the saved Ghidra
analysis, from `FUN_71002fab90` at `main+0x2fae4c`; the caller's higher-level
purpose and runtime cadence are still unidentified. Separately, the exact
registry entry `GetRemainingEncountAuxStepCount_` at `main+0x195840` and the
six item-name/source cross-check support interpreting `+0x11fa` as a remaining
encounter auxiliary step counter and `+0x11f8` as the associated item ID.
This now has direct static decrement/expiry evidence, beyond the earlier
positive-value inference. It still does not establish how often the call runs
in gameplay, whether the named entry dispatches to this state object, or that
any of these functions was reached at runtime.

The full decompilation and callsite windows are in the ignored
`logs/ghidra-encounter-mode-helper-v1-script.log`; rerun with
`powershell.exe -ExecutionPolicy Bypass -File scripts/ghidra/Run-InspectEncounterModeHelper.ps1`.
The source resources, decoded outputs, and manifests were unchanged. Current
coverage remains **SCANNED 27,824; DECODED 21,076; FAILED 0; UNKNOWN 6,748;
PENDING 0; UNSUPPORTED 0; 77,697 registered outputs**. The latest full WSL
suite result is **105/105 passed**. T10 remains `IN_PROGRESS`.

### T10 countdown callsite control-flow boundary — 2026-10-29

A further SHA-guarded Ghidra run followed incoming references one level above
the countdown caller. It again verified the same `main` hash, emitted
`SUMMARY`, and had zero script/decompiler failures. The exact instructions at
`main+0x2fae4c` show `FUN_71002fab90` calling `FUN_7100303580` only on a local
flag-controlled path: it loads a byte from `[x24+0x18]`, tests bit 3 at
`main+0x2fae3c`, and branches over the call when that bit is zero. The meaning
of that byte and flag is unknown.

The only direct reference to `FUN_71002fab90` is the call at
`main+0x2f8c14` from `FUN_71002f8a50` (`main+0x2f8a50`). Its surrounding
instructions show that the call follows `FUN_71002fa700(x20, x19)` and is
skipped when that previous call returns nonzero. Ghidra finds **zero direct
incoming references** to `FUN_71002f8a50`. Earlier exact-build tracing found
that same function directly calls the encounter parser candidate
`FUN_71002fdf90` at `main+0x2f8e2c`; thus the static call graph places the
auxiliary counter update and that parser candidate in one function, but does
not establish that the function itself is reached at runtime.

Ghidra's decompilation of the 1,314-line `FUN_71002fab90` body reported
`Type propagation algorithm not settling`. I did not use its inferred locals
or field names. The observations above come from direct reference records and
the raw AArch64 instruction windows at `main+0x2fae4c` and `main+0x2f8c14`.
The pass does not establish what the flag represents, whether the branch is a
player-step event, or how often the counter is decremented.

Reproduce with
`powershell.exe -ExecutionPolicy Bypass -File scripts/ghidra/Run-InspectEncounterModeHelper.ps1`;
the latest run returned 0, emitted `SUMMARY`, had no script/decompiler errors,
and is in `logs/ghidra-encounter-mode-helper-v1-script.log`. No source bytes,
decoded outputs, or manifests changed. Coverage remains
**SCANNED 27,824; DECODED 21,076; FAILED 0; UNKNOWN 6,748; PENDING 0;
UNSUPPORTED 0; 77,697 registered outputs**. The WSL suite passed **105/105**.
T10 remains `IN_PROGRESS`.

### T10 encounter-aux expiry lookup boundary — 2026-10-29

The same read-only Ghidra script then inspected the expiry branch's two
downstream helpers on the exact-hash 1.0.2 `main`. It emitted `SUMMARY`, had
no script/decompiler failures, and retained the verified main SHA-256
`1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8`.

`FUN_71001c95f0` at `main+0x1c95f0` has 31 direct call references in this
image, including the encounter parser candidate at `main+0x2fe270` and the
auxiliary expiry handler at `main+0x3067a4`. Its decompilation calls
`FUN_710071d1b0(item_id & 0xffff, 0xb)`. That helper returns zero unless the
item ID is below `0x422` and the second argument is `0xb`; otherwise it reads
one byte from a global item-indexed table and masks it to three bits. The
result selects one of seven pointer/length pairs in the first argument
(lengths 60, 108, 200, 150, 50, 150, 150; offsets `+0xde8` through `+0xe18`).
The lookup scans 32-bit entries, compares the low 15 bits to the item ID, and
returns the matching entry's high 15 bits. The data's field meaning remains
unknown; these are direct code/data-flow observations, not decoded item
semantics.

On expiry, `FUN_71003066d0` passes the saved item ID to this lookup, then
passes the ID and returned value to `FUN_710017abb0` with opaque key
`0x7664902f29cfbdeb`. `FUN_710017abb0` forwards through
`FUN_710017a750` with constant `0xcbf29ce484222645`; the latter selects an
opaque record through `FUN_710017b940` and writes the supplied values into
that record. These helpers have 3 and 14 direct references respectively, so
the route is shared. I searched the decoded message JSON tree for the exact
`7664902f29cfbdeb` value and found no match; its role as a localized-message
ID or textual hash is therefore unverified. I have not assigned meanings to
the returned packed value, the key, or the output record fields.

This extends the static expiry path through a generic item-index lookup and a
shared keyed-record builder, but does not identify the gameplay effect or
prove runtime execution. Reproduce the inspection with
`powershell.exe -ExecutionPolicy Bypass -File scripts/ghidra/Run-InspectEncounterModeHelper.ps1`.
Latest output is in `logs/ghidra-encounter-mode-helper-v1-script.log`. No
source resources, decoded files, or manifests changed. Coverage remains
**SCANNED 27,824; DECODED 21,076; FAILED 0; UNKNOWN 6,748; PENDING 0;
UNSUPPORTED 0; 77,697 registered outputs**. T10 remains `IN_PROGRESS`.

### T10 expiry record-accessor follow-up — 2026-10-29

A further read-only run extended this exact-hash main trace through
`FUN_710017b940`, the callee used by the shared builder. The run completed at
2026-10-29 14:23:36, emitted `SUMMARY`, and reported no `DECOMPILE_FAILED`
entries. The image base and main SHA-256 remained `0x7100000000` and
`1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8`.

`FUN_710017b940` has four direct references in this image; one is the call
from `FUN_710017a750` at `main+0x17a87c`. The call passes a pointer to the
result location, an object/context pointer, and the caller's second parameter.
The helper passes its third parameter into `FUN_7100194890`, then supplies the
returned four-word tuple to `FUN_710017cb50`. If the local result is null, it
allocates `0x480` bytes with `0x10` alignment, calls an initializer, and then
`FUN_710019b220`; otherwise it calls `FUN_710019b3c0`. Both branch helpers
have one direct caller here. The decompiler shows pointer/refcount handling
and opaque fixed-offset writes, but no type names or field semantics. The
`FUN_710019b3c0` decompile also warns that it could not recover an indirect
jump table. This supports describing the path as a shared keyed-record
accessor/builder candidate only; it does not identify a message, notification,
or gameplay effect.

Re-run with
`powershell.exe -ExecutionPolicy Bypass -File scripts/ghidra/Run-InspectEncounterModeHelper.ps1`;
the added targets are in `scripts/ghidra/InspectEncounterModeHelper.java` and
the output is in `logs/ghidra-encounter-mode-helper-v1-script.log`. No source
data, decoded resources, or manifests changed. Coverage remains **SCANNED
27,824; DECODED 21,076; FAILED 0; UNKNOWN 6,748; PENDING 0; UNSUPPORTED 0;
77,697 registered outputs**. Full WSL tests remain **105/105**. T10 remains
`IN_PROGRESS`.

### T10 encounter-parser lookup callsite — 2026-10-29

The read-only headless Ghidra run completed at 2026-10-29 14:27:50 with exit
code 0 and summary. It verified the exact 1.0.2 `main` SHA-256
`1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8` at base
`0x7100000000`.

At `main+0x2fe270` inside `FUN_71002fdf90`, the preceding instructions
assemble and compare `x8` to `0x97deb1f2d0a83282`. On equality, the code loads
`w1 = 0x36a`, moves `x25` to `x0`, and calls `FUN_71001c95f0`; the following
`cbz w0` branches away when the helper returns zero. This is a concrete
callsite and argument observation. The integer `0x36a` and compared constant
remain semantically unidentified; no species, item, weight, or field label is
assigned.

The direct caller of this parser candidate is `FUN_71002f8a50`, at
`main+0x2f8e2c`; Ghidra reports zero direct references to `FUN_71002f8a50` in
this image. Its stable decompilation shows the parser call only after an
earlier helper returns zero, then calls `FUN_7100300e40`. The candidate parser
decompilation is 2,192 lines and emits `Type propagation algorithm not
settling`, so conclusions here use the raw callsite instructions and the
separately decompiled 166-line parent only. Static references do not prove
runtime reachability.

Reproduce with
`powershell.exe -ExecutionPolicy Bypass -File scripts/ghidra/Run-InspectEncounterModeHelper.ps1`;
the script now prints instruction context at `main+0x2fe270` and
`main+0x2f8e2c`. Latest output is in
`logs/ghidra-encounter-mode-helper-v1-script.log`. No game files, decoded
outputs, or manifests changed. Coverage remains **SCANNED 27,824; DECODED
21,076; FAILED 0; UNKNOWN 6,748; PENDING 0; UNSUPPORTED 0; 77,697 outputs**.
The full WSL suite last passed **105/105**. T10 remains `IN_PROGRESS`.

The literal lookup argument has a verified text cross-reference: decimal 874
(`0x36a`) is row `ITEMNAME_874`, rendered as “Silph Scope” by the LGPE 1.0.2
English `itemname.dat/.tbl` pair. I reran the repository's message decoder on
the original pair and compared the full result with the existing JSON; they are
identical. The source DAT SHA-256 is
`9df661cc9c203e42a24f03d61d34067278fa23f4c7f2a9a2435cb05d57326f01`, the TBL
SHA-256 is `a1d590c0b6a04d881d0265a229857b830e8531e3a6637460518da5e36cc79250`,
and the output JSON SHA-256 is
`c0491b5a9cfb2b0676bb2b697bfeb65e72f4891e07ad40fa9b00d6dc7ab04376`. The
existing `manifests/outputs.jsonl` receipt records these source/output hashes
and LGPE 1.0.2. This cross-reference identifies the localized label at that
index only; it does not establish why the parser queries it or the gameplay
meaning of the branch.

The label-only cross-reference now has a repeatable verifier:
`python3 scripts/research/check_encounter_parser_label.py`. It re-decodes the
actual English DAT/TBL pair, requires byte-identical JSON, checks all three
SHA-256 values and the `outputs.jsonl` 1.0.2 receipt, and asserts only the
`ITEMNAME_874` / “Silph Scope” label. The local run passed. This validator does
not claim or test gameplay semantics.


### T10 exact-build ZoneNameHashTable cross-reference — 2026-10-29

A follow-up inspected the already-decoded exact-build callsite against the actual 1.0.2 `ZoneNameHashTable.tbl`. The local ExeFS `main` hash remains `1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8` at Ghidra base `0x7100000000`. In `FUN_71002fdf90`, `main+0x2fe250..0x2fe260` assembles and compares `x8` with `0x97deb1f2d0a83282`; `main+0x2fe268..0x2fe270` passes `0x36a` to `FUN_71001c95f0`. In the parent candidate `FUN_71002f8a50`, decompiled comparisons also contain `0x194d955fbf0a7685` and `0xd8652ab502b422c7`. The reproducible Ghidra command is `powershell.exe -ExecutionPolicy Bypass -File scripts/ghidra/Run-InspectEncounterModeHelper.ps1`; the 2026-10-29 local app log records those instruction contexts and parent code at `logs/ghidra-encounter-mode-helper-v1-app.log`.

The table source is 5,131 bytes with SHA-256 `2c314dec7348010523a6f695319d83a136b4f4b7c058666bf3f09c91a82912fe`. All 257 rows were parsed, and all 257 original label byte strings reproduce their stored hashes under 64-bit FNV-1a (offset basis `0xcbf29ce484222645`, prime `0x100000001b3`, trailing NUL padding excluded). The three Ghidra constants map to labels/indexes as follows:

| Ghidra qword | ZoneNameHashTable index | Label bytes / display |
|---|---:|---|
| `0x97deb1f2d0a83282` | 134 | `t005r0305` |
| `0x194d955fbf0a7685` | 255 | `gogo_park01` |
| `0xd8652ab502b422c7` | 256 | `gogo_play01` |

`python3 scripts/research/check_ahtb_zone_crossrefs.py` re-decodes all 15 unpaired AHTB sources and validates the exact main/table hashes, path-mirrored outputs, manifests, receipts, all 257 FNV results, and these three hash/label pairs. The `main+0x2fe270` call remains inside a parser candidate whose parent has zero direct incoming references in Ghidra's saved database. The constants now have verified table-label cross-references, but no runtime reachability, parser purpose, or gameplay interpretation is established. Current coverage is **SCANNED 27,824; DECODED 21,091; FAILED 0; UNKNOWN 6,733; PENDING 0; UNSUPPORTED 0; 77,712 outputs**. Full WSL tests pass **107/107**; T10 remains `IN_PROGRESS`.


### T10 `field_pocket.dat` loader and item-byte accessors — 2026-10-29

A new SHA-guarded Ghidra pass, `scripts/ghidra/InspectItemSelectorTable.java`,
reopened the saved read-only program for the exact local Let's Go Pikachu 1.0.2
`0/main`. It revalidated base `0x7100000000` and `main` SHA-256
`1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8`.

`FUN_710071d1b0` (`main+0x71d1b0`) returns zero for item indices `>= 0x422`;
for an in-range index and its second argument equal to `0xb`, it returns the
indexed byte masked with `7`. `FUN_710071d210` applies the same index bound and
tests the signed byte at that index. `FUN_71001c95f0` consumes the selector
result to select one of seven pointer/list pairs at first-argument offsets
`+0xde8` through `+0xe18`, with observed scan bounds 60, 108, 200, 150, 50,
150, and 150. Entry words are matched by low 15 bits and the helper returns
the high 15 bits. A follow-up exact-source comparison against pinned pkNX
commit `d191cd0e5c05f2af81d9a41c1f1d82e6621b351a` confirmed the accessor's
low-three-bit value matches GameManagerGG `Item.PocketField` in all 1,058 item
records; the JSON export now calls this numeric value `pocket_field`.
Human-readable category names, packed-word meanings, list contents, and bit 7
remain unresolved. These are observed access operations, not proof of runtime
execution.

The global byte-map slot `0x710163ea48` lies in Ghidra's uninitialized `.bss`
range (`0x710160d000`–`0x7101ee06f7`), so its runtime bytes are absent from the
static `main` image. Its unique observed writer is `FUN_710071cec0` at
`main+0x71cec0`, directly called from `FUN_71001d3730` at `main+0x1d43a8`.
The callsite loads `x0` from `[x19+0x98]`. In the initializer, the resource
request goes through `FUN_71000adc70`; the returned object's byte count is read
at `+0x160`, the data pointer at `+0x170`, and that range is copied into the
`.bss` buffer. The only direct caller of `FUN_710073b950` (`main+0x73b950`)
is this initializer. The helper constructs a name with the literal suffix
`field_pocket.dat` and passes it to `FUN_71001d88b0`. The caller's decompiled
setup also contains `bin/pokelib/item` path strings. The matching local
RomFS file is `1/bin/pokelib/item/field_pocket.dat`, exactly `0x422` bytes;
the batch decode and byte/hash checks are documented in `T07-notes.md`.

Reproduce the static pass with
`powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/ghidra/Run-InspectItemSelectorTable.ps1`.
The successful run's ignored app log is
`logs/ghidra-item-selector-map-v4-app.log`; it emitted the program hash,
uninitialized BSS range, all slot references, the resource-name builder,
initializer caller instructions, and decompilation for both byte accessors.
This establishes a statically observed resource/access chain, not runtime
execution or gameplay semantics. T10 remains `IN_PROGRESS`.

The separate `battle_pocket.dat` bytes match pinned pkNX
`Item.PocketBattle` for all 1,058 item records (0 mismatches), and its numeric
byte map is exported in `T07-notes.md`. This is a full data-value comparison;
the exact 1.0.2 `main` loader/accessor for `battle_pocket.dat` remains
unidentified. The negative full-filename string search does not exclude a
dynamically assembled path or generic loader.

### T10 exact 1.0.2 `item_hash_to_index.dat` load/parse chain — 2026-10-29

This follow-up corrects the earlier negative raw-string result: ExeFS `main`
is a packed NSO (`NSO0`), so raw `strings` scans the compressed file bytes.
Ghidra 12.2's Switch loader mapped the exact source NSO and exposed the
decompressed string/code at image base `0x7100000000`. The guarded `main`
SHA-256 is `1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8`.

`main+0xf02a31` contains the path
`bin/pokelib/item/item_hash_to_index.dat`; its data xref at `main+0x1d4538`
lands in `FUN_71001d4510`. The function builds a path object with
`FUN_71001d4ff0`, requests the resource through `FUN_71000adc70`, obtains the
buffer pointer from request object `+0x170`, reads a u32 count from file
offset 0, then walks 0x10-byte rows. It uses the qword at row `+0` as a
hash-map key and stores the low 16 bits of the qword at `+8` after casting it
to `short`. This is exact-build static load/parse evidence; it does not
establish the key hash algorithm, map consumer semantics, or execution.

The reader's only direct code caller is `FUN_71001d35e0` from
`main+0x1d364c`; that function calls the sibling item-resource loaders and has
direct callers at `main+0x5c88` (`FUN_7100005bd0`) and `main+0x1d638c`
(`FUN_71001d62b0`). Ghidra reports one data reference to `FUN_7100005bd0`
from `main+0x1527458`, but that alone does not prove runtime execution. The
research decoder now preserves the source bytes and every 16-byte row; its
real output and verification are recorded in `T07-notes.md`.

Reproduce with
`pwsh.exe -NoProfile -File scripts/ghidra/Run-InspectItemHashReferences.ps1`.
The script guards the exact NCA path, `main` hash, source table hash/size, and
image base, and uses the local read-only Ghidra project. The earlier packed
NSO scan should not be treated as evidence that the path string is absent.

No encounter/catch/RNG behavior is assigned to this loader. T10 remains
`IN_PROGRESS`; overall source-wide coverage after the associated T07 batch is
**SCANNED 27,824; DECODED 21,094; FAILED 0; UNKNOWN 6,730; PENDING 0;
UNSUPPORTED 0; 77,715 registered outputs**.

### T10 exact-build xoroshiro recurrence follow-up — 2026-10-30

The public [LGPE spawn-mechanics gist](https://gist.github.com/Lusamine/c9c6be1287daa3aff2c5010a01d662f7)
was used only as a candidate lead. I checked it against the local Pikachu
1.0.2 ExeFS `main`, not an address map copied from another build. The
SHA-guarded input is
`1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8` at
Ghidra image base `0x7100000000`. The inspection uses Ghidra 12.2 with
`-noanalysis -readOnly`; its tracked runner is
`scripts/ghidra/Run-InspectSpawnRngContext.ps1` and its script is
`scripts/ghidra/InspectSpawnRngContext.java`.

The lead's `main+0x2fdfc0` is not a function entry in the saved exact-build
Ghidra program. It is the `mov x19,x0` instruction inside
`FUN_71002fdf90` (entry `main+0x2fdf90`). The function has one direct incoming
call, from `FUN_71002f8a50` at `main+0x2f8e2c`; the caller has zero direct
incoming references in the saved database. This is an exact static call edge,
not proof the caller is reached at runtime.

The decompilation shows two separate pairs of 64-bit words in the first
argument object, at byte offsets `+0x80/+0x88` and `+0x90/+0x98`. Both follow
the same recurrence: output `s0+s1`, set `t=s0 XOR s1`, then update
`s0=rotl(s0,24) XOR t XOR (t<<16)` and `s1=rotl(t,37)`. This exactly matches
the xoroshiro128+ recurrence with `(24,16,37)` parameters described by
[Blackman and Vigna's xoroshiro128+ 1.0 reference implementation](https://prng.di.unimi.it/xoroshiro128plus.c).
That identifies the local recurrence; it does not establish where either
state is initialized, its seed source, or whether the orphaned call path runs.

In the same function, one state pair supplies a bounded draw: the low seven
bits are retried while greater than 100, then compared against the result of
`FUN_71003154a0`. Earlier exact-build cross-references establish that helper
as a lookup of the encounter table's ground/water/sky encounter-rate field.
This ties the RNG recurrence to a static encounter-rate selection path.

The second pair is read only after a boolean condition and the opaque
`plVar61[0x7a] == 3` gate. Its output is reduced modulo 10,000 and accepted
when the remainder is at most 4; a second output is reduced modulo 3 and maps
to numeric values `0x90`, `0x91`, or `0x92`. Those values are then compared
with the low 16 bits returned by `FUN_7100218470` for candidate objects. A
follow-up below shows that this wrapper copies four qwords from object offsets
`+0x3e8`, `+0x3f0`, `+0x3f8`, and `+0x400` (32 bytes total) into a local
descriptor before calling a table-driven metadata helper. The descriptor and
returned payload remain semantically opaque; this does not assign the numeric
values a species or gameplay label.

No seed initialization, time/cryptographic randomness, capture formula,
Pokémon PID/EC or shiny generation, or runtime edge into this path was
recovered. The later branch is recorded as exact code behavior only; the
external gist's names and wider mechanics remain unverified for this build.
Reproduce with:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/ghidra/Run-InspectSpawnRngContext.ps1
```

The successful Ghidra 12.2 headless run reported the expected main SHA,
`target_exact_start=false`, one incoming call to the candidate, zero incoming
references to its caller, two incoming references to the encounter-rate
helper, and successful decompilation of the candidate and numeric-value
helper. Logs are `logs/ghidra-spawn-rng-context-v1-script.log` and
`logs/ghidra-spawn-rng-context-v1-app.log` (ignored generated evidence). No
ROM or decoded source was modified. Global coverage remains **SCANNED 27,824;
DECODED 21,456; FAILED 0; UNKNOWN 6,340; PENDING 0; UNSUPPORTED 28; 78,104
outputs**. T10 remains `IN_PROGRESS`.

### T10 exact-build candidate accessor follow-up — 2026-10-30

I extended the SHA-guarded Ghidra 12.2 `-noanalysis -readOnly` pass on the
same local Pikachu 1.0.2 `0/main` (SHA-256
`1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8`, image
base `0x7100000000`). `FUN_7100218470` has 51 direct code references in the
saved database, including four calls from `FUN_71002fdf90`; the low-16-bit
comparisons against `0x90..0x92` are in that exact-build function.

The decompilation narrows the data flow: `FUN_7100218470` copies qwords at
object offsets `+0x3e8`, `+0x3f0`, `+0x3f8`, and `+0x400` into a 32-byte local
descriptor, then calls `FUN_71000d4af0`. That helper starts with output value
`0x69`, looks up metadata rows using selector indexes `0x0f` and `0x17..0x1c`
through `FUN_71000b84d0` / `FUN_71000d22b0`, and on a match writes a 32-bit
payload plus small side fields. The labels for the descriptor, metadata rows,
and payload are not recovered, so calling this a Species accessor would still
be an unsupported semantic assignment. As a data-side check, a recursive
search of the actual decoded `encount_data_p.json` (70 rows and all nested
slot vectors) found zero `Species` values `0x90`, `0x91`, or `0x92`; the
encounter table therefore provides no positive cross-check for that label.

Reproduce the exact-build trace with
`pwsh.exe -NoProfile -ExecutionPolicy Bypass -File scripts/ghidra/Run-TraceSpawnEntityValue.ps1`.
The tracked script writes decompilations for the wrapper, metadata helpers,
and candidate under the ignored
`logs/ghidra-spawn-entity-value-v1-functions/` directory, and verifies the
main hash and image base before analysis. The successful run emitted the
expected hash/base summary. This narrows the opaque return path but does not
resolve the label, state initialization, or runtime reachability. No source
or decoded output changed; coverage remains **SCANNED 27,824; DECODED 21,456;
FAILED 0; UNKNOWN 6,340; PENDING 0; UNSUPPORTED 28; 78,104 outputs**. T10
remains `IN_PROGRESS`.

### T10 candidate descriptor construction trace — 2026-10-30

A literal-offset store scan of the exact SHA-guarded main examined 29,483
Ghidra functions and 2,243,719 instructions. It found 352 store instructions
across common object offsets, so hits alone were not treated as field
evidence. The useful hit, `FUN_71002175e0`, was then verified by direct xrefs
and the candidate's actual constructor call path: it reads optional fields
from its FlatBuffer table argument and writes four qwords to object offsets
`+0x3e8`, `+0x3f0`, `+0x3f8`, and `+0x400`. Its only direct call site in the
saved database is `FUN_710026f930` at `main+0x26f974`; that function is called
from `FUN_71002334d0` at `main+0x233530`.

The exact-build candidate `FUN_71002fdf90` allocates a `0x10d0`-byte object
and calls `FUN_71002334d0` at `main+0x3008a4` with a table reached through a
FlatBuffer vector. In that same candidate, four direct calls to
`FUN_7100218470` compare its result with values derived by the RNG branch.
This statically links a candidate object-construction path to the 32-byte
descriptor read by the value helper. It does not reveal the four schema field
names, identify the input FlatBuffer resource, or prove that this function
runs at runtime. The two constructor vtable groups at
`PTR_DAT_71015fe9d8` and `PTR_DAT_71015fe9e0` have null type-info pointers at
the inspected address points; this route did not yield RTTI class names.

Reproduce the focused writer scan and vtable check with
`pwsh.exe -NoProfile -ExecutionPolicy Bypass -File scripts/ghidra/Run-ScanSpawnEntityDescriptorWrites.ps1`
and
`pwsh.exe -NoProfile -ExecutionPolicy Bypass -File scripts/ghidra/Run-InspectSpawnEntityVtables.ps1`.
The full helper/constructor/candidate decompilation pass is reproduced with
`scripts/ghidra/Run-TraceSpawnEntityValue.ps1`. All passes guarded the same
local Pikachu 1.0.2 `main` hash and base and used `-noanalysis -readOnly`.
No data exports changed. The source-table check above remains zero
`Species` hits for `0x90..0x92`; the selected values and accessor payload stay
UNKNOWN. Coverage is unchanged: **SCANNED 27,824; DECODED 21,456; FAILED 0;
UNKNOWN 6,340; PENDING 0; UNSUPPORTED 28; 78,104 outputs**. T10 remains
`IN_PROGRESS`.

### T10 shared spawn-state consumer follow-up — 2026-10-30

The decompiled direct caller `FUN_71002f8a50` reaches `FUN_71002fdf90` at `main+0x2f8e2c`, then calls `FUN_7100300e40` at `main+0x2f8e38`. The latter independently reads and writes the same first 128-bit state pair at argument offsets `+0x80/+0x88`, follows the same `(24,16,37)` xoroshiro128+ recurrence, and calls the exact-build encounter-rate helper `FUN_71003154a0`. This statically shows the pair is consumed by two consecutive handlers on one direct call path. It does not prove runtime dispatch or reveal the seed source. The dispatcher itself has zero direct incoming references in the saved Ghidra database and no direct accesses to these state offsets; the two handler states' initializer remains unidentified.

The SHA-guarded trace now also decompiles the dispatcher and following handler, writing ignored outputs under `logs/ghidra-spawn-entity-value-v1-functions/`. Reproduce with `pwsh.exe -NoProfile -ExecutionPolicy Bypass -File scripts/ghidra/Run-TraceSpawnEntityValue.ps1`. Exact `main` SHA/base checks passed and `-readOnly` was used. Coverage is unchanged: **SCANNED 27,824; DECODED 21,456; FAILED 0; UNKNOWN 6,340; PENDING 0; UNSUPPORTED 28; 78,104 outputs**. T10 remains `IN_PROGRESS`.

### T10 dispatcher address-materialization scan — 2026-10-30

A focused Ghidra 12.2 code scan checked the exact local Pikachu 1.0.2 `0/main` (SHA-256 `1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8`, image base `0x7100000000`) for `ADR`/`ADRP` instructions whose rendered operands contain `2f8`, the page/address substring for dispatcher `main+0x2f8a50`. It traversed one initialized executable block: 2,839,329 instructions, including 91,789 `ADR`/`ADRP` instructions; there were zero `2f8` operand candidates. Combined with the saved database's zero direct incoming references and the earlier initialized-memory scans (which found only FDE-style range records for the matching relative-dword values), this found no static code-address materialization or constant dispatch-table edge in those tested forms. It does not rule out runtime registration, an uninitialized table, indirect computation, or an edge absent from the saved Ghidra analysis database; dispatcher reachability and RNG state initialization remain unresolved.

Reproduce with `pwsh.exe -NoProfile -ExecutionPolicy Bypass -File scripts/ghidra/Run-ScanSpawnDispatcherAddressMaterialization.ps1`. The script verifies the local NCA path, exact main SHA, and base, and runs Ghidra with `-noanalysis -readOnly`; logs are ignored under `logs/ghidra-spawn-dispatcher-materialization-v1-{script,app}.log`. No ROM or decoded outputs changed. Coverage remains **SCANNED 27,824; DECODED 21,456; FAILED 0; UNKNOWN 6,340; PENDING 0; UNSUPPORTED 28; 78,104 outputs**. T10 remains `IN_PROGRESS`.

### T10 shared-state store-offset ambiguity check — 2026-10-30

A second SHA-guarded Ghidra instruction pass scanned the same 29,483 function entries / 2,243,719 instructions for 64-bit `STR`/`STP` writes to object-relative-looking offsets `+0x80/+0x88/+0x90/+0x98`. The exact parser candidate `FUN_71002fdf90` is a positive control and writes both state pairs through one register base; however, **199 same-base writer groups** across the executable contain stores covering all four offsets. This collision rate means those offsets alone cannot identify a constructor, state initializer, or object type. No RNG seed source or state-initializing function was confirmed. The scanner now prints only the exact-build positive-control writer and an aggregate summary rather than dumping the broad candidate set. Reproduce with `pwsh.exe -NoProfile -ExecutionPolicy Bypass -File scripts/ghidra/Run-ScanSpawnRngStateStores.ps1`; it verifies the NCA path, `main` SHA/base, and uses `-noanalysis -readOnly`. The exact-build state-pair stores in `FUN_71002fdf90` include `main+0x2ffb08`/`+0x2ffd48` (`STP` to `+0x80`) and `main+0x300394`/`+0x3003d8` (`STP` to `+0x90`, covering adjacent qwords). This is instruction evidence only; no semantic field names are added. Coverage remains **SCANNED 27,824; DECODED 21,456; FAILED 0; UNKNOWN 6,340; PENDING 0; UNSUPPORTED 28; 78,104 outputs**. T10 remains `IN_PROGRESS`.

### T10 selector ordinal cross-reference — 2026-10-30

`UV_PROJECT_ENVIRONMENT=/tmp/lgpe-research-t07-venv uv run lgpe spawn-rng-crossref` writes the reproducible tracked manifest `manifests/spawn_rng-value-crossref.json`. The command hash-checks the exact 1.0.2 `main`, all four actual RomFS source files and mirrored JSON outputs, and pkNX checkout `d191cd0e5c05f2af81d9a41c1f1d82e6621b351a`. It verifies `Species.cs` (`4539de45…4f167`) and `GameFileMapping.cs` (`c439e07b…4fa5b92`) at that commit; the latter maps `bin/script_event_data/event_encount.bin` to `EncounterTableStatic`. The decoded personal table has matching index/`GoSpecies` values 144, 145, and 146, named Articuno, Zapdos, and Moltres by the pinned enum. Both ordinary encounter files have **0/1,820** matching `Species` fields. The actual 640-byte event file decodes as 10 `EncounterStatic7b` entries of 64 bytes; entries 2, 3, and 4 have `Species` 144, 145, and 146, each `Form=0` and `Level=50`.

This is a real numeric cross-reference and a lead for the RNG branch's `0x90..0x92` choices, not proof that `FUN_7100218470` returns a species ID or that `FUN_71002fdf90` selects those records. The report status remains deliberately `CORRELATED_UNASSIGNED`; accessor semantics and candidate runtime reachability remain UNKNOWN/UNVERIFIED.

A new SHA-guarded Ghidra 12.2 `-noanalysis -readOnly` trace establishes a separate static code-to-file path for `event_encount.bin` in this exact `main`. The string at `main+0xf0415a` has one direct xref at `main+0x2ba87c` into resource setup function `main+0x2ba7c0`, which calls the path builder `main+0x1d4ff0` and request helper `main+0xa63a0`. The loader has direct callsites at `main+0x289ae4`, `main+0x28e904`, and `main+0x28f3ec`. In the `main+0x28f300` state handler, readiness is checked via `main+0x2ba980`; completion calls `main+0x28f430`. The loader's completion helper `main+0x2baa10` uses the resource buffer size shifted right by six as its loop count, advances input rows by `0x40` bytes, and copies `0x59` bytes of normalized row data into an internal map. `main+0x2baba0` looks up a record in that map; its three direct call references are at `main+0x289db4` (no containing function in the saved database), `main+0x28ebe8` (owner `main+0x28eb60`), and `main+0x28f4a8` (owner `main+0x28f430`). This establishes that the exact-build static path requests this resource and contains code to split its buffer into 64-byte entries, index them, and pass a looked-up record into event handling. It does **not** connect that path to `FUN_71002fdf90`: the inspected completion handler has no direct call to the candidate, whose only direct incoming call remains `main+0x2f8e2c` from `main+0x2f8a50`; that caller still has no direct incoming refs. Indirect/runtime reachability remains unresolved.

Reproduce the data report with `uv run lgpe spawn-rng-crossref`. Reproduce the Ghidra trace with `scripts/ghidra/Run-InspectEventEncounterPathXrefs.ps1`; it checks the exact 1.0.2 `main` SHA and opens the saved database read-only. The first default WSL uv invocation attempted to recreate the project `.venv` and failed because the mapped drive does not permit symlinks; set `UV_PROJECT_ENVIRONMENT=/tmp/lgpe-research-t07-venv` for WSL. No game source or decoded data was modified. The latest WSL2 regression run passes **146/146 in 9.680s**; `git diff --check` is clean. Coverage remains **SCANNED 27,824; DECODED 21,456; FAILED 0; UNKNOWN 6,340; PENDING 0; UNSUPPORTED 28; 78,104 outputs**. T10 remains `IN_PROGRESS`.

### T10 event handler row cross-reference — 2026-10-30

The expanded `spawn-rng-crossref` report (schema v3) joins the exact-build handler's normalized row checks against the actual `event_encount.bin` bytes. All addresses below are from local Let's Go Pikachu 1.0.2 `0/main`, SHA-256 `1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8`, image base `0x7100000000`. In `FUN_71002baa10` (`main+0x2baa10`), each `0x40`-byte source row contributes the little-endian `u16` at source offset `0x08` as a zero-extended `u32` at normalized offset `0x08`; source bytes `0x0a` and `0x0b` become normalized bytes `0x0c` and `0x0d`. `FUN_710028f430` (`main+0x28f430`) obtains a row through `FUN_71002baba0` and tests normalized `Species == 0x85 && Form == 1`, or `Species == 0x19 && Form == 8`.

Those pairs match local source rows 1 and 0 respectively: `Eevee`/Form 1/Level 5 and `Pikachu`/Form 8/Level 5, using enum names from pinned pkNX commit `d191cd0e5c05f2af81d9a41c1f1d82e6621b351a`. Source SHA-256 is `2bbe6321c8c25dd75ed5d11db81fa4077bd513081c0c77d72b6574874ff5e814`; the mirrored JSON SHA-256 is `2f4c59c422f832cf74d3c13d1ee50c50dc3a07a5eec397209970d646e5e2d4eb`. A fresh pinned-pkNX C# export plus Python comparison validated all 10 records and 39 properties per record with zero mismatches. The report checks source row bytes against each mirrored JSON `raw_hex` before evaluating the conditions.

The same handler conditionally changes the normalized `Gender` byte. `FUN_71001ca030` (`main+0x1ca030`) returns the byte at opaque object offset `+0x111`; at call sites `main+0x28f4fc` and `main+0x28f508`, `FUN_710028f430` writes `1` to normalized offset `+0x14` when the first read is `0`, or writes `2` when the first read is nonzero and the second read is `1`. The builder copies source byte `+0x0d` to normalized `+0x14`; pinned `EncounterStatic7b.cs` masks source `+0x0d` to two bits for `Gender`, while pinned `FixedGender.cs` defines `1=Male` and `2=Female`. Both matching event rows start with `Gender=Random`. The C# source hashes are `7d6606801788be39d28890e751126f42aade289963f684ae7f27085b3d331a91` (`EncounterStatic7b.cs`) and `b981dab73e8148c50cde48e3218c25414f8d9178ba996e5290ef255ae5733ac6` (`FixedGender.cs`), both at the pinned commit above. This statically maps the code's byte writes to the pkNX Gender encodings; the opaque `+0x111` input's meaning, runtime execution, and actual gameplay outcome remain unknown.

This field-to-row match does not connect the event handler or event-table loader to RNG candidate `FUN_71002fdf90`; that candidate remains `CORRELATED_UNASSIGNED` with runtime reachability unverified. Reproduce the independent source decode with `dotnet run --project scripts/gamedata-crosscheck/crosscheck.csproj -c Release`, then compare pinned pkNX records with `UV_PROJECT_ENVIRONMENT=/tmp/lgpe-research-t07-venv uv run python scripts/gamedata-crosscheck/verify_pknx_encounters.py`. Reproduce the report and checks with `UV_PROJECT_ENVIRONMENT=/tmp/lgpe-research-t07-venv uv run lgpe spawn-rng-crossref`, `UV_PROJECT_ENVIRONMENT=/tmp/lgpe-research-t07-venv uv run python -m unittest discover -s tests -p 'test_spawn_rng_crossref.py' -v`, and the SHA-guarded Ghidra wrapper `scripts/ghidra/Run-InspectEventEncounterPathXrefs.ps1` (the latest run uses `v2` log names). The full WSL suite passes **146/146 in 7.696s**, including the four focused cross-reference tests. Coverage remains **SCANNED 27,824; DECODED 21,456; FAILED 0; UNKNOWN 6,340; PENDING 0; UNSUPPORTED 28; 78,104 outputs**.


### T10 opaque event-byte setter cross-reference — 2026-10-30

The schema-v4 `spawn-rng-crossref` report adds a hash-pinned trace of the event handler's opaque byte accessors. All addresses below refer only to the local Let's Go Pikachu 1.0.2 `0/main`, SHA-256 `1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8`, base `0x7100000000`. Ghidra 12.2 was run with `-noanalysis -readOnly`. `FUN_71001ca030` at `main+0x1ca030` reads byte `param+0x111`; setter `FUN_71001ca020` at `main+0x1ca020` writes `param_2` to that byte.

The setter's direct call reference is `main+0xf058` from `FUN_710000e420` (`main+0xe420`). The instruction context is `mov w1,#0x1; mov x0,x20; bl main+0x1ca020`, so the statically verified second argument at this call is constant 1. A decompiled switch case (`0xb`) in that same function instead presents `((int)uVar2 + (int)uVar1 & 1U) != 0` as the setter argument. The function also has a Ghidra type-propagation warning. The decompiled expression and instruction context conflict; this report records the conflict as `UNRESOLVED` and does not claim an RNG value reaches the setter.

The event handler and setter caller have superficially similar nested pointer access shapes, but their roots differ (a global pointer in the event handler versus `param_2` in the setter caller). Static evidence does not establish that the `+0x111` getter reads the same object instance that this setter writes. Opaque input semantics, runtime dispatch, event gender behavior, and any relationship to the separate spawn RNG candidate remain unknown. The report's overall status stays `CORRELATED_UNASSIGNED`.

Reproduce the report with `UV_PROJECT_ENVIRONMENT=/tmp/lgpe-research-t07-venv uv run lgpe spawn-rng-crossref`. Run the guarded trace with `scripts/ghidra/Run-InspectEventEncounterPathXrefs.ps1`; it verifies the exact `main` hash and opens the saved project read-only. The trace source SHA-256 is `cdbbf2193b0785b1e2f9b9589e628f8a430ddd9089cbf1cb651730fb4ae4042a`, and wrapper SHA-256 is `b9dc68e0208cdede2c803fb5896f1463e475cdaac3aa7029db40049c184f0b92`. The latest logs are ignored at `logs/ghidra-event-encounter-path-xrefs-v3-{script,app}.log`. Focused tests pass **4/4** and the full WSL2 suite passes **146/146 in 9.179s**. Coverage remains **SCANNED 27,824; DECODED 21,456; FAILED 0; UNKNOWN 6,340; PENDING 0; UNSUPPORTED 28; 78,104 outputs**; T10 remains `IN_PROGRESS`.


### T10 setter-caller data-reference inspection — 2026-10-30

A follow-up SHA-guarded Ghidra 12.2 `-noanalysis -readOnly` pass inspected the only incoming reference to `FUN_710000e420` reported in the saved database. It is a DATA reference from `main+0x15278b8`, not a call instruction. Ghidra reports that cell as `undefined *` in writable, non-executable `.data`, with stored value `main+0xe420`. Its 64-byte observed neighborhood at `main+0x1527898` consists of qwords `0x7100002a90`, `0x7100011160`, `0x710000e2c0`, `0x710000e2d0`, `0x710000e420`, `0x7100010e60`, `0xffffffffffffffff`, and zero. Ghidra found zero direct references to the specific data cell in the saved database. The neighboring values and placement suggest a pointer collection, but its table type, consumers, runtime read, and dispatch role are not identified; the entry does not establish runtime reachability or object identity.

The trace script now emits the exact data cell type/value, memory block permissions, 64-byte raw window, and inbound/outbound references. Reproduce with `scripts/ghidra/Run-InspectEventEncounterPathXrefs.ps1`; the ignored logs use `logs/ghidra-event-encounter-path-xrefs-v6-{script,app}.log`. Both the program path/hash and base remain pinned to the local 1.0.2 main. The `spawn-rng-crossref` report is now schema v5 and retains `CORRELATED_UNASSIGNED`; it records this data pointer as an observation and explicitly leaves runtime dispatch unverified. The regenerated report passes the full WSL2 suite **146/146 in 9.198s**. Coverage remains **SCANNED 27,824; DECODED 21,456; FAILED 0; UNKNOWN 6,340; PENDING 0; UNSUPPORTED 28; 78,104 outputs**; T10 remains `IN_PROGRESS`.


### T10 setter-caller data page-reference boundary — 2026-10-30

The Ghidra v8 pass adds a bounded query for references to the 4 KiB page base containing `main+0x15278b8`. It reports **375** references to page base `main+0x1527000`: **178 DATA** and **197 PARAM** reference types, across **82 unique owner labels** (including references with no containing function). Sample source addresses are `main+0xc9ba0c`, `main+0x5fb254`, `main+0x36a9b8`, `main+0xcaa1cc`, and `main+0x469578`. The specific cell still has zero direct incoming references. Page-base references are broad and do not establish that code reads the particular qword at offset `+0x8b8`; no table or dispatch meaning is assigned.

The Ghidra script now prints a compact page-reference summary rather than dumping every page reference context. Reproduce with `scripts/ghidra/Run-InspectEventEncounterPathXrefs.ps1`; ignored outputs are `logs/ghidra-event-encounter-path-xrefs-v8-{script,app}.log`. Script SHA-256: `98399a4c2402dbd5b0d3915c144ec37f85d9adf093e43e0ca72ba39c58f2a97c`; wrapper SHA-256: `a77e0d35b43e950e274e06ffdc95e31e5e22268d807a232c290a9164b5f0a2a2`. The regenerated report is schema v6 and remains `CORRELATED_UNASSIGNED`. Full WSL2 suite: **146/146 in 9.681s**. Coverage remains **SCANNED 27,824; DECODED 21,456; FAILED 0; UNKNOWN 6,340; PENDING 0; UNSUPPORTED 28; 78,104 outputs**; T10 remains `IN_PROGRESS`.


### T10 event-state owner data-reference inspection — 2026-10-30

The SHA-guarded Ghidra v11 trace inspected the incoming DATA cell for FUN_710028f300, the function that directly calls the event loader at main+0x28f3ec, readiness helper at main+0x28f400, and event consumer FUN_710028f430 at main+0x28f40c. The data cell is main+0x1547368, stores main+0x28f300, and lies in writable, non-executable .data. Its observed 64-byte window at main+0x1547348 is 0x7100002a90, 0x7100011160, 0x710028f2e0, 0x710028f2f0, 0x710028f300, 0x710028f6c0, 0xffffffffffffffb8, and zero. Ghidra found no direct incoming references to this data cell; the values are recorded without assigning a vtable/table type.

The containing 4 KiB page has five references (four DATA, one READ) across three owner labels. The inspected contexts address page offsets +0x1c8, +0x820, and +0x838; none targets this pointer cell at page offset +0x368. Thus the cell and its function's direct event-loader/consumer calls form static code/data evidence, but runtime dispatch is not established. The separate main+0x15278b8 cell for FUN_710000e420 remains similarly unconnected to an instruction read.

Reproduce with scripts/ghidra/Run-InspectEventEncounterPathXrefs.ps1; the current ignored logs are logs/ghidra-event-encounter-path-xrefs-v11-{script,app}.log. Script SHA-256: a4e4840b28325bd97cfe91892aaee62e189257cc7a98943af5f4ad9625310f68; wrapper SHA-256: b14d48087d43ef38c478aed6b5aac406258ce92e7ee42c288aec64b1707c363d. The spawn-rng-crossref report is schema v7 and remains CORRELATED_UNASSIGNED. Full WSL2 tests: **146/146 in 9.015s**. Coverage remains **SCANNED 27,824; DECODED 21,456; FAILED 0; UNKNOWN 6,340; PENDING 0; UNSUPPORTED 28; 78,104 outputs**; T10 remains IN_PROGRESS.


### T10 event-state qword target inspection — 2026-10-30

A SHA-guarded Ghidra 12.2 pass inspected the eight qwords beginning at main+0x1547348 in the exact local Let's Go Pikachu 1.0.2 main (SHA-256 1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8, image base 0x7100000000). The six pointer-valued cells have DATA xrefs to code addresses. Ghidra's FunctionManager reports exact function boundaries at main+0x11160 (FUN_7100011160) and main+0x28f300 (FUN_710028f300). It reports no exact or containing function at main+0x2a90, main+0x28f2e0, main+0x28f2f0, or main+0x28f6c0, although instructions are decoded at all four locations: respectively ldr x8,[x0,#0x58], mov w0,#1 followed by ret, ret, and ret. These observations locate code and existing function boundaries; they do not assign a type or role to the qword run. The final two qwords are -0x48 and zero. The event-state cell main+0x1547368 still has zero direct incoming references in the saved database, and the five broad page references do not target that cell. Runtime dispatch remains unverified.

Reproduce with scripts/ghidra/Run-InspectEventEncounterPathXrefs.ps1. The successful v15 read-only run logs are logs/ghidra-event-encounter-path-xrefs-v15-script.log and logs/ghidra-event-encounter-path-xrefs-v15-app.log. The script SHA-256 is 23a9dcd36786bd5c4afeb1a32fd774bff49e7c212efb96eb006c5a9e618f064a; wrapper SHA-256 is 0ba6ea421867608546ba86b49a6f4d28b8a1f8483982787327483880a7346eaa. The spawn-rng-crossref report is schema v8 and remains CORRELATED_UNASSIGNED. Focused tests pass 4/4; the full WSL2 suite passes 146/146 in 9.707s. Decoder coverage is unchanged: SCANNED 27,824; DECODED 21,456; FAILED 0; UNKNOWN 6,340; PENDING 0; UNSUPPORTED 28; 78,104 outputs. T10 remains IN_PROGRESS.


### T10 event-state target incoming-reference counts — 2026-10-30

A v17 SHA-guarded Ghidra 12.2 pass queried incoming references for the six code-address qwords from the event-state data window at `main+0x1547348`. In the saved database, `main+0x2a90` has 1,175 incoming references, all DATA, and `main+0x11160` has 65, all DATA. Each of `main+0x28f2e0`, `main+0x28f2f0`, `main+0x28f300`, and `main+0x28f6c0` has one DATA reference from its matching cell in that window. These references have no containing function owner in the database. Counts and sample sources are recorded in schema v9 as `incoming_reference_summary`; they do not identify the eight-qword window's type or establish that code reads a specific entry at runtime. `CORRELATED_UNASSIGNED` is unchanged.

The same pass recorded six GFBCol-related instruction sites for the T08 investigation; those six call instructions target `main+0xb660`, but the sites are not assigned a loader role. This is corroborating address evidence only. Reproduce the T10 trace with `pwsh.exe -NoProfile -ExecutionPolicy Bypass -File scripts/ghidra/Run-InspectEventEncounterPathXrefs.ps1`. The successful v17 script SHA-256 is `e24dd90b2cbf1de394a13a178e90b57367c70435edad9d71d390407a6b8aacb9`; wrapper SHA-256 is `f7d8aa01a975e2ff36adda63d9149d0cb597b11b20049228c40ef81239358f29`; ignored script-log SHA-256 is `572446f7e403e4b3be2ce0489c61d8e42733ee6a934c9c285507f28046b3652a`. The run verified exact local `main` SHA-256 `1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8`, base `0x7100000000`, and read-only mode.

### T10 capture request and result-handler trace — 2026-10-30

A separate read-only Ghidra pass examined capture-named request/getter candidates in the exact same 1.0.2 `main`; it did not find a proved RNG-to-capture-decision-to-result chain. The getter object constructor at `main+0x1aae40` allocates `0xe0` bytes and calls `main+0x28e750`. The global at `main+0x15ff078` points to data at `main+0x1547248`; its primary vptr is at `main+0x1547258`, and the observed `+0x48` slot at `main+0x15472a0` contains `main+0x28e7f0`.

The shared request constructor at `main+0x292640` allocates `0x270` bytes. Global `main+0x15ff088` points to `main+0x15473d8`, with the main vptr at `main+0x15473e8`; its observed `+0x40` and `+0x48` cells contain `main+0x290210` and `main+0x290420`. These are pointer/data observations: the saved database shows only the corresponding DATA references, not direct code-call references, so runtime callback dispatch is unproved. `main+0x290210` reads an object string at `+0xe0`; its code at `main+0x2902cc` calls `main+0x21fb10` with a path assembled from `bin/field/param/placement/`, that string, and `.bin`, then calls shared helper `main+0xa63a0` at `main+0x2902fc`. Matching the copied string's byte offset to object `+0xe0` is structural evidence only, not capture-probability evidence. The other callback candidate contains a state machine and a stair-up/down sound literal, with no direct call to the identified RNG core. Getter candidate `main+0x28e7f0` branches to handlers at `main+0x28eb60` and `main+0x28ee10`; their returned state/result semantics remain opaque.

The investigation is reproducible with `pwsh.exe -NoProfile -ExecutionPolicy Bypass -File scripts/ghidra/Run-InspectCaptureFlowCandidates.ps1`. The wrapper checks Ghidra 12.2, exact program path/base and `main` hash, runs `-noanalysis -readOnly`, and verifies that temporary function-boundary aids were discarded from `/main`; the exact `main` source hash was unchanged before and after. The run inspected 18 existing functions plus 8 temporary candidate boundaries. Script SHA-256 is `67a6ed2892a3722182879e3dfdebc9e96507190c27deba071a135ef5e2ca776e`; wrapper SHA-256 is `0c02593c27de3e406cc9b7af0da8a2947fa467a2b774da616b622f25b899858f`. The current ignored log hashes are `e3eeb30af151a30feeeda3312818dacfbc100c10f61d7fbe16ca9bb7efe3c04e` (script) and `e6efa069154830ad1b8a65592d1bafc3f4ff04168dc1c770370e47042f1cb0f3` (application). No capture probability, outcome, PID/EC, shiny, or RNG linkage is assigned; T10 remains `IN_PROGRESS`.

### T10 getter result consumer cross-reference — 2026-10-30

The reproducible capture-candidate trace follows one getter callback's direct call at `main+0x28e934` into `main+0x28eb60`. That handler passes its object field at `+0x88` and a pointer to its field at `+0xc8` to `main+0x2baba0` (`main+0x28ebe8`), then copies `0x60` bytes from the returned record into a local buffer (`main+0x28ebf8`). It subsequently constructs a `0x2b8`-byte object through `main+0x2f5a40` and calls `main+0x2f5ec0` and `main+0x2f5f60` with that buffer (`main+0x28ec60`, `+0x28ec98`, `+0x28eca4`). The same handler copies a `u16` from object `+0xd0` to `+0xac` at two branch sites (`main+0x28ed88/+0x28ed8c` and `main+0x28edf0/+0x28edf4`).

The call to `main+0x2baba0` connects this getter result path to the same lookup helper already traced for event-table data. This is a static call and byte-copy chain, not a field-name or capture-result interpretation: the input key at `+0x88`, output record contents, copied `u16`, later helper semantics, and runtime reachability remain unknown. In particular, it does not show a catch probability, result format, or call to the identified RNG core.

### T10 capture-result record consumer follow-up — 2026-10-30

A reproducible Ghidra 12.2 pass examined the exact local Let's Go Pikachu 1.0.2 `0/main` (SHA-256 `1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8`, image base `0x7100000000`). The wrapper ran headless with `-noanalysis -readOnly`; Ghidra logged `Processing read-only project file: /main`, and the script checked the source hash again before reporting success. The final pass decompiled **10/10** defined functions, traversed **1,006 instructions**, recorded **32 direct call sites**, and had **0 failures**. The first wrapper iteration falsely returned failure because it expected a discard notice even though this no-change read-only run emitted none; the wrapper now verifies Ghidra's read-only processing line and the script's `sourceHashUnchanged=true/readOnly=true` summary.

In `FUN_710028eb60` (`main+0x28eb60`), the sole saved call reference is at `main+0x28e934`. The handler looks up a record through `main+0x2baba0`, copies `0x60` bytes to a local buffer, allocates a `0x2b8`-byte object, and calls `main+0x2f5a40`, `main+0x2f5ec0`, and `main+0x2f5f60`. The latter sets object offset `+0x298` to 1, maps the source record into an internal record beginning at object `+0x58` using `main+0x2f6000`, and copies source qwords at `+0x20/+0x28` to object offsets `+0x2a0/+0x2a8`. The direct readers `main+0x2f6b60` and `main+0x2f6b40` return those respective qwords. The handler compares them to zero and `0xc4f29ce484222645` (signed decompiler rendering `-0x340d631b7bddd9bb`) and stores values/branches through opaque fields. `main+0x2f5ec0` also writes a helper return to object `+0x29c`. None of these offsets or constants identifies a result field or outcome.

A bounded indexed path checks a supplied index against object `+0x298` and addresses records at `+0x58 + index * 0x60` (`main+0x2f6440`). Its `main+0x2f6470` helper initializes a temporary record, calls `main+0x2f6600`, allocates a `0xb8`-byte nested object, then calls additional helpers. This establishes object construction and byte-offset data flow, not a Pokémon schema. Dynamic callbacks remain indirect, and the handler's reachable runtime context, capture success/failure meaning, RNG, PID/EC, and shiny semantics remain UNKNOWN.

Reproduce with `pwsh.exe -NoProfile -ExecutionPolicy Bypass -File scripts/ghidra/Run-InspectCaptureResultConsumers.ps1`. The final ignored logs are `logs/ghidra-capture-result-consumers-v3-{script,app}.log`. Script SHA-256: `a06de6c85f3acfebf7aa70e6e8c89d2f3a7e823b0f9d9a28020975362b160192`; wrapper SHA-256: `b7784cc94a8a6a9c727b704efa6d065bfdb404523f057b44f5e0514942282b38`. The source and game assets were not modified. Source-wide totals remain **SCANNED 27,824; DECODED 21,839; FAILED 0; UNKNOWN 5,957; PENDING 0; UNSUPPORTED 28; 78,498 outputs**; T10 remains `IN_PROGRESS`.

### T10 event-record pointer-pair cross-reference — 2026-10-30

This follow-up joins the exact-build consumer trace to the actual event records. Source `../1.0.2/2b7730a9e56498bbafac2002d4908c6b_NCA/1/bin/script_event_data/event_encount.bin` is 640 bytes, SHA-256 `2bbe6321c8c25dd75ed5d11db81fa4077bd513081c0c77d72b6574874ff5e814`; the mirrored JSON is `decoded/1.0.2/romfs/bin/script_event_data/event_encount.json`, SHA-256 `2f4c59c422f832cf74d3c13d1ee50c50dc3a07a5eec397209970d646e5e2d4eb`. All 10 rows are 64 bytes, and the cross-reference checks every JSON `raw_hex` against source bytes before reading values.

On the exact LGPE Pikachu 1.0.2 `0/main` (SHA-256 `1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8`, base `0x7100000000`), Ghidra 12.2 traces `main+0x2baa10` from input row offsets `+0x10..+0x17` / `+0x18..+0x1f` to normalized record offsets `+0x20..+0x27` / `+0x28..+0x2f`, then copies 0x59 bytes to the indexed map. `main+0x2f5f60` copies those qwords to object offsets `+0x2a0/+0x2a8`; `main+0x2f6b60/+0x2f6b40` read them, and `main+0x28eb60` compares both qwords against `0xcbf29ce484222645` or both against zero. This is static data flow only.

Pinned pkNX commit `d191cd0e5c05f2af81d9a41c1f1d82e6621b351a`, source `pkNX.Structures/Encounter/Gen7/EncounterStatic7b.cs` (SHA-256 `7d6606801788be39d28890e751126f42aade289963f684ae7f27085b3d331a91`), labels the four source u32 values `Ptr0..Ptr3`. Its comment says the 0x10..0x1f region may contain text line references but does not confirm that interpretation. The actual data's `Ptr0/Ptr1` and `Ptr2/Ptr3` each pack to the two qwords consumed by the handler. Rows **0, 1, 6, 8, and 9** match the constant pair; no row has a zero pair; the other five rows match neither. The report checks all 40 property values against raw bytes, records every packed qword, pins the Ghidra trace script/wrapper hashes, and remains schema v10 / `CORRELATED_UNASSIGNED`. Ptr field meaning, handler runtime execution, and any capture-result interpretation remain UNKNOWN/UNVERIFIED.

Reproduce with `uv run lgpe spawn-rng-crossref`; this run used native Windows uv 0.11.25 with Python 3.12.13 and `UV_PROJECT_ENVIRONMENT=D:\SDK\uv-envs\lgpe-research`. The tracked report is `manifests/spawn_rng-value-crossref.json`. Focused regression: `uv run --no-sync --python 3.12.13 python -m unittest discover -s tests -p 'test_spawn_rng_crossref.py' -v` passed **4/4**. Full regression: `uv run --no-sync --python 3.12.13 python -m unittest discover -s tests -v` passed **194 tests with 1 skip**. Global coverage is unchanged: **SCANNED 27,824; DECODED 21,839; FAILED 0; UNKNOWN 5,957; PENDING 0; UNSUPPORTED 28; 78,498 outputs**.

### T10 save/filesystem API census — 2026-10-30

A read-only Ghidra 12.2 pass inspected the exact local Let's Go Pikachu 1.0.2 `0/main`, SHA-256 `1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8`, image base `0x7100000000`. The wrapper used `-noanalysis -readOnly`; the application log says `Processing read-only project file: /main`, and the Java script verified the source hash was unchanged. The trace found 6 save API symbols, 71 references, 50 total save API calls including telemetry/thunk references, 37 API caller functions, 18 filesystem API symbols, 19 direct filesystem code calls, 2 filesystem operation parent callsites, and 0 decompilation failures.

`nn::fs::IsSaveDataExisting` has one user-code call at `main+0x24e50`; `nn::fs::MountSaveData` has one at `main+0x24e6c`, both in `main+0x24d70`. In the saved reference model, direct user-code call counts are zero for `CommitSaveData`, `EnsureSaveData`, `WriteFile`, `SetFileSize`, and `DeleteFile`. The save worker at `main+0x24d70` has zero incoming references in that database, so its registration/caller is unresolved. These counts do not rule out indirect calls or wrapped operations.

The filesystem census found two `CreateFile` calls and one `FlushFile` call. The create functions are `main+0x677620` and `main+0x6777e0`, with parents `main+0x6755f0` and `main+0x675770`. The latter formats a `%u.wem` path before traversing a list; this path is not evidence of player-save ownership. `main+0x618af0` calls `FlushFile` but has no incoming references in the saved model. No player-save owner or runtime behavior is assigned.

Reproduce the trace with `pwsh.exe -NoProfile -ExecutionPolicy Bypass -File scripts/ghidra/Run-InspectSaveApiReferences.ps1`, then build `manifests/save-api-crossref.json` with `uv run lgpe save-api-crossref`. The ignored trace log is `logs/ghidra-save-api-references-v1-script.log`. Script SHA-256: `f3661b60051cde1cc875f6235545a5bcae3491da4740962107006ec3c4bfd931`; wrapper SHA-256: `872a44533faa22d31eaba294d3540eb4371fb9365be61863bce369aba581ad77`; trace-log SHA-256: `4549575b85f32a9fb855ea70ebdc5761b4ff61ec3bd116dd3360838ea7b307c2`. The report is `STATIC_REFS_ONLY`; player-save ownership is `UNKNOWN`, runtime execution is `UNVERIFIED`. Focused parser/CLI regression passed **5/5**; full native Windows regression passed **199 tests with one skip (198 passed)**. Global source totals remain **SCANNED 27,824; DECODED 21,839; FAILED 0; UNKNOWN 5,957; PENDING 0; UNSUPPORTED 28; 78,498 outputs**. T10 remains `IN_PROGRESS`.

### T10 save-worker raw pointer census — 2026-10-30

A second read-only Ghidra 12.2 pass scanned the exact local Let's Go Pikachu 1.0.2 `0/main`, SHA-256 `1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8`, base `0x7100000000`. It checked all 18 initialized readable memory blocks (23,113,044 bytes) for the worker `main+0x24d70` and its three local helpers. None of the four targets has an absolute little-endian qword match anywhere in those blocks. The saved Ghidra reference database also reports zero incoming references to the worker; the helper counts are 2, 1, and 1.

The separate non-executable image-offset dword scan found two raw matches for helper `main+0x27200`: `.rela.plt` slot `main+0xee83f3` and `.hash` slot `main+0xeeadeb`. They are retained as `UNASSIGNED_RAW_CANDIDATE`; neither is identified as a function pointer or registration entry. A separate code pass examined all 2,839,329 instructions (91,789 ADR/ADRP) for rendered ADR/ADRP operands to page `main+0x24000` and a same-register `ADD #0xd70` within the following `0x20` bytes; it found zero page or page-plus-offset candidates. This covers only those rendered instruction forms and local contexts; it does not establish the absence of copied/split address construction, other relative encodings, or indirect calls through another table. Worker registration, player-save ownership, and runtime execution therefore remain UNKNOWN/UNVERIFIED.

Reproduce with `pwsh.exe -NoProfile -ExecutionPolicy Bypass -File scripts/ghidra/Run-ScanSaveWorkerPointers.ps1`, then generate `manifests/save-worker-pointer-scan.json` with `uv run lgpe save-worker-pointer-scan`. The ignored Ghidra log is `logs/ghidra-save-worker-pointers-v1-script.log`. Script SHA-256: `10be8bacb2476af82b7376b884a415a9801686b13956b67320b9b3cdf5538075`; wrapper SHA-256: `51a24c233d494d217b5548c95c586feef29eeed1d3a27b10a23c6a181ac08960`; trace-log SHA-256: `17063287540935d822d4fc729d2728c107f7cabb29834f377aeb30255802185c`. Focused pointer-scan tests passed **4/4**; the full native Windows suite passed **203 tests with one skip (202 passed)**. Global source totals remain **SCANNED 27,824; DECODED 21,839; FAILED 0; UNKNOWN 5,957; PENDING 0; UNSUPPORTED 28; 78,498 outputs**. T10 remains `IN_PROGRESS`.

### T10 full dispatcher-body incoming-edge audit — 2026-10-30

A new SHA-guarded, read-only Ghidra 12.2 scan checked the complete defined body of `FUN_71002f8a50` in the local Let's Go Pikachu 1.0.2 `0/main` (SHA-256 `1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8`; image base `0x7100000000`). The body is one 1,052-byte range, `main+0x2f8a50..0x2f8e6b`. Across the single executable block, the scan visited **2,839,329 instructions** and found **0 direct call/jump flows from outside the body** and **0 saved Ghidra references to any instruction in the body**. A non-executable readable-memory scan covered **17 blocks / 9,286,364 bytes** and found **0 absolute qword pointers** to any body address.

The relative-dword sweep produced **10 arithmetic candidates from five byte slots**, because it tested both slot-relative and next-dword-relative bases. Two slots are unaligned byte matches with no Ghidra references. Three are 4-byte aligned: `main+0x13c3040` points to the function entry and is followed by `0x41c`, the exact body size, consistent with the already recorded range-metadata candidate; `main+0x13017a4` and `main+0x13017ac` point to body offsets `+0x14` and `+0xcc` within an 8-byte-stride sequence, but their record meaning is unassigned and neither slot has an incoming reference. None is evidence of a dispatch edge. The scan counted **96,971 computed call/jump instructions** across executable code; their runtime targets were not resolved. Thus no static direct edge to any byte of the dispatcher was recovered, while indirect/runtime reachability remains unresolved.

Reproduce with `pwsh.exe -NoProfile -ExecutionPolicy Bypass -File scripts/ghidra/Run-ScanSpawnDispatcherIncomingEdges.ps1`. The wrapper ran `-noanalysis -readOnly` and Ghidra logged `Processing read-only project file: /main`. Script SHA-256: `af8abe535974e5513872ab30878b57f67c4d3212eb650a5845c09cfecae55d86`; wrapper SHA-256: `77e823fe83aa85b26029142326f4a279455c2bc5b2355de42ba152db8fb94d50`; script-log SHA-256: `99e09b8670fbac4f4b3f22f8c48cb43fc8a2afd1b5a14bf3511de4ab76af88be`; application-log SHA-256: `ee402f275badb60494ee8ebd55363c6c2a573dd89ff6534560e398c3b767016a`. This analysis emitted no decoder rows or outputs. Source-wide coverage remains **SCANNED 27,824; DECODED 21,839; FAILED 0; UNKNOWN 5,957; PENDING 0; UNSUPPORTED 28; 78,498 outputs**. T10 remains `IN_PROGRESS`.

### T10 relative-candidate table-window xref follow-up — 2026-10-30

To check whether the aligned relative-dword candidates were referenced through a table base rather than through each entry, the read-only scan was extended to query every byte address from `center−0x40` through `center+0x40` (129 addresses inclusive) around each aligned candidate. In the saved Ghidra reference database, the windows around `main+0x13017a4` (`main+0x1301764..+0x13017e4`), `main+0x13017ac` (`main+0x130176c..+0x13017ec`), and `main+0x13c3040` (`main+0x13c3000..+0x13c3080`) have **0 references**. This supplies no static xref from code to the observed relative-record windows. It still cannot rule out a dynamically computed address or runtime registration absent from the reference database, so dispatcher reachability remains UNKNOWN.

Reproduce with the same command, `pwsh.exe -NoProfile -ExecutionPolicy Bypass -File scripts/ghidra/Run-ScanSpawnDispatcherIncomingEdges.ps1`; the latest run used the `v3` ignored logs. Script SHA-256: `008e5a15736d58aa0184b8f1e6a66de0040a8f434eda51a68550a1b122fa613b`; wrapper SHA-256: `7a1c387d8c4533d3d27a399804a791d97152b5598b7a402cd4d89c02fd5bd208`; script-log SHA-256: `26e08be3eccf96a4011b91ade55fa7be2950f7eb2041670d7c0cb8e77337ea4b`; application-log SHA-256: `68821e595c72e0c8d6d1e35d11ec23b6c8ee2c1826592c3d4d8ecf32f082a17f`. The source `main` SHA remains unchanged. No decoder rows or outputs changed; global coverage remains **SCANNED 27,824; DECODED 21,839; FAILED 0; UNKNOWN 5,957; PENDING 0; UNSUPPORTED 28; 78,498 outputs**. T10 remains `IN_PROGRESS`.

### T10 NSO RELATIVE/RELR relocation cross-reference — 2026-10-30

`uv run lgpe nso-relocation-crossref` read the actual
`../1.0.2/2b7730a9e56498bbafac2002d4908c6b_NCA/0/main` and wrote
`manifests/nso-relocation-crossref.json`. It verified the exact Pikachu 1.0.2
`main` SHA-256 `1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8`
before parsing and again afterward. The parser source is PokeLDN commit
`0afe6f61f25464767e55b909eef6b260a372bb34` (AGPL-3.0),
`tools/src/pokeldn/pokeldn/switch/nso.py`, source SHA-256
`f80e274130a5c055789815604d456271d715cdfc4f1c0528df7ce02460b3c87d`.

The extracted `.text`, `.rodata`, and `.data` segments were laid out at their
NSO memory offsets as a 23,117,872-byte segment image (SHA-256
`32ff708cc634829aeb2e39a5f39eb156d20e16237c5996f5e1299a905ffe68e9`). The
separate PokeLDN `layout()` result includes zero-filled `.bss`: 32,376,568
bytes, SHA-256
`5d598a5d3bf2c645050231b87d4b4814a31798148ab2e4dc6bae35a2aa8f9ba1`.
Neither image was written to disk. Parsing the full memory image yielded
**71,687** `R_AARCH64_RELATIVE` / RELR records.

The report checks the complete Ghidra function range for
`FUN_71002f8a50`, `[main+0x2f8a50, main+0x2f8e6c)`, so its final byte at
`main+0x2f8e6b` is included: **0** relocation addends target the body. Exact
entries `main+0x2fdf90`, `main+0x300e40`, and `main+0x3154a0` also have zero
relocation addends. Conversely, the local capture API table targets are
independently recovered in three relocation slots:
`main+0x153c870 -> main+0x1a5e80`,
`main+0x153c880 -> main+0x1a61e0`, and
`main+0x153c890 -> main+0x1a64c0`. These are slot/addend observations only;
the query does not infer a dispatch role, runtime reachability, RNG seed
initialization, or capture behavior. Computed and runtime-generated
references remain outside this relocation check.

The manifest retains the exact main hash, parser revision/license/source hash,
both in-memory image hashes, relocation count, queried ranges, every matching
slot/addend, and hashes of the existing read-only Ghidra script and wrapper.
Focused tests passed **4/4**; the full native Windows CPython 3.12.13 suite
ran **211 tests: 210 passed, 1 expected symlink-permission skip**. Source coverage
was refreshed and remains **SCANNED 27,824; DECODED 21,839; FAILED 0; UNKNOWN
5,957; PENDING 0; UNSUPPORTED 28; 78,498 outputs**. T10 remains
`IN_PROGRESS`.

## T09 cross-reference: exact-build BSEQ resource path chain — 2026-10-31

A read-only Ghidra 12.2 PUBLIC inspection of the exact Pikachu 1.0.2
`0/main` (SHA-256
`1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8`, image
base `0x7100000000`) adds a version-bound sequence resource path chain. All
addresses below are `main+offset`; none are carried over from another title or
build.

| Address | Static relation observed in the saved Ghidra program |
|---|---|
| `main+0xa81470` | Formats battle sequence paths `ew%03d%s.bseq` / `ew%03d.bseq`, then calls the shared path helper at `main+0x1d88b0`. |
| `main+0xa812c0` | Reads opaque `fileName` state, formats `%s.bseq`, and calls `main+0xaa0c60`; when its path-object check is not `1`, it uses `ee000.bseq`. |
| `main+0xa815e0` | Performs the same path-object status branch and supplies either its input path or `ee000.bseq` to `main+0xaa0c60`. |
| `main+0xaa0c60` | Allocates two `0x2a0`-byte records and passes the selected path to `main+0x2103c0`, retaining two constructed objects in the caller's `+0x10` and `+0x18` slots. The object/constructor type and final I/O consumer are not named by this evidence. |
| `main+0x2103c0` → `main+0xadc70` | At `main+0x210494`, the request constructor passes the selected path object to the shared resource helper as its resource argument; the fifth argument is zero. That helper directly calls `main+0xa63a0`, which submits through `main+0x276e0`, then waits through `main+0x23880`. |
| `main+0xa81460` | Reads owner `+0x7c == 0` as a boolean state-machine gate. |
| `main+0xa8acd0` | Contains an `ee610.bseq` / `ee615.bseq` branch; other cases call the generic `%s.bseq` handler. |

The tracked scripts are `scripts/ghidra/InspectWwiseSequenceSymbols.java`,
`scripts/ghidra/Run-InspectWwiseSequenceSymbols.ps1`,
`scripts/ghidra/InspectSequenceRuntimeHelpers.java`, and
`scripts/ghidra/Run-InspectSequenceRuntimeHelpers.ps1`. They hash-check the
local original `main` before/after read-only analysis. The helper pass found
and decompiled **11/11** selected functions and records the direct request
chain above. Ghidra is the local 12.2 PUBLIC Apache-2.0 distribution; the
configured JDK reports Java 25.0.5. Detailed marker counts, exact reproduction
commands, script/log hashes, and T09 scope limits are in
`docs/research/T09-notes.md`.

This is static reference and resource-request code evidence only. It does not
show the BSEQ request's final filesystem worker or successful physical read,
BSEQ command dispatch, Wwise action, runtime reachability, or a gameplay effect.
The separate encounter request trace to `nn::fs::OpenFile`/`ReadFile` is not
assumed to prove the BSEQ object's indirect worker route. Capture/RNG,
encounter handling, and runtime selection work remain open; T10 remains
`IN_PROGRESS`.

## T10 exact-build BSEQ request vtable and filesystem call chain — 2026-10-31

The follow-up to the earlier BSEQ trace is recorded in full under
`docs/research/T09-notes.md`. A read-only Ghidra 12.2 run against the same
Pikachu 1.0.2 `main` hash-checked the request vtable and decompiled **19/19**
selected functions. On the fresh-request path, the request initializer at
`main+0x23680` copies the selected path object's fields into its request at
`+0x60`; the shared loader can reuse an existing request. The BSEQ call path
passes literal zero as the fifth `main+0xadc70` argument, and
`main+0x237c0` stores that value at request `+0x148`, which the subsequent
open/read helpers test as an optional cache object.

The request vtable address point is `main+0x15287f8`. Slot `+0x38` resolves
to `main+0x26070`, which calls `main+0x238e0` (`nn::fs::OpenFile`, then
`GetFileSize` after a successful open), invokes slot `+0x40` at
`main+0x26610`, and then calls `main+0x23970` (conditional
`nn::fs::CloseFile`). With the BSEQ request's `+0x148` value zero, the read
handler's cache branch falls through to `main+0x23990` and its
`nn::fs::ReadFile` call. `main+0x276e0` invokes slot `+0x38` immediately only
when the TLS manager pointer at `+0x88` matches its manager argument;
otherwise it queues the request and signals a condition variable. The queued
consumer and runtime branch selection are not established by this trace.

Reproduce with `pwsh -NoProfile -File
scripts/ghidra/Run-InspectSequenceRuntimeHelpers.ps1`. The wrapper ran
`-noanalysis -readOnly`, verified exact local `main` SHA-256
`1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8` before
and after, and reported zero decompiler/function failures. The final script
SHA-256 is
`4fd4a868039274e5e1cdf52f6f99ba74430ff1c2e66ae9e705a50303cbda1653`.
Successful physical I/O, queue servicing, BSEQ semantic dispatch, Wwise
event invocation, playback, and gameplay/runtime behavior remain
`UNKNOWN`/`UNVERIFIED`. Coverage is unchanged at **27,824 SCANNED; 21,839
DECODED; 0 FAILED; 5,957 UNKNOWN; 0 PENDING; 28 UNSUPPORTED; 78,498
registered outputs**. T10 remains `IN_PROGRESS`.

## T10 exact-main BSEQ command-record consumer follow-up — 2026-10-31

The follow-up in `docs/research/T09-notes.md` identifies a static sequence
consumer after the earlier resource-path and request traces. In the exact
Pikachu 1.0.2 `main`, constructor `main+0x2103c0` copies the SESD version and
frame-bound header words into object offsets `+0x18c` and `+0x184`; the
per-frame consumer at `main+0x210510` reads both, selects version-dependent
command-record fields, and dispatches through the callback object's virtual
slot `+0x10`. A separate target-frame path reaches `main+0x210880` and uses the
same versioned record reader/callback slot. Direct caller edges were checked at
`main+0x80f5b4` and `main+0x81a888`.

This also corrects the prior T10 follow-up's limited search statement: the
header-field consumers are now identified. The callback's dynamic target and
the commands' gameplay effects remain unknown. An actual `ee000.bseq` sample
passed the pinned LGPE v3 parser and exact serialization/semantic round-trips;
its 29-frame header matches the decoded first label record's end frame. This
does not prove runtime execution or playback. The read-only helper decompiled
31/31 selected functions with no failures; the exact build SHA and the offset
sweep's broad-hit limitation are recorded in T09 notes. BSEQ coverage remains
**381 SCANNED / 353 DECODED / 0 FAILED / 0 UNKNOWN / 28 UNSUPPORTED**; global
coverage remains **27,824 SCANNED / 21,839 DECODED / 0 FAILED / 5,957 UNKNOWN
/ 0 PENDING / 28 UNSUPPORTED / 78,498 outputs**. T10 remains `IN_PROGRESS`.

## T10 BSEQ object vtable and selector-caller follow-up — 2026-10-31

A further exact-build read-only pass decompiled **27/27** selected functions
with no failures. The object vptr installed by `main+0x2103c0` resolves through
global cell `main+0x15fe628` to address point `main+0x1541e40`; its first two
slots lead to `main+0x2109e0` and `main+0x210ae0`, whose observed bodies reset
request state and call `main+0x23c70`. They do not consume the two header
values copied into object offsets `+0x184/+0x18c`. Exact BSEQ path-selection
callers include `main+0x1db010`, `main+0xa812c0`, `main+0xa8acd0`,
`main+0xa8ce20`, and `main+0xa81690`; their branch and path evidence is
documented in the T09 note. This narrows the search boundary to downstream
consumers of the constructed object/header fields. It does not establish
BSEQ command dispatch or selector semantics. Script SHA-256:
`965f39182fb870456eccb5636ff09f81738a326deb9220b1251c2e7c2dfd9016`.
Coverage remains **27,824 SCANNED; 21,839 DECODED; 0 FAILED; 5,957 UNKNOWN;
0 PENDING; 28 UNSUPPORTED; 78,498 registered outputs**. T10 remains
`IN_PROGRESS`.

## T10 BSEQ callback and command-table cross-reference — 2026-10-31

The exact-build follow-up in `docs/research/T09-notes.md` now traces the
delegate installed at controller `+0x3e0` into the sequence callback field at
`main+0x2103c0` `+0x190`, then resolves the callback virtual `+0x10` to
`main+0xaa0eb0`. The exact 1.0.2 per-frame reader passes mode `0` and reaches
the handler pointer table; the target-frame reader passes mode `1` and reaches
the inline switch. A capped 256-entry probe found 256/256 executable pointers;
no table terminator was reached. The pinned LGPE command reference contributes
227 unique numeric ID cross-references, and all five commands in actual
`ee000.bseq` map to table slots and decompiled targets. A later exact-byte
probe corrects the prior `DummyLabel` note: `main+0xada060` is a one-instruction
`ret` (`c0 03 5f d6`), with one DATA reference from dispatch slot 0.

The structured report is `manifests/bseq-runtime-dispatch.json`, generated by
`python3 scripts/research/build_bseq_runtime_dispatch.py`. Ghidra helper
decompilation was 40/40 with zero failures; the callback pass created five
missing function definitions in the local Ghidra project and decompiled 8/8
targets with zero failures. Both runs checked the exact original `main` hash
before and after; no original game data was modified. This resolves the static
callback and dispatch routes, not runtime execution, handler semantics,
dispatch table length, or gameplay effects. BSEQ coverage remains **381
SCANNED / 353 DECODED / 0 FAILED / 0 UNKNOWN / 28 UNSUPPORTED**; overall
coverage remains **27,824 SCANNED / 21,839 DECODED / 0 FAILED / 5,957 UNKNOWN
/ 0 PENDING / 28 UNSUPPORTED / 78,498 outputs**. T10 remains `IN_PROGRESS`.

## T10 BSEQ handler target byte verification — 2026-10-31

The exact-build Ghidra 12.2 `-noanalysis -readOnly` probe verified the
Pikachu 1.0.2 `main` hash before and after. `main+0xada060` is a 4-byte AArch64
`ret` (`c0 03 5f d6`), and its only saved incoming reference is the DATA
pointer at handler-table slot 0 (`main+0x15d4c70`). This resolves the previous
`br x16` recording error at that address without assigning command semantics.

An extended memory scan read indexes **256–1351**, or **1,096** mapped slots,
with **858** values targeting executable memory and **238** targeting
non-executable memory. It stopped after eight consecutive non-executable
values at indexes 1344–1351. The values after index 255 can include adjacent
pointer data, so this does not establish the table's full length or command-ID
bounds. The evidence is in `manifests/bseq-dispatch-boundary.json`; reproduce
the trace with `pwsh.exe -NoProfile -ExecutionPolicy Bypass -File
scripts/ghidra/Run-InspectBseqDispatchBoundary.ps1` and refresh the manifest
with `uv run lgpe bseq-dispatch-boundary`. Five new focused tests pass; the
four dispatch-manifest tests also pass. Coverage is unchanged: BSEQ **381
SCANNED / 353 DECODED / 0 FAILED / 0 UNKNOWN / 28 UNSUPPORTED**, global
**27,824 SCANNED / 21,839 DECODED / 0 FAILED / 5,957 UNKNOWN / 0 PENDING /
28 UNSUPPORTED / 78,498 outputs**. T10 remains `IN_PROGRESS`.


## T10 capture getter / API wrapper cross-reference — 2026-10-31

A read-only Ghidra 12.2 trace inspected the actual Pikachu 1.0.2 `0/main`
(SHA-256 `1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8`,
image base `0x7100000000`). The wrapper pinned the local NCA ID, verified the
source hash before and after, and invoked `-noanalysis -readOnly`. It
successfully decompiled **7 functions / 1,264 instructions / 71 direct calls**
with zero failures. One missing boundary at `main+0x28e7f0` was temporary and
discarded with the read-only project.

The existing exact-build API registry trace pairs `main+0x1a64c0` with the
local `GetCaptureResult` registry entry at `main+0x153c890`. This pass records a
DATA reference from that cell to `main+0x1a64c0` (no containing data/function
owner) and a direct call at `main+0x1a6524` to `main+0x1aae40`. Its decompiled
wrapper reads a qword from `param_2+0x8`, constructs/queries a helper object,
and on one branch copies that qword to an output object at `+0xc8`, writes zero
to a 16-bit field at `+0xd0`, and returns constant zero. These offsets and the
input value's purpose remain opaque. The helper at `main+0x1aae40` allocates
`0xe0` bytes and returns an opaque pointer through its output parameter; no
capture result meaning is assigned.

The separate temporary candidate at `main+0x28e7f0` has one incoming DATA
reference from `main+0x15472a0`, not a code-call edge. Its decompilation places
`main+0x28eb60` in switch case 2, increments state, then continues into case 3
and calls `main+0x28ee10`; this is static decompiler control-flow evidence,
and the boundary is not persisted. Helper `main+0x28ee10` allocates `0x3b0`
bytes, reads qwords through `param_2+0x68/+0x70`, and writes an opaque pointer
through `param_1`. It has four direct references: `main+0x28e978` (temporary
owner), `main+0x3059d4` (owner `main+0x305970`), `main+0x319fe0` (owner
`main+0x319f80`), and `main+0x8549fc` (no saved owner). The latter two saved
owners have incoming sites at `main+0x2fdf34/+0x2fdf80` and
`main+0x319cc4`, respectively. In the unowned `0x8549fc` window, `x1` is
loaded from an object at `+0x68`, `x0` is `x22`, and a returned stack qword at
`sp+0x58` is later stored to `sp+0x20`; the owning function and value meanings
remain unknown. The shared helper is not established as capture-specific.

The schema-v2 report is `manifests/capture-getter-callers.json`. Reproduce the
read-only Ghidra pass with `pwsh.exe -NoProfile -ExecutionPolicy Bypass -File
scripts/ghidra/Run-InspectCaptureGetterCallers.ps1`, then regenerate the
manifest with `UV_PROJECT_ENVIRONMENT=/tmp/lgpe-research-t07-venv uv run lgpe
capture-getter-crossref`. Java probe SHA-256:
`ba12229eb27b220166727ebc7d2e6f0641d998bc47bcc99849758a7d345636da`; wrapper
SHA-256: `21306dd34f04009684be043710418c3c47263cf29397933fe92f82dac1d0beea`;
Ghidra stdout log SHA-256:
`b843837879c03a3e1466b701d2468639868e1217ef9df4fa175fc966ad7c3678`; manifest
SHA-256: `3a2ad322359e2a4dbf808c9f5d1aa30e46b0f1eef8458962a7cf5ec9884822ac`.
Focused tests pass **5/5**; native PowerShell 7 full regression passes **261
tests, 260 passed, one expected skip, in 64.747s**. A WSL suite attempt was
interrupted after waiting on a mapped-drive WAV read (`p9_client_rpc`) and is
not counted as a test failure. No source resource or decoder status changed.
Global coverage remains **SCANNED 27,824; DECODED 21,839; FAILED 0; UNKNOWN
5,957; PENDING 0; UNSUPPORTED 28; 78,498 registered outputs**. Capture
outcome/probability, RNG linkage, and runtime execution remain UNKNOWN or
UNVERIFIED; T10 remains `IN_PROGRESS`.

## T10 exact-build capture API resource literal search — 2026-10-31

Ran the native Windows wrapper `scripts/research/Run-CaptureApiResourceSearch.ps1`, which invokes `uv run lgpe capture-api-resource-search` against the local 1.0.2 dump. The CLI verified the actual `0/main` SHA-256 as `1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8` before binding the report to this build. It scanned **10,770** actual RomFS message `.dat`/`.tbl` files (**32,878,553 bytes**), **7** loose battle AI `.amx` files (**139,256 bytes**), and **705** raw extracted members under `script_amx.gfpak.contents` (**2,613,253 bytes**): **11,482 files / 35,631,062 bytes total**. JSON sidecars were excluded from the archive-member byte search.

Case-insensitive literal searches for `CaptureCall` and `GetCaptureResult` in ASCII, UTF-16LE, and UTF-16BE returned **0 occurrences**. The structured result is `manifests/capture-api-resource-search.json` (`NO_LITERAL_REFERENCE`, SHA-256 `f939a93c89bb3cc6fd1c4df161fdddbebfe53d2829b0c58c9eebd45740fc2ac3`). It includes a relative path, byte size, and SHA-256 for every one of the 11,482 scanned files; the receipt sizes sum to the recorded 35,631,062 bytes. A separate decoded-JSON sweep using `rg --no-ignore` also found no literal occurrence; `--no-ignore` is required because `decoded/` is gitignored. These bounded misses do not rule out numeric/hashed identifiers, other resource formats, generic registry dispatch, compressed data, or runtime-created calls and do not change the unresolved capture wrapper semantics.

Focused tests: **3/3 passed**. Native Windows full regression passed **264 tests: 263 passed, 1 expected symlink-permission skip, in 40.392s**. No source asset or decoder receipt changed. Global coverage remains **SCANNED 27,824; DECODED 21,839; FAILED 0; UNKNOWN 5,957; PENDING 0; UNSUPPORTED 28; 78,498 outputs**. Reproduce with `pwsh.exe -NoProfile -ExecutionPolicy Bypass -File scripts/research/Run-CaptureApiResourceSearch.ps1`; T10 remains `IN_PROGRESS`.

## T10 script-registry explicit operand scan — 2026-10-31

The new parser and CLI tests are included in a native Windows regression of **269 tests: 268 passed, 1 expected symlink-permission skip, in 67.098s**.

The native Windows wrapper `scripts/ghidra/Run-InspectScriptRegistryOperandScan.ps1` ran Ghidra 12.2 with `-noanalysis -readOnly` against the saved exact-build `main` program. It SHA-guarded original `0/main` before and after; the hash stayed `1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8`. The probe traversed **2,839,329** instructions and found **13** instruction operands explicitly materializing page `0x710153c000` (`main+0x153c000`); the four owned functions decompiled **4/4**, with **0** failures. The manifest preserves all 13 hit instructions and their 8-instruction context on either side.

Among those contexts, `main+0x1a61d0` computes `0x710153c878` (`main+0x153c878`), the already identified `MapChangeCore_` name-pointer cell. Other page constructions resolve from the visible `ADRP`/`ADD` sequences to `main+0x153ced8`, `main+0x153cf20`, `main+0x153cf68`, or `main+0x153cfb0`. No captured context constructs the `CaptureCall` function-pointer cell `main+0x153c880` or `GetCaptureResult` cell `main+0x153c890`. The recorded windows therefore provide no explicit operand path to either function slot; this does not exclude longer dataflow, dynamic indexing, pointers loaded through another base, or runtime dispatch.

The report is `manifests/script-registry-operand-scan.json` (SHA-256 `8a5d04a87512b31ac736c91e754c97ed995ee73745706423af8905fd8efb21a4`). Java probe SHA-256 `49ba74970208ee13cfa61d80cbbb4ae1335d547358c76fffe067d33ddef675b0`; wrapper SHA-256 `45c211228665b40c4726be8d5f893db3f0b58bfed5ce11001ee10009dfea19ed`; Ghidra evidence-log SHA-256 `b4a43f0fabd1f9f5de1025a4d9eb43e0153e7e4eb220d5eff675d294bf95781a`. Reproduce with `pwsh.exe -NoProfile -ExecutionPolicy Bypass -File scripts/ghidra/Run-InspectScriptRegistryOperandScan.ps1`; the wrapper also runs `uv run lgpe script-registry-operand-scan` to validate and write the manifest. This is instruction-operand evidence only; registration dispatch, `GetCaptureResult` semantics, and runtime reachability remain UNKNOWN. Source-wide counts remain **SCANNED 27,824; DECODED 21,839; FAILED 0; UNKNOWN 5,957; PENDING 0; UNSUPPORTED 28; 78,498 outputs**. T10 remains `IN_PROGRESS`.


## T10 exact-build registry cell values and target-byte cross-reference - 2026-10-31

A SHA-guarded Ghidra 12.2 `-noanalysis -readOnly` follow-up read seven actual qword cells and their saved references. Original `0/main` remained SHA-256 `1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8` before and after.

| Cell (main-relative) | Observed qword | Static evidence |
|---|---:|---|
| `+0x153c878` (MapChangeCore_ name pointer) | `0x7100f01b93` | One saved DATA reference from `main+0x1a61d4`, in the function beginning at `main+0x1a61d0`. |
| `+0x153c880` (CaptureCall function-pointer slot) | `0x71001a61e0` | Executable target; saved incoming-reference count is 0. |
| `+0x153c890` (GetCaptureResult function-pointer slot) | `0x71001a64c0` | Executable target; saved incoming-reference count is 0. |
| `+0x153ced8` | `0x7100193c90` | Executable target; temporary read-only function boundary. |
| `+0x153cf20` | `0x71001abcd0` | Executable target; temporary read-only function boundary. |
| `+0x153cf68` | `0x7100193c90` | Same target as `+0x153ced8`; boundary shared. |
| `+0x153cfb0` | `0x71001abf40` | Executable target; temporary read-only function boundary. |

The four neighboring candidate cells resolve to three unique code targets. Each has one decoded AArch64 instruction, `ret` (`c0 03 5f d6`), over 4 bytes. Ghidra temporarily established boundaries for all three targets, decompiled **3/3**, and reported **0** failures; the read-only wrapper discarded temporary changes. The report retains saved DATA xrefs, including multiple references to `main+0x193c90` from these cells and an additional cell at `main+0x153b7c8`.

Zero saved incoming references to the two API function-pointer cells describes only Ghidra's persisted reference database; it does not rule out computed accesses, dynamic indexing, references through another base, or runtime dispatch. The four neighboring cells' roles are not identified, and the one-instruction return stubs do not establish call semantics.

The refreshed report is `manifests/script-registry-operand-scan.json`, SHA-256 `0c469f0dfa3edc011890224e058e0042e7824cd09dc041218daec4b7435615d1`. Java probe SHA-256 `c3fe92fbd99a44849225e5583e925cec8de673b8f4d8ddfbdbad922308198280`; wrapper SHA-256 `935f6485ebe8d0191a2d2f36319e88b4f7129ce27f0154a5f7ac5508733c1b2e`; Ghidra stdout log SHA-256 `a4563319f300224d316c4bf83d107ed75265e450015fae28b3074940a2992907`. Reproduce with `pwsh.exe -NoProfile -ExecutionPolicy Bypass -File scripts/ghidra/Run-InspectScriptRegistryOperandScan.ps1`; the wrapper rechecks the source hash and validates/regenerates the report with `uv run lgpe script-registry-operand-scan`.

Native Windows regression passed **269 tests: 268 passed, 1 expected symlink-permission skip, in 68.483s**. Asset totals did not change: **27,824 SCANNED; 21,839 DECODED; 0 FAILED; 5,957 UNKNOWN; 0 PENDING; 28 UNSUPPORTED; 78,498 outputs**. T10 remains `IN_PROGRESS`.
