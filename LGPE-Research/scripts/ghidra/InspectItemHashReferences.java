import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Data;
import ghidra.program.model.listing.DataIterator;
import ghidra.program.model.listing.Function;
import ghidra.program.model.mem.MemoryBlock;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;
import java.io.InputStream;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

public class InspectItemHashReferences extends GhidraScript {
    private static final long EXPECTED_BASE = 0x7100000000L;
    private static final String EXPECTED_NCA_ID = "2b7730a9e56498bbafac2002d4908c6b";
    private static final String EXPECTED_MAIN_SHA256 =
        "1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8";
    private static final String EXPECTED_TABLE_SHA256 =
        "a9050fef634aa1bc2dfe34cd48781bc6357498f05133e2ac63a463be2b5f9fc0";
    private static final int EXPECTED_TABLE_BYTES = 16740;
    private static final int CANDIDATE_STRIDE = 0x10;
    private static final int MAX_STRING_OUTPUT = 200;

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
        Path ncaRoot = Path.of(executable.trim()).getParent().getParent();
        Path tablePath = ncaRoot.resolve("1/bin/pokelib/item/item_hash_to_index.dat");
        byte[] table = Files.readAllBytes(tablePath);
        String tableHash = sha256(table);
        if (table.length != EXPECTED_TABLE_BYTES || !EXPECTED_TABLE_SHA256.equals(tableHash)) {
            throw new IllegalStateException("item_hash_to_index source identity mismatch: bytes="
                + table.length + " sha256=" + tableHash);
        }
        int candidateCount = ByteBuffer.wrap(table, 0, 4)
            .order(ByteOrder.LITTLE_ENDIAN).getInt();
        if (candidateCount < 0 || 4L + (long) candidateCount * CANDIDATE_STRIDE != table.length) {
            throw new IllegalStateException("pinned cross-version candidate stride does not fit source");
        }
        Map<Long, List<Integer>> rowsByOpaqueWord = new HashMap<>();
        for (int row = 0; row < candidateCount; row++) {
            monitor.checkCancelled();
            int offset = 4 + row * CANDIDATE_STRIDE;
            long word = ByteBuffer.wrap(table, offset, 8)
                .order(ByteOrder.LITTLE_ENDIAN).getLong();
            if (word != 0) {
                rowsByOpaqueWord.computeIfAbsent(word, ignored -> new ArrayList<>()).add(row);
            }
        }
        println("PROGRAM\tversion=Pokemon Let's Go Pikachu 1.0.2\tbase="
            + currentProgram.getImageBase() + "\tmain_sha256=" + mainHash);
        println("SOURCE\tpath=" + tablePath + "\tbytes=" + table.length
            + "\tsha256=" + tableHash + "\tcandidate_rows=" + candidateCount
            + "\tcandidate_stride=0x10\tfield_name=opaque_u64_at_record_offset_0");

