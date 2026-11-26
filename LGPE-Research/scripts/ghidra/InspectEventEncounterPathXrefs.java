import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Data;
import ghidra.program.model.listing.DataIterator;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import ghidra.program.model.listing.Listing;
import ghidra.program.model.mem.MemoryBlock;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;

import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashSet;
import java.util.Locale;
import java.util.Set;
import java.util.TreeMap;

public class InspectEventEncounterPathXrefs extends GhidraScript {
    private static final String EXPECTED_MAIN_SHA256 =
        "1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8";
    private static final long EXPECTED_BASE = 0x7100000000L;
    private static final String EXPECTED_NCA_ID = "2b7730a9e56498bbafac2002d4908c6b";

    @Override
    public void run() throws Exception {
        String executable = currentProgram.getExecutablePath();
        String normalized = executable == null ? "" : executable.trim().replace('\\', '/');
        if (currentProgram.getImageBase().getOffset() != EXPECTED_BASE
            || !normalized.toLowerCase(Locale.ROOT).contains(EXPECTED_NCA_ID)
            || !normalized.toLowerCase(Locale.ROOT).endsWith("/0/main")) {
            throw new IllegalStateException("not the recorded LGPE 1.0.2 main program");
        }
        String actualHash = sha256(executable.trim());
        if (!EXPECTED_MAIN_SHA256.equals(actualHash)) {
            throw new IllegalStateException("source main SHA-256 mismatch: " + actualHash);
        }

        int definedStrings = 0;
        int matchedStrings = 0;
        int xrefs = 0;
        DataIterator iterator = currentProgram.getListing().getDefinedData(true);
        while (iterator.hasNext()) {
            Data data = iterator.next();
            Object value = data.getValue();
            if (!(value instanceof String)) {
                continue;
            }
            definedStrings++;
            String text = (String) value;
            String lower = text.toLowerCase(Locale.ROOT);
            if (!lower.contains("event_encount") && !lower.contains("script_event_data")) {
                continue;
            }
            matchedStrings++;
            println("STRING\t" + data.getAddress() + "\t" + escape(text));
            ReferenceIterator references = currentProgram.getReferenceManager()
                .getReferencesTo(data.getAddress());
            while (references.hasNext()) {
                Reference reference = references.next();
                Function caller = currentProgram.getFunctionManager()
                    .getFunctionContaining(reference.getFromAddress());
                println("XREF\t" + reference.getFromAddress() + "\t" + reference.getReferenceType()
                    + "\tcaller=" + (caller == null ? "<no-function>" : caller.getEntryPoint())
                    + "\tname=" + (caller == null ? "<no-function>" : caller.getName()));
                xrefs++;
                if (lower.contains("event_encount.bin") && caller != null) {
                    inspectFunction(caller);
                }
            }
        }
        inspectTarget(0x71002ba980L);
        inspectTarget(0x71002baba0L);
        inspectTarget(0x71002baa10L);
        inspectTarget(0x71002f5f60L);
        inspectTarget(0x71001ca020L);
        inspectTarget(0x71001ca030L);
        inspectTarget(0x710000e420L);
        inspectDataCell(0x71015278b8L);
        inspectBodyOnly(0x71000001c0L);
        inspectDataCell(0x7101547368L);
        inspectPointerRun(0x7101527898L, 8);
        inspectPointerRun(0x7101547348L, 8);
        inspectBodyOnly(0x710028f2e0L);
        inspectBodyOnly(0x710028f2f0L);
        inspectBodyOnly(0x710028f6c0L);
        inspectCodeAddress(0x7100002a90L);
        inspectCodeAddress(0x7100011160L);
        inspectCodeAddress(0x710028f2e0L);
        inspectCodeAddress(0x710028f2f0L);
        inspectCodeAddress(0x710028f300L);
        inspectCodeAddress(0x710028f6c0L);
        inspectDataCell(0x71015a8a38L);
        inspectCodeAddress(0x710024f480L);
        inspectCodeAddress(0x710024f4d8L);
        inspectCodeAddress(0x710024f528L);
        inspectCodeAddress(0x710024f578L);
        inspectCodeAddress(0x710024f5c8L);
        inspectCodeAddress(0x710024f618L);
        inspectBodyOnly(0x710000b660L);
        inspectTarget(0x710028f430L);
        println("SUMMARY\tmain_sha256=" + actualHash + "\tdefined_strings=" + definedStrings
            + "\tmatched_strings=" + matchedStrings + "\txrefs=" + xrefs
            + "\tprogram=" + currentProgram.getName());
    }

