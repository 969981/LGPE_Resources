import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionIterator;
import ghidra.program.model.listing.FunctionManager;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;
import ghidra.program.model.symbol.Symbol;
import ghidra.program.model.symbol.SymbolIterator;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;

/** Read-only save API and callsite inventory for the exact local LGPE 1.0.2 main. */
public class InspectSaveApiReferences extends GhidraScript {
    private static final String EXPECTED_MAIN_SHA256 =
        "1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8";
    private static final long EXPECTED_BASE = 0x7100000000L;
    private static final String EXPECTED_NCA_ID = "2b7730a9e56498bbafac2002d4908c6b";
    private static final long SAVE_WORKER = 0x7100024d70L;
    private static final long[] SAVE_HELPERS = {
        0x7100027200L, 0x7100027440L, 0x71000275f0L
    };

    @Override
    public void run() throws Exception {
        String executable = currentProgram.getExecutablePath();
        String normalized = executable == null ? "" : executable.trim().replace('\\', '/');
        if (currentProgram.getImageBase().getOffset() != EXPECTED_BASE
            || !normalized.toLowerCase(Locale.ROOT).contains(EXPECTED_NCA_ID)
            || !normalized.toLowerCase(Locale.ROOT).endsWith("/0/main")) {
            throw new IllegalStateException("not the recorded LGPE 1.0.2 main program");
        }
        String sourceHashBefore = sha256(executable.trim());
        if (!EXPECTED_MAIN_SHA256.equals(sourceHashBefore)) {
            throw new IllegalStateException("source main SHA-256 mismatch: " + sourceHashBefore);
        }

        FunctionManager manager = currentProgram.getFunctionManager();
        List<Symbol> saveApis = new ArrayList<>();
        Set<String> fileSystemApiNames = new java.util.TreeSet<>();
        SymbolIterator allSymbols = currentProgram.getSymbolTable().getExternalSymbols();
        while (allSymbols.hasNext()) {
            Symbol symbol = allSymbols.next();
            String qualifiedName = symbol.getName(true);
            String lowerName = qualifiedName.toLowerCase(Locale.ROOT);
            if (lowerName.contains("nn::fs::")) {
                fileSystemApiNames.add(qualifiedName);
            }
            if (lowerName.contains("save")) {
                saveApis.add(symbol);
            }
        }
        for (String apiName : fileSystemApiNames) {
            println("FS_API_SYMBOL\t" + apiName);
        }

        int apiReferences = 0;
        int apiCalls = 0;
        int mountCalls = 0;
        int existingCalls = 0;
        Set<String> callerEntries = new HashSet<>();
        Map<String, Integer> codeCallsByApi = new TreeMap<>();
        Map<String, Integer> fsCodeCallsByApi = new TreeMap<>();
        Map<String, Function> mutationCallers = new TreeMap<>();
        Map<String, Function> operationParents = new TreeMap<>();
        for (Symbol api : saveApis) {
            println("API_SYMBOL\t" + api.getAddress() + "\t" + api.getName(true)
                + "\texternal_symbol=true");
        }

        FunctionIterator allProgramFunctions = manager.getFunctions(true);
        while (allProgramFunctions.hasNext()) {
            Function function = allProgramFunctions.next();
            if (function.isExternal()) continue;
            Function resolved = function;
            if (function.isThunk()) {
                Function thunked = function.getThunkedFunction(true);
                if (thunked != null) resolved = thunked;
            }
            String apiName = resolved.getName(true);
            String lowerName = apiName.toLowerCase(Locale.ROOT);
            boolean isFileSystemApi = lowerName.contains("nn::fs::");
            if (!isFileSystemApi && !lowerName.contains("save")) continue;
            println("API_THUNK\t" + function.getEntryPoint() + "\t" + apiName
                + "\tisThunk=" + function.isThunk());
            ReferenceIterator incoming = currentProgram.getReferenceManager()
                .getReferencesTo(function.getEntryPoint());
            while (incoming.hasNext()) {
                Reference reference = incoming.next();
                Function caller = manager.getFunctionContaining(reference.getFromAddress());
                boolean isCall = reference.getReferenceType().isCall();
                apiReferences++;
                if (isCall) {
                    apiCalls++;
                    if (caller != null) callerEntries.add(caller.getEntryPoint().toString());
                    if (caller != null && !caller.isThunk()) {
                        codeCallsByApi.put(apiName, codeCallsByApi.getOrDefault(apiName, 0) + 1);
                        if (isFileSystemApi) {
                            fsCodeCallsByApi.put(apiName,
                                fsCodeCallsByApi.getOrDefault(apiName, 0) + 1);
                        }
                        if (apiName.endsWith("nn::fs::MountSaveData")) mountCalls++;
                        if (apiName.endsWith("nn::fs::IsSaveDataExisting")) existingCalls++;
                        if (isFilesystemMutation(apiName)) {
                            mutationCallers.put(caller.getEntryPoint().toString(), caller);
                            println("FS_OPERATION_CALLSITE\t" + reference.getFromAddress()
                                + "\t" + apiName + "\tcaller=" + caller.getEntryPoint()
                                + "\tcaller_name=" + caller.getName());
                        }
                    }
                }
                println("API_XREF\t" + reference.getFromAddress() + "\t"
                    + reference.getReferenceType() + "\t" + apiName + "\tcaller="
                    + (caller == null ? "<no-function>" : caller.getEntryPoint()) + "\tcaller_name="
                    + (caller == null ? "<no-function>" : caller.getName()));
            }
        }
        for (Symbol api : saveApis) {
            String apiName = api.getName(true);
            println("API_CODE_CALLS\t" + apiName + "\tcount="
                + codeCallsByApi.getOrDefault(apiName, 0));
        }
        for (String apiName : fileSystemApiNames) {
            println("FS_API_CODE_CALLS\t" + apiName + "\tcount="
                + fsCodeCallsByApi.getOrDefault(apiName, 0));
        }
        println("FS_OPERATION_CALLER_COUNT\tcount=" + mutationCallers.size());
        for (Function operationCaller : mutationCallers.values()) {
            int incomingCount = inspectIncoming("FS_OPERATION_OWNER",
                operationCaller.getEntryPoint());
            println("FS_OPERATION_OWNER_XREF_SUMMARY\tfunction="
                + operationCaller.getEntryPoint() + "\tname=" + operationCaller.getName()
                + "\tincoming_references=" + incomingCount);
            ReferenceIterator incoming = currentProgram.getReferenceManager()
                .getReferencesTo(operationCaller.getEntryPoint());
            while (incoming.hasNext()) {
                Reference reference = incoming.next();
                Function caller = manager.getFunctionContaining(reference.getFromAddress());
                if (!reference.getReferenceType().isCall() || caller == null || caller.isThunk()) {
                    continue;
                }
                operationParents.put(caller.getEntryPoint().toString(), caller);
                println("FS_OPERATION_PARENT_CALLSITE\t" + reference.getFromAddress()
                    + "\tchild=" + operationCaller.getEntryPoint() + "\tparent="
                    + caller.getEntryPoint() + "\tparent_name=" + caller.getName());
            }
        }
        println("FS_OPERATION_PARENT_COUNT\tcount=" + operationParents.size());

        int workerIncoming = inspectIncoming("SAVE_WORKER", toAddr(SAVE_WORKER));
        DecompInterface decompiler = new DecompInterface();
        decompiler.openProgram(currentProgram);
        int decompileFailures = 0;
        List<Function> targets = new ArrayList<>();
        targets.addAll(operationParents.values());
        targets.addAll(mutationCallers.values());
        Function worker = manager.getFunctionAt(toAddr(SAVE_WORKER));
        if (worker == null) throw new IllegalStateException("save worker function missing");
        targets.add(worker);
        for (long address : SAVE_HELPERS) {
            Function helper = manager.getFunctionAt(toAddr(address));
            if (helper == null) throw new IllegalStateException("save helper missing at 0x" + Long.toHexString(address));
            targets.add(helper);
        }
        Set<String> decompiledEntries = new HashSet<>();
        for (Function target : targets) {
            if (!decompiledEntries.add(target.getEntryPoint().toString())) continue;
            println("FUNCTION\t" + target.getEntryPoint() + "\t" + target.getName()
                + "\tbytes=" + target.getBody().getNumAddresses());
            DecompileResults result = decompiler.decompileFunction(target, 120, monitor);
            if (!result.decompileCompleted() || result.getDecompiledFunction() == null) {
                println("DECOMPILE_FAILED\t" + target.getEntryPoint() + "\t"
                    + result.getErrorMessage());
                decompileFailures++;
                continue;
            }
            println("DECOMPILED_BEGIN\t" + target.getEntryPoint());
            println(result.getDecompiledFunction().getC());
            println("DECOMPILED_END\t" + target.getEntryPoint());
        }
        decompiler.dispose();

        String sourceHashAfter = sha256(executable.trim());
        if (!sourceHashBefore.equals(sourceHashAfter)) {
            throw new IllegalStateException("source main changed during read-only inspection");
        }
        println("SUMMARY\tmain_sha256=" + sourceHashAfter
            + "\timage_base=0x" + Long.toHexString(currentProgram.getImageBase().getOffset())
            + "\tsave_api_symbols=" + saveApis.size()
            + "\tsave_api_references=" + apiReferences
            + "\tsave_api_calls=" + apiCalls
            + "\tmount_calls=" + mountCalls
            + "\texisting_calls=" + existingCalls
            + "\tworker_incoming_references=" + workerIncoming
            + "\tunique_api_caller_functions=" + callerEntries.size()
            + "\tfilesystem_api_symbols=" + fileSystemApiNames.size()
            + "\tfilesystem_api_code_calls=" + fsCodeCallsByApi.values().stream()
                .mapToInt(Integer::intValue).sum()
            + "\tfilesystem_operation_parents=" + operationParents.size()
            + "\tdecompile_failures=" + decompileFailures
            + "\tsourceHashUnchanged=true\treadOnly=true");
    }

