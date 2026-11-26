import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
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

public class InspectSortStringReferences extends GhidraScript {
    private static final long EXPECTED_BASE = 0x7100000000L;
    private static final String EXPECTED_NCA_ID = "2b7730a9e56498bbafac2002d4908c6b";
    private static final String EXPECTED_MAIN_SHA256 =
        "1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8";
    private static final String[] NEEDLES = {
        "sort_string", "initial_index", "initial_to_sort", "sort_table",
        "item_initial", "monsname_initial", "waza_initial", "monsname.dat"
    };
    private final Set<String> rawMatches = new HashSet<>();
    private final Set<String> decompiledFunctions = new HashSet<>();
    private int definedMatches;
    private int rawMatchCount;
    private int xrefs;
    private int decompiled;
    private int inspectedFunctions;
    private int temporaryFunctions;

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
        scanRawStrings();
        inspectFunction(0x71003740d0L, "sort-file request helper");
        inspectFunction(0x7100374530L, "sort resource state initializer");
        inspectFunction(0x7100023a20L, "resource object attachment helper");
        inspectFunction(0x71007774a0L, "item sort initializer caller");
        inspectFunction(0x7100b094e0L, "monsname sort initializer caller");
        inspectFunction(0x71007775b0L, "waza sort initializer caller");
        inspectFunction(0x71008f6450L, "monsname resource owner caller A");
        inspectFunction(0x7100b06d60L, "monsname resource owner caller B");
        inspectFunction(0x7100b09810L, "monsname sort state helper");
        inspectFunction(0x7100b09900L, "zukan_data owner resource initializer");
        inspectFunction(0x7100b31300L, "item sort state constructor");
        inspectFunction(0x7100b317c0L, "waza sort state constructor");
        inspectFunction(0x7100b06f10L, "monsname resource owner dispatch helper");
        inspectFunction(0x7100b09dc0L, "monsname list availability predicate");
        inspectFunction(0x7100b0b560L, "monsname sort resource owner factory");
        inspectFunction(0x7100176c50L, "monsname initial range helper A");
        inspectFunction(0x7100176c70L, "monsname initial range helper B");
        inspectFunction(0x7100377800L, "ushort resource accessor candidate");
        inspectFunction(0x7100377810L, "resource element count helper");
        inspectFunction(0x71003775e0L, "localized resource request helper");
        inspectFunction(0x7100b29b70L, "candidate shared resource field reader A");
        inspectFunction(0x7100b2acfcL, "candidate shared resource field reader B");
        inspectFunction(0x7100b36c70L, "candidate shared resource field reader C");
        inspectFunction(0x7100b36e80L, "candidate shared resource field reader D");
        inspectFunction(0x7100b0a150L, "monsname vtable method candidate 2");
        inspectFunction(0x7100b0a200L, "monsname vtable method candidate 3");
        inspectFunction(0x7100b0a2f0L, "monsname vtable method candidate 4");
        inspectFunction(0x7100b0a350L, "monsname vtable method candidate 5");
        inspectFunction(0x7100b0ac90L, "monsname vtable method candidate 6");
        inspectFunction(0x7100b0aca0L, "monsname vtable method candidate 7");
        inspectFunction(0x7100b0acb0L, "monsname vtable method candidate 8");
        inspectFunction(0x7100b0acc0L, "monsname vtable method candidate 9");
        inspectFunction(0x7100b0acd0L, "monsname vtable method candidate 10");
        inspectFunction(0x7100b0ae20L, "monsname vtable method candidate 11");
        inspectFunction(0x7100b0b530L, "monsname vtable method candidate 1");
        inspectFunction(0x7100b0b680L, "monsname vtable method candidate 14");
        inspectFunction(0x7100b0b690L, "monsname vtable method candidate 15");
        inspectFunction(0x7100b0a4b0L, "monsname query builder A");
        inspectFunction(0x7100b0a8f0L, "monsname query builder B");
        inspectPointerTable(0x71016093c8L, "monsname owner vtable", 0x10L);
        inspectPointerTable(0x7101609568L, "item sort resource vtable", 0x10L, 0x30L, 0x68L);
        inspectPointerTable(0x7101609570L, "waza sort resource vtable", 0x10L, 0x30L, 0x68L);
        inspectPointerTable(0x7101609330L, "monsname list owner vtable", 0x10L, 0xb0L);
        inspectCallWindow(0x7100776cecL, "item resource owner call site");
        inspectCallWindow(0x7100776cf4L, "waza resource owner call site");
        inspectCallWindow(0x7100b0a150L, "monsname vtable method candidate 2 body");
        inspectCallWindow(0x7100b0a200L, "monsname vtable method candidate 3 body");
        inspectCallWindow(0x7100b0a2f0L, "monsname vtable method candidate 4 body");
        inspectCallWindow(0x7100b0a350L, "monsname vtable method candidate 5 body");
        inspectCallWindow(0x7100b0acd0L, "monsname vtable method candidate 10 body");
        inspectCallWindow(0x7100b0ae20L, "monsname vtable method candidate 11 body");
        inspectIncomingCalls(0x7100b31400L, "item sort resource initializer");
        inspectIncomingCalls(0x7100b315e0L, "monsname sort resource initializer");
        inspectIncomingCalls(0x7100b318c0L, "waza sort resource initializer");
        inspectIncomingCalls(0x71007774a0L, "item sort resource owner");
        inspectIncomingCalls(0x7100b094e0L, "monsname sort resource owner");
        inspectIncomingCalls(0x71007775b0L, "waza sort resource owner");
        println("SUMMARY\tdefined_matches=" + definedMatches
            + "\traw_matches=" + rawMatchCount + "\tdirect_xrefs=" + xrefs
            + "\tdecompiled_functions=" + decompiled
            + "\texplicit_functions=" + inspectedFunctions
            + "\ttemporary_candidates=" + temporaryFunctions
            + "\tprogram=" + currentProgram.getName());
        if (!EXPECTED_MAIN_SHA256.equals(sha256(Path.of(executable.trim())))) {
            throw new IllegalStateException("source main hash changed during inspection");
        }
    }

    private void inspectFunction(long addressOffset, String role) throws Exception {
        ghidra.program.model.address.Address address =
            currentProgram.getImageBase().add(addressOffset - EXPECTED_BASE);
        Function function = currentProgram.getFunctionManager().getFunctionAt(address);
        if (function == null) {
            function = currentProgram.getFunctionManager().getFunctionContaining(address);
        }
        boolean temporary = false;
        if (function == null) {
            if (currentProgram.getListing().getInstructionAt(address) == null) {
                disassemble(address);
            }
            if (currentProgram.getListing().getInstructionAt(address) != null) {
                function = createFunction(address, null);
                temporary = function != null;
            }
            if (function == null) {
                println("HELPER_NOT_FOUND\trole=" + role + "\taddress=" + address);
                return;
            }
            temporaryFunctions++;
        }
        println("HELPER_FUNCTION\trole=" + role + "\trequested=" + address
            + "\tentry=" + function.getEntryPoint() + "\tname=" + function.getName()
            + "\ttemporary=" + temporary);
        ReferenceIterator references = currentProgram.getReferenceManager()
            .getReferencesTo(function.getEntryPoint());
        int incoming = 0;
        while (references.hasNext()) {
            monitor.checkCancelled();
            Reference reference = references.next();
            Function caller = currentProgram.getFunctionManager()
                .getFunctionContaining(reference.getFromAddress());
            println("HELPER_INCOMING\trole=" + role + "\tfrom=" + reference.getFromAddress()
                + "\ttype=" + reference.getReferenceType()
                + "\tcaller=" + (caller == null ? "<no-function>" : caller.getEntryPoint())
                + "\tname=" + (caller == null ? "<no-function>" : caller.getName()));
            incoming++;
        }
        println("HELPER_INCOMING_COUNT\trole=" + role + "\tcount=" + incoming);
        DecompInterface decompiler = new DecompInterface();
        decompiler.openProgram(currentProgram);
        decompile(decompiler, function);
        decompiler.dispose();
        inspectedFunctions++;
    }

    private void inspectIncomingCalls(long addressOffset, String role) throws Exception {
        ghidra.program.model.address.Address address =
            currentProgram.getImageBase().add(addressOffset - EXPECTED_BASE);
        Function function = currentProgram.getFunctionManager().getFunctionAt(address);
        if (function == null) {
            println("ENTRY_NOT_FOUND\trole=" + role + "\taddress=" + address);
            return;
        }
        println("ENTRY_FUNCTION\trole=" + role + "\tentry=" + address
            + "\tname=" + function.getName());
        ReferenceIterator references = currentProgram.getReferenceManager()
            .getReferencesTo(function.getEntryPoint());
        int incoming = 0;
        while (references.hasNext()) {
            monitor.checkCancelled();
            Reference reference = references.next();
            Function caller = currentProgram.getFunctionManager()
                .getFunctionContaining(reference.getFromAddress());
            println("ENTRY_INCOMING\trole=" + role + "\tfrom=" + reference.getFromAddress()
                + "\ttype=" + reference.getReferenceType()
                + "\tcaller=" + (caller == null ? "<no-function>" : caller.getEntryPoint())
                + "\tname=" + (caller == null ? "<no-function>" : caller.getName()));
            incoming++;
        }
        println("ENTRY_INCOMING_COUNT\trole=" + role + "\tcount=" + incoming);
    }

    private void inspectCallWindow(long addressOffset, String role) {
        ghidra.program.model.address.Address center =
            currentProgram.getImageBase().add(addressOffset - EXPECTED_BASE);
        println("CALL_WINDOW_BEGIN\trole=" + role + "\tcenter=" + center);
        for (long delta = -0x30; delta <= 0x30; delta += 4) {
            ghidra.program.model.address.Address address = center.add(delta);
            ghidra.program.model.listing.Instruction instruction =
                currentProgram.getListing().getInstructionAt(address);
            if (instruction == null) continue;
            Function caller = currentProgram.getFunctionManager()
                .getFunctionContaining(address);
            println("CALL_WINDOW_INSN\taddress=" + address
                + "\tfunction=" + (caller == null ? "<no-function>" : caller.getEntryPoint())
                + "\ttext=" + escape(instruction.toString()));
        }
        println("CALL_WINDOW_END\trole=" + role);
    }

    private void inspectPointerTable(long globalOffset, String role, long... tableOffsets)
        throws Exception {
        ghidra.program.model.address.Address global =
            currentProgram.getImageBase().add(globalOffset - EXPECTED_BASE);
        long pointer = currentProgram.getMemory().getLong(global);
        println("POINTER_TABLE_GLOBAL\trole=" + role + "\tglobal=" + global
            + "\tvalue=0x" + Long.toHexString(pointer));
        ghidra.program.model.address.Address base =
            currentProgram.getAddressFactory().getDefaultAddressSpace().getAddress(pointer);
        for (long tableOffset : tableOffsets) {
            ghidra.program.model.address.Address table = base.add(tableOffset);
            println("POINTER_TABLE_BEGIN\trole=" + role + "\ttable=" + table
                + "\tbase_offset=0x" + Long.toHexString(tableOffset));
            for (int index = 0; index < 16; index++) {
                ghidra.program.model.address.Address slot = table.add(index * 8L);
                long value = currentProgram.getMemory().getLong(slot);
                ghidra.program.model.address.Address target =
                    currentProgram.getAddressFactory().getDefaultAddressSpace().getAddress(value);
                Function function = currentProgram.getFunctionManager().getFunctionAt(target);
                println("POINTER_TABLE_SLOT\tindex=" + index + "\taddress=" + slot
                    + "\tvalue=" + target + "\tfunction="
                    + (function == null ? "<no-function>" : function.getName()));
            }
            println("POINTER_TABLE_END\trole=" + role);
        }
    }

    private void scanDefinedStrings() throws Exception {
        DataIterator iterator = currentProgram.getListing().getDefinedData(true);
        DecompInterface decompiler = new DecompInterface();
        decompiler.openProgram(currentProgram);
        while (iterator.hasNext()) {
            monitor.checkCancelled();
            Data data = iterator.next();
            Object value = data.getValue();
            if (!(value instanceof String)) continue;
            String text = (String) value;
            String lower = text.toLowerCase(Locale.ROOT);
            if (!containsNeedle(lower)) continue;
            definedMatches++;
            println("DEFINED_STRING\taddress=" + data.getAddress()
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
                    && decompiledFunctions.size() <= 16) {
                    decompile(decompiler, caller);
                }
            }
        }
        decompiler.dispose();
    }

    private void scanRawStrings() throws Exception {
        for (MemoryBlock block : currentProgram.getMemory().getBlocks()) {
            monitor.checkCancelled();
            if (!block.isInitialized() || block.isExecute()) continue;
            long size = block.getSize();
            if (size < 8 || size > Integer.MAX_VALUE) continue;
            byte[] bytes = new byte[(int) size];
            if (currentProgram.getMemory().getBytes(block.getStart(), bytes) != bytes.length) {
                throw new IllegalStateException("short initialized block read: " + block.getName());
            }
            for (String needle : NEEDLES) {
                scanNeedle(block, bytes, needle, false);
                scanNeedle(block, bytes, needle, true);
            }
        }
    }

    private void scanNeedle(MemoryBlock block, byte[] bytes, String needle, boolean utf16)
        throws Exception {
        byte[] target = needle.toLowerCase(Locale.ROOT).getBytes(
            utf16 ? java.nio.charset.StandardCharsets.UTF_16LE
                : java.nio.charset.StandardCharsets.US_ASCII);
        int stride = utf16 ? 2 : 1;
        for (int offset = 0; offset <= bytes.length - target.length; offset += stride) {
            if ((offset & 0x3fffff) == 0) monitor.checkCancelled();
            boolean match = true;
            for (int i = 0; i < target.length; i += stride) {
                int actual = bytes[offset + i] & 0xff;
                int expected = target[i] & 0xff;
                if (Character.toLowerCase((char) actual)
                    != Character.toLowerCase((char) expected)) {
                    match = false;
                    break;
                }
                if (utf16 && bytes[offset + i + 1] != 0) {
                    match = false;
                    break;
                }
            }
            if (!match) continue;
            String key = (utf16 ? "U" : "A") + block.getStart().add(offset) + ":" + needle;
            if (!rawMatches.add(key)) continue;
            println("RAW_STRING\taddress=" + block.getStart().add(offset)
                + "\tneedle=" + needle + "\tencoding="
                + (utf16 ? "UTF16LE" : "ASCII") + "\tblock=" + block.getName());
            rawMatchCount++;
        }
    }

    private boolean containsNeedle(String text) {
        for (String needle : NEEDLES) {
            if (text.contains(needle)) return true;
        }
        return false;
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