    private void inspectFunction(Function function) throws Exception {
        println("FUNCTION\t" + function.getEntryPoint() + "\t" + function.getName()
            + "\tbytes=" + function.getBody().getNumAddresses());
        ReferenceIterator incoming = currentProgram.getReferenceManager()
            .getReferencesTo(function.getEntryPoint());
        while (incoming.hasNext()) {
            Reference reference = incoming.next();
            Function caller = currentProgram.getFunctionManager()
                .getFunctionContaining(reference.getFromAddress());
            println("INCOMING\t" + reference.getFromAddress() + "\t" + reference.getReferenceType()
                + "\tcaller=" + (caller == null ? "<no-function>" : caller.getEntryPoint()));
            inspectCallsite(reference.getFromAddress());
            if (caller != null) inspectFunction(caller);
        }

        InstructionIterator instructions = currentProgram.getListing()
            .getInstructions(function.getBody(), true);
        while (instructions.hasNext()) {
            Instruction instruction = instructions.next();
            for (Reference reference : instruction.getReferencesFrom()) {
                if (reference.getReferenceType().isCall()) {
                    Function callee = currentProgram.getFunctionManager()
                        .getFunctionContaining(reference.getToAddress());
                    println("CALL\t" + instruction.getAddress() + "\t" + reference.getToAddress()
                        + "\tcallee=" + (callee == null ? "<no-function>" : callee.getEntryPoint()));
                }
            }
        }

        DecompInterface decompiler = new DecompInterface();
        decompiler.openProgram(currentProgram);
        DecompileResults result = decompiler.decompileFunction(function, 120, monitor);
        if (!result.decompileCompleted() || result.getDecompiledFunction() == null) {
            println("DECOMPILE_FAILED\t" + result.getErrorMessage());
        } else {
            println("DECOMPILED_BEGIN\t" + function.getEntryPoint());
            println(result.getDecompiledFunction().getC());
            println("DECOMPILED_END\t" + function.getEntryPoint());
        }
        decompiler.dispose();
    }

    private void inspectTarget(long address) throws Exception {
        Address target = toAddr(address);
        Function function = currentProgram.getFunctionManager().getFunctionAt(target);
        if (function == null) {
            function = currentProgram.getFunctionManager().getFunctionContaining(target);
        }
        if (function == null) {
            println("TARGET_FUNCTION_MISSING\t" + target);
            return;
        }
        println("TARGET\t" + target + "\tfunction=" + function.getEntryPoint());
        inspectFunction(function);
    }

    private void inspectBodyOnly(long address) throws Exception {
        Address target = toAddr(address);
        Function function = currentProgram.getFunctionManager().getFunctionAt(target);
        if (function == null) function = currentProgram.getFunctionManager().getFunctionContaining(target);
        if (function == null) {
            println("BODY_ONLY_FUNCTION_MISSING\t" + target);
            return;
        }
        println("BODY_ONLY\t" + target + "\tfunction=" + function.getEntryPoint()
            + "\tname=" + function.getName() + "\tbytes=" + function.getBody().getNumAddresses());
        DecompInterface decompiler = new DecompInterface();
        decompiler.openProgram(currentProgram);
        DecompileResults result = decompiler.decompileFunction(function, 120, monitor);
        if (!result.decompileCompleted() || result.getDecompiledFunction() == null) {
            println("BODY_ONLY_DECOMPILE_FAILED\t" + result.getErrorMessage());
        } else {
            println("BODY_ONLY_DECOMPILED_BEGIN\t" + function.getEntryPoint());
            println(result.getDecompiledFunction().getC());
            println("BODY_ONLY_DECOMPILED_END\t" + function.getEntryPoint());
        }
        decompiler.dispose();
    }