    private boolean isFilesystemMutation(String apiName) {
        return apiName.endsWith("nn::fs::CreateFile")
            || apiName.endsWith("nn::fs::DeleteFile")
            || apiName.endsWith("nn::fs::SetFileSize")
            || apiName.endsWith("nn::fs::FlushFile")
            || apiName.endsWith("nn::fs::WriteFile")
            || apiName.endsWith("nn::fs::CommitSaveData")
            || apiName.endsWith("nn::fs::EnsureSaveData");
    }

    private int inspectIncoming(String label, Address target) {
        int count = 0;
        ReferenceIterator references = currentProgram.getReferenceManager().getReferencesTo(target);
        while (references.hasNext()) {
            Reference reference = references.next();
            Function caller = currentProgram.getFunctionManager()
                .getFunctionContaining(reference.getFromAddress());
            println("INTERNAL_XREF\t" + label + "\t" + reference.getFromAddress() + "\t"
                + reference.getReferenceType() + "\tcaller="
                + (caller == null ? "<no-function>" : caller.getEntryPoint()) + "\tcaller_name="
                + (caller == null ? "<no-function>" : caller.getName()));
            count++;
        }
        println("INTERNAL_TARGET\t" + label + "\t" + target + "\tincoming_references=" + count);
        return count;
    }

    private String sha256(String path) throws Exception {
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        try (InputStream input = Files.newInputStream(Paths.get(path))) {
            byte[] buffer = new byte[1024 * 1024];
            int count;
            while ((count = input.read(buffer)) >= 0) digest.update(buffer, 0, count);
        }
        StringBuilder result = new StringBuilder();
        for (byte value : digest.digest()) result.append(String.format("%02x", value & 0xff));
        return result.toString();
    }
}