        inspectStrings();
        inspectFunctionChain(0x1d4510L, "ITEM_HASH_PATH_XREF_FUNCTION");
        inspectFunctionChain(0x1d3730L, "ITEM_DIRECTORY_PATH_XREF_FUNCTION");
        inspectFunctionChain(0x1d35e0L, "ITEM_RESOURCE_INIT_CALLER");
        inspectFunctionChain(0x5bd0L, "ITEM_RESOURCE_STARTUP_INIT");
        int rawMatches = scanInitializedMemory(rowsByOpaqueWord);
        println("ITEM_HASH_REFERENCE_SUMMARY\tunique_nonzero_candidate_words="
            + rowsByOpaqueWord.size()
            + "\traw_memory_matches=" + rawMatches
            + "\tinterpretation=opaque-byte-matches-only");
    }

    private void inspectStrings() throws Exception {
        DataIterator iterator = currentProgram.getListing().getDefinedData(true);
        int matched = 0;
        int printed = 0;
        int xrefCount = 0;
        while (iterator.hasNext()) {
            monitor.checkCancelled();
            Data data = iterator.next();
            Object value = data.getValue();
            if (!(value instanceof String)) continue;
            String text = (String) value;
            String lower = text.toLowerCase(Locale.ROOT);
            if (!lower.contains("item") && !lower.contains("hash")) continue;
            matched++;
            if (printed >= MAX_STRING_OUTPUT) continue;
            printed++;
            println("ITEM_OR_HASH_STRING\taddress=" + data.getAddress()
                + "\ttext=" + escape(text));
            ReferenceIterator refs = currentProgram.getReferenceManager()
                .getReferencesTo(data.getAddress());
            while (refs.hasNext()) {
                monitor.checkCancelled();
                Reference ref = refs.next();
                Function caller = currentProgram.getFunctionManager()
                    .getFunctionContaining(ref.getFromAddress());
                println("STRING_XREF\tfrom=" + ref.getFromAddress()
                    + "\tcaller=" + (caller == null ? "<no-function>" : caller.getEntryPoint())
                    + "\tname=" + (caller == null ? "<no-function>" : caller.getName()));
                xrefCount++;
            }
        }
        println("STRING_SCAN_SUMMARY\tmatched_item_or_hash_strings=" + matched
            + "\tprinted=" + printed + "\txrefs=" + xrefCount);
    }

    private void inspectFunctionChain(long relativeAddress, String label) throws Exception {
        Address address = currentProgram.getImageBase().add(relativeAddress);
        Function function = currentProgram.getFunctionManager().getFunctionAt(address);
        if (function == null) {
            function = currentProgram.getFunctionManager().getFunctionContaining(address);
        }
        println("FUNCTION_TARGET\t" + label + "\taddress=" + address
            + "\tentry=" + (function == null ? "<not-found>" : function.getEntryPoint()));
        if (function == null) return;
        decompileFunction(label, function);

        ReferenceIterator references = currentProgram.getReferenceManager()
            .getReferencesTo(function.getEntryPoint());
        int count = 0;
        Map<Long, Function> callers = new HashMap<>();
        while (references.hasNext()) {
            monitor.checkCancelled();
            Reference reference = references.next();
            Function caller = currentProgram.getFunctionManager()
                .getFunctionContaining(reference.getFromAddress());
            println("FUNCTION_INCOMING\t" + label + "\tfrom=" + reference.getFromAddress()
                + "\ttype=" + reference.getReferenceType()
                + "\tcaller=" + (caller == null ? "<no-function>" : caller.getEntryPoint()));
            count++;
            if (caller != null) callers.put(caller.getEntryPoint().getOffset(), caller);
        }
        println("FUNCTION_INCOMING_COUNT\t" + label + "\tcount=" + count);
        int printed = 0;
        for (Function caller : callers.values()) {
            if (printed++ >= 20) {
                println("FUNCTION_CALLER_LIMIT\t" + label + "\tlimit=20");
                break;
            }
            decompileFunction(label + "_CALLER_" + caller.getEntryPoint(), caller);
        }
    }

    private void decompileFunction(String label, Function function) throws Exception {
        DecompInterface decompiler = new DecompInterface();
        decompiler.openProgram(currentProgram);
        DecompileResults result = decompiler.decompileFunction(function, 90, monitor);
        if (!result.decompileCompleted() || result.getDecompiledFunction() == null) {
            println("DECOMPILE_FAILED\t" + label + "\t" + result.getErrorMessage());
            decompiler.dispose();
            return;
        }
        String[] lines = result.getDecompiledFunction().getC().split("\\R", -1);
        println("DECOMPILED_BEGIN\t" + label + "\tentry=" + function.getEntryPoint()
            + "\tlines=" + lines.length);
        for (int index = 0; index < lines.length; index++) {
            println("CODE\t" + label + "\t" + index + "\t"
                + lines[index].replace("\t", "\\t"));
        }
        println("DECOMPILED_END\t" + label);
        decompiler.dispose();
    }

    private int scanInitializedMemory(Map<Long, List<Integer>> candidateWords) throws Exception {
        int matches = 0;
        for (MemoryBlock block : currentProgram.getMemory().getBlocks()) {
            monitor.checkCancelled();
            if (!block.isInitialized()) continue;
            long size = block.getSize();
            if (size < 8 || size > Integer.MAX_VALUE) {
                println("MEMORY_BLOCK_SKIPPED\tname=" + block.getName() + "\tbytes=" + size);
                continue;
            }
            byte[] bytes = new byte[(int) size];
            int read = currentProgram.getMemory().getBytes(block.getStart(), bytes);
            if (read != bytes.length) {
                throw new IllegalStateException("short initialized block read: " + block.getName());
            }
            for (int offset = 0; offset + 8 <= bytes.length; offset++) {
                if ((offset & 0x3fffff) == 0) monitor.checkCancelled();
                long word = readLongLe(bytes, offset);
                List<Integer> rows = candidateWords.get(word);
                if (rows == null) continue;
                matches += rows.size();
                for (int row : rows) {
                    println("OPAQUE_WORD_BYTE_MATCH\tblock=" + block.getName()
                        + "\taddress=" + block.getStart().add(offset)
                        + "\ttable_row=" + row
                        + "\tmain_byte_match_only=true");
                }
            }
            println("MEMORY_BLOCK_SCANNED\tname=" + block.getName()
                + "\tbytes=" + size + "\tstart=" + block.getStart());
        }
        return matches;
    }

    private String sha256(byte[] bytes) throws Exception {
        return hex(MessageDigest.getInstance("SHA-256").digest(bytes));
    }

    private long readLongLe(byte[] bytes, int offset) {
        return ((long) bytes[offset] & 0xffL)
            | (((long) bytes[offset + 1] & 0xffL) << 8)
            | (((long) bytes[offset + 2] & 0xffL) << 16)
            | (((long) bytes[offset + 3] & 0xffL) << 24)
            | (((long) bytes[offset + 4] & 0xffL) << 32)
            | (((long) bytes[offset + 5] & 0xffL) << 40)
            | (((long) bytes[offset + 6] & 0xffL) << 48)
            | (((long) bytes[offset + 7] & 0xffL) << 56);
    }

    private String sha256(Path path) throws Exception {
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        try (InputStream stream = Files.newInputStream(path)) {
            byte[] buffer = new byte[65536];
            int count;
            while ((count = stream.read(buffer)) >= 0) digest.update(buffer, 0, count);
        }
        return hex(digest.digest());
    }

    private String hex(byte[] bytes) {
        StringBuilder result = new StringBuilder(bytes.length * 2);
        for (byte value : bytes) result.append(String.format(Locale.ROOT, "%02x", value & 0xff));
        return result.toString();
    }

    private String escape(String value) {
        return value.replace("\\", "\\\\").replace("\r", "\\r")
            .replace("\n", "\\n").replace("\t", "\\t");
    }
}