    private void inspectPointerRun(long rawStart, int count) {
        for (int index = 0; index < count; index++) {
            Address cell = toAddr(rawStart + (long) index * 8L);
            Data data = currentProgram.getListing().getDataAt(cell);
            if (data == null) data = currentProgram.getListing().getDefinedDataContaining(cell);
            println("POINTER_RUN_CELL\t" + cell + "\tdata="
                + (data == null ? "<undefined>" : data.getDataType()) + "\tvalue="
                + (data == null ? "<undefined>" : data.getValue()));
            Reference[] outgoing = currentProgram.getReferenceManager().getReferencesFrom(cell);
            for (Reference reference : outgoing) {
                println("POINTER_RUN_OUTGOING\t" + cell + "\t" + reference.getReferenceType()
                    + "\tto=" + reference.getToAddress());
            }
            ReferenceIterator incoming = currentProgram.getReferenceManager().getReferencesTo(cell);
            while (incoming.hasNext()) {
                Reference reference = incoming.next();
                Function caller = currentProgram.getFunctionManager()
                    .getFunctionContaining(reference.getFromAddress());
                println("POINTER_RUN_INCOMING\t" + cell + "\tfrom=" + reference.getFromAddress()
                    + "\t" + reference.getReferenceType() + "\towner="
                    + (caller == null ? "<no-function>" : caller.getEntryPoint()));
            }
        }
    }

    private void inspectCodeAddress(long rawAddress) {
        Address address = toAddr(rawAddress);
        Function exactFunction = currentProgram.getFunctionManager().getFunctionAt(address);
        Function containingFunction = currentProgram.getFunctionManager().getFunctionContaining(address);
        Instruction center = currentProgram.getListing().getInstructionAt(address);
        println("CODE_FUNCTION\t" + address + "\texact="
            + (exactFunction == null ? "<no-function>" : exactFunction.getEntryPoint() + ":" + exactFunction.getName())
            + "\tcontaining="
            + (containingFunction == null ? "<no-function>"
                : containingFunction.getEntryPoint() + ":" + containingFunction.getName()));
        ReferenceIterator incoming = currentProgram.getReferenceManager().getReferencesTo(address);
        while (incoming.hasNext()) {
            Reference reference = incoming.next();
            Function caller = currentProgram.getFunctionManager()
                .getFunctionContaining(reference.getFromAddress());
            println("CODE_INCOMING\t" + address + "\tfrom=" + reference.getFromAddress()
                + "\t" + reference.getReferenceType() + "\towner="
                + (caller == null ? "<no-function>" : caller.getEntryPoint()));
        }
        println("CODE_ADDRESS\t" + address + "\tinstruction="
            + (center == null ? "<missing>" : center.toString()));
        if (center == null) return;
        Instruction current = center;
        for (int i = 0; i < 12 && current != null; i++) {
            println("CODE_CONTEXT\t" + current.getAddress() + "\t" + current);
            for (Reference reference : current.getReferencesFrom()) {
                println("CODE_REFERENCE\t" + current.getAddress() + "\t" + reference.getReferenceType()
                    + "\tto=" + reference.getToAddress());
            }
            current = currentProgram.getListing().getInstructionAfter(current.getAddress());
        }
    }

