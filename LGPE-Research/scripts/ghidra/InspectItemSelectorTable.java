import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Data;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.mem.MemoryBlock;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;

import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.program.model.listing.InstructionIterator;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.util.HashSet;
import java.util.Locale;
import java.util.Set;

public class InspectItemSelectorTable extends GhidraScript {
    private static final long EXPECTED_BASE = 0x7100000000L;
    private static final String EXPECTED_NCA_ID = "2b7730a9e56498bbafac2002d4908c6b";
    private static final String EXPECTED_MAIN_SHA256 =
        "1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8";
    private static final long MAP_POINTER_SLOT = 0x163ea48L;
    private static final int ITEM_COUNT_BOUND = 0x422;
    private static final int TARGET_ITEM_INDEX = 0x36a;

    @Override
    public void run() throws Exception {
        String executable = currentProgram.getExecutablePath();
        String normalized = executable == null ? "" : executable.trim().replace('\\', '/');
        if (currentProgram.getImageBase().getOffset() != EXPECTED_BASE
            || !normalized.toLowerCase(Locale.ROOT).contains(EXPECTED_NCA_ID)
            || !normalized.toLowerCase(Locale.ROOT).endsWith("/0/main")) {
            throw new IllegalStateException("not the recorded LGPE 1.0.2 main program");
        }
        String mainHash = sha256(executable.trim());
        if (!EXPECTED_MAIN_SHA256.equals(mainHash)) {
            throw new IllegalStateException("source main SHA-256 mismatch: " + mainHash);
        }
        println("PROGRAM\tbase=" + currentProgram.getImageBase() + "\tsha256=" + mainHash);

        Address slot = currentProgram.getImageBase().add(MAP_POINTER_SLOT);
        Data slotData = currentProgram.getListing().getDefinedDataAt(slot);
        MemoryBlock slotBlock = currentProgram.getMemory().getBlock(slot);
        if (slotBlock == null || !slotBlock.isInitialized()) {
            println("ITEM_SELECTOR_MAP_GLOBAL_UNAVAILABLE\taddress=" + slot
                + "\tblock=" + (slotBlock == null ? "<none>" : slotBlock.getName())
                + "\tinitialized=" + (slotBlock != null && slotBlock.isInitialized()));
            for (MemoryBlock mapped : currentProgram.getMemory().getBlocks()) {
                println("MEMORY_BLOCK\t" + mapped.getName() + "\t"
                    + mapped.getStart() + ".." + mapped.getEnd()
                    + "\tinitialized=" + mapped.isInitialized());
            }
            ReferenceIterator slotReferences = currentProgram.getReferenceManager().getReferencesTo(slot);
            Set<Long> decompiled = new HashSet<>();
            int slotReferenceCount = 0;
            while (slotReferences.hasNext()) {
                monitor.checkCancelled();
                Reference reference = slotReferences.next();
                slotReferenceCount++;
                Address from = reference.getFromAddress();
                Function caller = currentProgram.getFunctionManager().getFunctionContaining(from);
                Instruction instruction = currentProgram.getListing().getInstructionAt(from);
                println("MAP_SLOT_XREF\tfrom=" + from + "\ttype=" + reference.getReferenceType()
                    + "\tcaller=" + (caller == null ? "<no-function>" : caller.getEntryPoint())
                    + "\tinstruction=" + (instruction == null ? "<none>" : instruction.toString()));
                if (caller != null && decompiled.add(caller.getEntryPoint().getOffset())) {
                    decompileFunction("MAP_SLOT_CALLER_" + caller.getEntryPoint(), caller);
                }
            }
            println("MAP_SLOT_XREF_COUNT\t" + slotReferenceCount);
            traceFunction(0x71cec0L, "MAP_TABLE_REPLACEMENT");
            traceFunction(0x00adc70L, "RESOURCE_REQUEST_HELPER");
            traceFunction(0x73b320L, "RESOURCE_CONTEXT_HELPER");
            traceFunction(0x73b950L, "RESOURCE_KEY_BUILDER");
            traceFunction(0x71d800L, "NEARBY_DATA_LOADER");
            printInstructions(0x71d780L, 0x71d7e0L, "MAP_SLOT_NEARBY_INIT");
            printInstructions(0x1d42f0L, 0x1d43d0L, "TABLE_INITIALIZER_CALLSITE");
            println("SUMMARY\tprogram=" + normalized + "\tmap_slot=" + slot
                + "\tstatus=slot-unmapped");
            return;
        }
        long tablePointer = currentProgram.getMemory().getLong(slot);
        Address tableAddress = toAddr(tablePointer);
        MemoryBlock block = currentProgram.getMemory().getBlock(tableAddress);
        println("ITEM_SELECTOR_MAP_GLOBAL\taddress=" + slot
            + "\ttype=" + (slotData == null ? "<undefined>" : slotData.getDataType().getName())
            + "\tvalue=" + tableAddress
            + "\tmapped=" + currentProgram.getMemory().contains(tableAddress)
            + "\tblock=" + (block == null ? "<none>" : block.getName())
            + "\tinitialized=" + (block != null && block.isInitialized()));

        if (block == null || !block.isInitialized()
            || !block.contains(tableAddress.add(ITEM_COUNT_BOUND - 1))) {
            throw new IllegalStateException("item selector map is not fully present in initialized memory");
        }
        byte[] raw = new byte[ITEM_COUNT_BOUND];
        int read = currentProgram.getMemory().getBytes(tableAddress, raw);
        if (read != raw.length) {
            throw new IllegalStateException("short item selector map read: " + read);
        }

        int[] counts = new int[8];
        StringBuilder entries = new StringBuilder();
        for (int index = 0; index < raw.length; index++) {
            int value = raw[index] & 0xff;
            int selector = value & 7;
            counts[selector]++;
            entries.append("    {\"item_index\": ").append(index)
                .append(", \"raw_byte\": ").append(value)
                .append(", \"selector_code\": ").append(selector).append("},\n");
        }
        String tableHash = sha256(raw);
        int targetRaw = raw[TARGET_ITEM_INDEX] & 0xff;
        println("ITEM_SELECTOR_MAP\taddress=" + tableAddress
            + "\tbytes=" + raw.length + "\tsha256=" + tableHash
            + "\ttarget_index=" + TARGET_ITEM_INDEX
            + "\ttarget_raw=0x" + String.format(Locale.ROOT, "%02x", targetRaw)
            + "\ttarget_selector=" + (targetRaw & 7));
        for (int code = 0; code < counts.length; code++) {
            println("ITEM_SELECTOR_CODE_COUNT\tcode=" + code + "\tcount=" + counts[code]);
        }

        Function accessor = currentProgram.getFunctionManager()
            .getFunctionAt(currentProgram.getImageBase().add(0x71d1b0L));
        println("ACCESSOR_FUNCTION\t" + (accessor == null ? "<not-found>" : accessor.getEntryPoint()));
        if (accessor != null) {
            ReferenceIterator refs = currentProgram.getReferenceManager()
                .getReferencesTo(accessor.getEntryPoint());
            int count = 0;
            while (refs.hasNext()) {
                monitor.checkCancelled();
                Reference reference = refs.next();
                count++;
                Function caller = currentProgram.getFunctionManager()
                    .getFunctionContaining(reference.getFromAddress());
                println("ACCESSOR_XREF\tfrom=" + reference.getFromAddress()
                    + "\tcaller=" + (caller == null ? "<no-function>" : caller.getEntryPoint()));
            }
            println("ACCESSOR_XREF_COUNT\t" + count);
        }

        String json = "{\n"
            + "  \"schema\": \"lgpe-main-item-selector-map-v1\",\n"
            + "  \"game_version\": \"Pokemon Let's Go Pikachu 1.0.2\",\n"
            + "  \"main_sha256\": \"" + mainHash + "\",\n"
            + "  \"map_pointer_slot\": \"" + slot + "\",\n"
            + "  \"map_address\": \"" + tableAddress + "\",\n"
            + "  \"map_bytes\": " + raw.length + ",\n"
            + "  \"map_sha256\": \"" + tableHash + "\",\n"
            + "  \"target_item_index\": " + TARGET_ITEM_INDEX + ",\n"
            + "  \"target_raw_byte\": " + targetRaw + ",\n"
            + "  \"target_selector_code\": " + (targetRaw & 7) + ",\n"
            + "  \"selector_code_counts\": [" + join(counts) + "],\n"
            + "  \"entries\": [\n" + entries + "  ]\n"
            + "}\n";
        Path output = Path.of("manifests/research/lgpe102-item-selector-map.json");
        Files.createDirectories(output.getParent());
        Files.writeString(output, json);
        println("STRUCTURED_OUTPUT\t" + output.toAbsolutePath().normalize());
        println("SUMMARY\tprogram=" + normalized + "\tmap=" + tableAddress
            + "\tentries=" + raw.length);
    }

