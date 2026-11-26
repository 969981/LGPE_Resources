import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Data;
import ghidra.program.model.listing.DataIterator;
import ghidra.program.model.listing.Function;
import ghidra.program.model.mem.MemoryBlock;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.util.HashSet;
import java.util.Locale;
import java.util.Set;

public class InspectGrammarDataReferences extends GhidraScript {
    private static final long EXPECTED_BASE = 0x7100000000L;
    private static final String EXPECTED_NCA_ID = "2b7730a9e56498bbafac2002d4908c6b";
    private static final String EXPECTED_MAIN_SHA256 =
        "1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8";
    private final Set<String> seenRawMatches = new HashSet<>();
    private int definedMatches;
    private int rawMatches;
    private int xrefs;
    private int decompiled;

    @Override
    public void run() throws Exception {
        String executable = currentProgram.getExecutablePath();
        String normalized = executable == null ? "" : executable.trim().replace('\\', '/');
        if (currentProgram.getImageBase().getOffset() != EXPECTED_BASE
            || !normalized.toLowerCase(Locale.ROOT).contains(EXPECTED_NCA_ID)
            || !normalized.toLowerCase(Locale.ROOT).endsWith("/0/main")) {
            throw new IllegalStateException("not the recorded LGPE 1.0.2 main program");
        }
        String mainHash = sha256(Path.of(executable.trim()));
        if (!EXPECTED_MAIN_SHA256.equals(mainHash)) {
            throw new IllegalStateException("source main SHA-256 mismatch: " + mainHash);
        }
        println("PROGRAM\tversion=Pokemon Let's Go Pikachu 1.0.2\tbase="
            + currentProgram.getImageBase() + "\tmain_sha256=" + mainHash);
        scanDefinedStrings();
        inspectLoaderIncomingReferences();
        scanInitializedNonExecutableBlocks();
        println("SUMMARY\tdefined_grammar_strings=" + definedMatches
            + "\traw_ascii_or_utf16_matches=" + rawMatches
            + "\tdirect_string_xrefs=" + xrefs
            + "\tdecompiled_xref_functions=" + decompiled
            + "\tprogram=" + currentProgram.getName());
    }

    private void scanDefinedStrings() throws Exception {
        DataIterator iterator = currentProgram.getListing().getDefinedData(true);
        DecompInterface decompiler = new DecompInterface();
        decompiler.openProgram(currentProgram);
        Set<String> decompiledFunctions = new HashSet<>();
        while (iterator.hasNext()) {
            monitor.checkCancelled();
            Data data = iterator.next();
            Object value = data.getValue();
            if (!(value instanceof String)) continue;
            String text = (String) value;
            if (!text.toLowerCase(Locale.ROOT).contains("grammar")) continue;
            definedMatches++;
            println("DEFINED_GRAMMAR_STRING\taddress=" + data.getAddress()
                + "\ttext=" + escape(text));
            ReferenceIterator references = currentProgram.getReferenceManager()
                .getReferencesTo(data.getAddress());
            while (references.hasNext()) {
                monitor.checkCancelled();
                Reference reference = references.next();
                Function caller = currentProgram.getFunctionManager()
                    .getFunctionContaining(reference.getFromAddress());
                println("STRING_XREF\tfrom=" + reference.getFromAddress()
                    + "\ttype=" + reference.getReferenceType()
                    + "\tfunction=" + (caller == null ? "<no-function>" : caller.getEntryPoint())
                    + "\tname=" + (caller == null ? "<no-function>" : caller.getName()));
                xrefs++;
                if (caller != null && decompiledFunctions.add(caller.getEntryPoint().toString())
                    && decompiledFunctions.size() <= 12) {
                    decompile(decompiler, caller);
                }
            }
        }
        decompiler.dispose();
    }

    private void decompile(DecompInterface decompiler, Function function) throws Exception {
        DecompileResults result = decompiler.decompileFunction(function, 60, monitor);
        if (!result.decompileCompleted() || result.getDecompiledFunction() == null) {
            println("DECOMPILE_FAILED\tfunction=" + function.getEntryPoint()
                + "\terror=" + escape(result.getErrorMessage()));
            return;
        }
        String code = result.getDecompiledFunction().getC();
        println("DECOMPILED_BEGIN\tfunction=" + function.getEntryPoint()
            + "\tname=" + function.getName() + "\tchars=" + code.length());
        String[] lines = code.split("\\R", -1);
        for (int index = 0; index < lines.length; index++) {
            println("CODE\t" + function.getEntryPoint() + "\t" + index
                + "\t" + lines[index].replace("\t", "\\t"));
        }
        println("DECOMPILED_END\tfunction=" + function.getEntryPoint());
        decompiled++;
    }