    private void inspectDataCell(long rawAddress) throws Exception {
        Address address = toAddr(rawAddress);
        Data data = currentProgram.getListing().getDataAt(address);
        if (data == null) data = currentProgram.getListing().getDefinedDataContaining(address);
        println("DATA_CELL\t" + address + "\tdata=" + (data == null ? "<undefined>" : data.getDataType())
            + "\tvalue=" + (data == null ? "<undefined>" : data.getValue()));
        MemoryBlock block = currentProgram.getMemory().getBlock(address);
        if (block != null) {
            println("DATA_BLOCK\t" + block.getName() + "\tread=" + block.isRead()
                + "\twrite=" + block.isWrite() + "\texecute=" + block.isExecute());
        }

        byte[] bytes = new byte[0x40];
        int length = currentProgram.getMemory().getBytes(toAddr(rawAddress - 0x20), bytes);
        StringBuilder hex = new StringBuilder();
        for (int i = 0; i < length; i++) hex.append(String.format("%02x", bytes[i] & 0xff));
        println("DATA_WINDOW\t" + toAddr(rawAddress - 0x20) + "\t" + hex);

        Reference[] references = currentProgram.getReferenceManager().getReferencesFrom(address);
        for (Reference reference : references) {
            println("DATA_OUTGOING\t" + reference.getFromAddress() + "\t" + reference.getReferenceType()
                + "\tto=" + reference.getToAddress());
        }
        ReferenceIterator incoming = currentProgram.getReferenceManager().getReferencesTo(address);
        while (incoming.hasNext()) {
            Reference reference = incoming.next();
            Function caller = currentProgram.getFunctionManager()
                .getFunctionContaining(reference.getFromAddress());
            println("DATA_INCOMING\t" + reference.getFromAddress() + "\t" + reference.getReferenceType()
                + "\tcaller=" + (caller == null ? "<no-function>" : caller.getEntryPoint()));
            inspectCallsite(reference.getFromAddress());
        }

        Address pageAddress = toAddr(rawAddress & ~0xfffL);
        ReferenceIterator pageIncoming = currentProgram.getReferenceManager().getReferencesTo(pageAddress);
        TreeMap<String, Integer> pageReferenceTypes = new TreeMap<>();
        Set<String> pageReferenceOwners = new HashSet<>();
        ArrayList<String> pageReferenceSamples = new ArrayList<>();
        int pageReferenceCount = 0;
        while (pageIncoming.hasNext()) {
            Reference reference = pageIncoming.next();
            Function caller = currentProgram.getFunctionManager()
                .getFunctionContaining(reference.getFromAddress());
            String type = reference.getReferenceType().toString();
            pageReferenceTypes.put(type, pageReferenceTypes.getOrDefault(type, 0) + 1);
            pageReferenceOwners.add(caller == null ? "<no-function>" : caller.getEntryPoint().toString());
            if (pageReferenceSamples.size() < 5) pageReferenceSamples.add(reference.getFromAddress().toString());
            pageReferenceCount++;
        }
        println("DATA_PAGE_REFERENCE_SUMMARY\tpage=" + pageAddress + "\tcount=" + pageReferenceCount
            + "\ttypes=" + pageReferenceTypes + "\tunique_owners=" + pageReferenceOwners.size());
        for (String sample : pageReferenceSamples) {
            println("DATA_PAGE_REFERENCE_SAMPLE\t" + sample);
        }
        if (pageReferenceCount > 0 && pageReferenceCount <= 16) {
            ReferenceIterator pageDetails = currentProgram.getReferenceManager().getReferencesTo(pageAddress);
            while (pageDetails.hasNext()) {
                Reference reference = pageDetails.next();
                println("DATA_PAGE_CONTEXT_BEGIN\t" + reference.getFromAddress() + "\t"
                    + reference.getReferenceType());
                inspectCallsite(reference.getFromAddress());
                println("DATA_PAGE_CONTEXT_END\t" + reference.getFromAddress());
            }
        }
    }

    private void inspectCallsite(Address address) {
        Listing listing = currentProgram.getListing();
        Instruction center = listing.getInstructionAt(address);
        if (center == null) {
            println("CALLSITE_INSTRUCTION_MISSING\t" + address);
            return;
        }
        ArrayList<Instruction> previous = new ArrayList<>();
        Instruction current = center;
        for (int i = 0; i < 6; i++) {
            current = listing.getInstructionBefore(current.getAddress());
            if (current == null) break;
            previous.add(current);
        }
        Collections.reverse(previous);
        for (Instruction instruction : previous) {
            println("CALLSITE_CONTEXT\t" + instruction.getAddress() + "\t" + instruction);
        }
        current = center;
        for (int i = 0; i < 9 && current != null; i++) {
            println("CALLSITE_CONTEXT\t" + current.getAddress() + "\t" + current);
            current = listing.getInstructionAfter(current.getAddress());
        }
    }

    private String sha256(String file) throws Exception {
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        try (InputStream input = Files.newInputStream(Paths.get(file))) {
            byte[] buffer = new byte[1024 * 1024];
            int count;
            while ((count = input.read(buffer)) != -1) {
                digest.update(buffer, 0, count);
            }
        }
        StringBuilder result = new StringBuilder();
        for (byte value : digest.digest()) result.append(String.format("%02x", value));
        return result.toString();
    }

    private static String escape(String value) {
        return value.replace("\\", "\\\\").replace("\r", "\\r")
            .replace("\n", "\\n").replace("\t", "\\t");
    }
}