    private String join(int[] values) {
        StringBuilder result = new StringBuilder();
        for (int index = 0; index < values.length; index++) {
            if (index != 0) result.append(", ");
            result.append(values[index]);
        }
        return result.toString();
    }

    private String sha256(byte[] bytes) throws Exception {
        return hex(MessageDigest.getInstance("SHA-256").digest(bytes));
    }

    private String sha256(String path) throws Exception {
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        try (InputStream stream = Files.newInputStream(Path.of(path))) {
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
            println("CODE\t" + label + "\t" + index + "\t" + lines[index].replace("\t", "\\t"));
        }
        println("DECOMPILED_END\t" + label);
        decompiler.dispose();
    }

    private void traceFunction(long relativeAddress, String label) throws Exception {
        Address address = currentProgram.getImageBase().add(relativeAddress);
        Function function = currentProgram.getFunctionManager().getFunctionAt(address);
        println("TRACE_FUNCTION\t" + label + "\taddress=" + address
            + "\tfound=" + (function != null));
        if (function == null) return;
        ReferenceIterator references = currentProgram.getReferenceManager()
            .getReferencesTo(function.getEntryPoint());
        int count = 0;
        while (references.hasNext()) {
            monitor.checkCancelled();
            Reference reference = references.next();
            Function caller = currentProgram.getFunctionManager()
                .getFunctionContaining(reference.getFromAddress());
            Instruction instruction = currentProgram.getListing()
                .getInstructionAt(reference.getFromAddress());
            println("TRACE_FUNCTION_XREF\t" + label + "\tfrom=" + reference.getFromAddress()
                + "\tcaller=" + (caller == null ? "<no-function>" : caller.getEntryPoint())
                + "\tinstruction=" + (instruction == null ? "<none>" : instruction.toString()));
            count++;
        }
        println("TRACE_FUNCTION_XREF_COUNT\t" + label + "\t" + count);
        if (label.equals("RESOURCE_REQUEST_HELPER")
            || label.equals("RESOURCE_CONTEXT_HELPER")
            || label.equals("RESOURCE_KEY_BUILDER")
            || label.equals("NEARBY_DATA_LOADER")) {
            decompileFunction(label, function);
        }
    }

    private void printInstructions(long startOffset, long endOffset, String label) throws Exception {
        Address start = currentProgram.getImageBase().add(startOffset);
        Address end = currentProgram.getImageBase().add(endOffset);
        InstructionIterator instructions = currentProgram.getListing().getInstructions(start, true);
        while (instructions.hasNext()) {
            monitor.checkCancelled();
            Instruction instruction = instructions.next();
            if (instruction.getAddress().compareTo(end) >= 0) break;
            println("INSTRUCTION\t" + label + "\t" + instruction.getAddress()
                + "\t" + instruction.toString());
        }
    }
}