    private void inspectLoaderIncomingReferences() throws Exception {
        Address address = currentProgram.getImageBase().add(0x1ae750L);
        Function loader = currentProgram.getFunctionManager().getFunctionAt(address);
        if (loader == null) {
            println("LOADER_FUNCTION_NOT_FOUND\taddress=" + address);
            return;
        }
        DecompInterface decompiler = new DecompInterface();
        decompiler.openProgram(currentProgram);
        ReferenceIterator references = currentProgram.getReferenceManager()
            .getReferencesTo(loader.getEntryPoint());
        Set<String> callerEntries = new HashSet<>();
        int incomingCount = 0;
        while (references.hasNext()) {
            monitor.checkCancelled();
            Reference reference = references.next();
            Function caller = currentProgram.getFunctionManager()
                .getFunctionContaining(reference.getFromAddress());
            println("LOADER_INCOMING\tfrom=" + reference.getFromAddress()
                + "\ttype=" + reference.getReferenceType()
                + "\tcaller=" + (caller == null ? "<no-function>" : caller.getEntryPoint())
                + "\tname=" + (caller == null ? "<no-function>" : caller.getName()));
            incomingCount++;
            if (caller != null && reference.getReferenceType().isCall()
                && callerEntries.add(caller.getEntryPoint().toString())) {
                decompile(decompiler, caller);
                ReferenceIterator parents = currentProgram.getReferenceManager()
                    .getReferencesTo(caller.getEntryPoint());
                int parentCount = 0;
                Set<String> parentEntries = new HashSet<>();
                while (parents.hasNext() && parentCount < 32) {
                    monitor.checkCancelled();
                    Reference parentReference = parents.next();
                    Function parent = currentProgram.getFunctionManager()
                        .getFunctionContaining(parentReference.getFromAddress());
                    println("LOADER_CALLER_INCOMING\tcaller=" + caller.getEntryPoint()
                        + "\tfrom=" + parentReference.getFromAddress()
                        + "\ttype=" + parentReference.getReferenceType()
                        + "\tparent=" + (parent == null ? "<no-function>" : parent.getEntryPoint())
                        + "\tname=" + (parent == null ? "<no-function>" : parent.getName()));
                    parentCount++;
                    if (parent != null && parentReference.getReferenceType().isCall()
                        && parentEntries.add(parent.getEntryPoint().toString())) {
                        decompile(decompiler, parent);
                    }
                }
                println("LOADER_CALLER_INCOMING_COUNT\tcaller=" + caller.getEntryPoint()
                    + "\tcount=" + parentCount);
            }
        }
        decompiler.dispose();
        println("LOADER_INCOMING_COUNT\tcount=" + incomingCount);
    }

    private void scanInitializedNonExecutableBlocks() throws Exception {
        byte[] ascii = "grammar".getBytes(java.nio.charset.StandardCharsets.US_ASCII);
        byte[] utf16 = "grammar".getBytes(java.nio.charset.StandardCharsets.UTF_16LE);
        for (MemoryBlock block : currentProgram.getMemory().getBlocks()) {
            monitor.checkCancelled();
            if (!block.isInitialized() || block.isExecute()) continue;
            long size = block.getSize();
            if (size < ascii.length || size > Integer.MAX_VALUE) continue;
            byte[] bytes = new byte[(int) size];
            if (currentProgram.getMemory().getBytes(block.getStart(), bytes) != bytes.length) {
                throw new IllegalStateException("short initialized block read: " + block.getName());
            }
            scanBytes(block, bytes, ascii, false);
            scanBytes(block, bytes, utf16, true);
        }
    }

    private void scanBytes(MemoryBlock block, byte[] bytes, byte[] needle, boolean utf16)
        throws Exception {
        int stride = utf16 ? 2 : 1;
        for (int offset = 0; offset <= bytes.length - needle.length; offset += stride) {
            if ((offset & 0x3fffff) == 0) monitor.checkCancelled();
            boolean match = true;
            for (int index = 0; index < needle.length; index += stride) {
                int actual = bytes[offset + index] & 0xff;
                int expected = needle[index] & 0xff;
                if (Character.toLowerCase((char) actual) != Character.toLowerCase((char) expected)) {
                    match = false;
                    break;
                }
                if (utf16 && bytes[offset + index + 1] != 0) {
                    match = false;
                    break;
                }
            }
            if (!match) continue;
            Address address = block.getStart().add(offset);
            String key = (utf16 ? "U" : "A") + address;
            if (!seenRawMatches.add(key)) continue;
            println("RAW_GRAMMAR_MATCH\taddress=" + address
                + "\tencoding=" + (utf16 ? "UTF16LE" : "ASCII")
                + "\tblock=" + block.getName());
            rawMatches++;
        }
    }

    private static String sha256(Path path) throws Exception {
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        try (java.io.InputStream stream = Files.newInputStream(path)) {
            byte[] buffer = new byte[1024 * 1024];
            int read;
            while ((read = stream.read(buffer)) >= 0) {
                if (read > 0) digest.update(buffer, 0, read);
            }
        }
        StringBuilder out = new StringBuilder();
        for (byte value : digest.digest()) out.append(String.format("%02x", value & 0xff));
        return out.toString();
    }

    private static String escape(String value) {
        return value.replace("\\", "\\\\").replace("\r", "\\r")
            .replace("\n", "\\n").replace("\t", "\\t");
    }
}
