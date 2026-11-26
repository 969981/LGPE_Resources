import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.AddressSet;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;

import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.security.MessageDigest;
import java.util.HashSet;
import java.util.Locale;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class InspectSequenceRuntimeHelpers extends GhidraScript {
    private static final String EXPECTED_MAIN_SHA256 =
        "1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8";
    private static final long EXPECTED_BASE = 0x7100000000L;
    private static final String EXPECTED_NCA_ID = "2b7730a9e56498bbafac2002d4908c6b";
    private static final String[] TARGETS = {
        "7100a815e0", "7100a81de0", "7100a81ff0", "7100a81460",
        "7100aa0c60", "7100a876f0", "7100027060", "71002103c0",
        "71000adc70", "71000a63a0", "71000276e0", "7100026070",
        "71000238e0", "7100026610", "7100023990", "7100023680",
        "71000237c0", "7100023970", "7100022c40", "71002109e0",
        "7100210ae0", "7100023c70", "71001db010", "7100a812c0",
        "7100a8acd0", "7100a8ce20", "7100a81690", "7100210510",
        "7100210880", "710080f4d0", "710081a790", "7100a77c20",
        "7100002fe0", "7100003030", "7100a6e4e0", "71009d5720",
        "7100aa0b80", "7100aa2310", "7100aa2370",
        "7100aa0eb0"
    };
    private static final Pattern CALLBACK_FIELD_OFFSET = Pattern.compile(
        "#0x3e0(?![0-9a-f])", Pattern.CASE_INSENSITIVE);

    private String sha256(String path) throws Exception {
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        try (InputStream stream = Files.newInputStream(Paths.get(path))) {
            byte[] buffer = new byte[1024 * 1024];
            int count;
            while ((count = stream.read(buffer)) >= 0) {
                if (count > 0) digest.update(buffer, 0, count);
            }
        }
        StringBuilder output = new StringBuilder();
        for (byte value : digest.digest()) output.append(String.format("%02x", value));
        return output.toString();
    }

    private void inspect(Function function, DecompInterface decompiler) {
        println("HELPER\t" + function.getEntryPoint() + "\t" + function.getName()
            + "\tbytes=" + function.getBody().getNumAddresses());

        ReferenceIterator incoming = currentProgram.getReferenceManager()
            .getReferencesTo(function.getEntryPoint());
        while (incoming.hasNext()) {
            Reference reference = incoming.next();
            Function caller = currentProgram.getFunctionManager()
                .getFunctionContaining(reference.getFromAddress());
            println("INCOMING\t" + reference.getFromAddress() + "\t"
                + reference.getReferenceType() + "\tcaller="
                + (caller == null ? "<none>" : caller.getEntryPoint())
                + "\tname=" + (caller == null ? "<none>" : caller.getName()));
        }

        InstructionIterator instructions = currentProgram.getListing()
            .getInstructions(function.getBody(), true);
        while (instructions.hasNext()) {
            Instruction instruction = instructions.next();
            Reference[] references = currentProgram.getReferenceManager()
                .getReferencesFrom(instruction.getAddress());
            for (Reference reference : references) {
                if (!reference.getReferenceType().isCall()) continue;
                Function callee = currentProgram.getFunctionManager()
                    .getFunctionContaining(reference.getToAddress());
                println("CALL\t" + instruction.getAddress() + "\t"
                    + reference.getToAddress() + "\ttarget="
                    + (callee == null ? "<none>" : callee.getEntryPoint())
                    + "\tname=" + (callee == null ? "<none>" : callee.getName())
                    + "\tinstruction=" + instruction);
            }
        }

        DecompileResults result = decompiler.decompileFunction(function, 120, monitor);
        if (!result.decompileCompleted() || result.getDecompiledFunction() == null) {
            println("DECOMPILE_FAILED\t" + function.getEntryPoint() + "\t"
                + result.getErrorMessage());
            return;
        }
        String code = result.getDecompiledFunction().getC();
        println("DECOMPILED_BEGIN\t" + function.getEntryPoint() + "\tchars=" + code.length());
        println(code);
        println("DECOMPILED_END\t" + function.getEntryPoint());
    }

    private void scanCallbackFieldOffset() {
        Set<String> functions = new HashSet<>();
        int matches = 0;
        InstructionIterator instructions = currentProgram.getListing().getInstructions(true);
        while (instructions.hasNext()) {
            Instruction instruction = instructions.next();
            Matcher matcher = CALLBACK_FIELD_OFFSET.matcher(instruction.toString());
            if (!matcher.find()) continue;
            Function function = currentProgram.getFunctionManager()
                .getFunctionContaining(instruction.getAddress());
            String entry = function == null ? "<no-function>"
                : function.getEntryPoint().toString();
            if (function != null) functions.add(entry);
            println("CALLBACK_FIELD_OFFSET_USE\t+0x3e0\t" + instruction.getAddress()
                + "\tfunction=" + entry + "\t" + instruction);
            matches++;
        }
        println("CALLBACK_FIELD_OFFSET_SUMMARY\tmatches=" + matches
            + "\tfunctions=" + functions.size());
    }

    private void dumpInstructionWindow(String centerText, int radius) {
        Address center = currentProgram.getAddressFactory().getAddress(centerText);
        AddressSet range = new AddressSet(center.subtract(radius), center.add(radius));
        InstructionIterator instructions = currentProgram.getListing().getInstructions(range, true);
        while (instructions.hasNext()) {
            Instruction instruction = instructions.next();
            Function function = currentProgram.getFunctionManager()
                .getFunctionContaining(instruction.getAddress());
            println("DISASM_WINDOW\tcenter=" + center
                + "\tfunction=" + (function == null ? "<no-function>" : function.getEntryPoint())
                + "\taddress=" + instruction.getAddress()
                + "\t" + instruction);
        }
    }

    private void inspectCallbackTable(String cellText) throws Exception {
        Address cell = currentProgram.getAddressFactory().getAddress(cellText);
        long table = currentProgram.getMemory().getLong(cell);
        Address addressPoint = currentProgram.getAddressFactory().getDefaultAddressSpace()
            .getAddress(table + 0x10);
        println("CALLBACK_TABLE\tcell=" + cell
            + "\ttable=" + currentProgram.getAddressFactory().getDefaultAddressSpace().getAddress(table)
            + "\taddress_point=" + addressPoint);
        for (int slot = 0; slot < 16; slot++) {
            Address slotAddress = addressPoint.add(slot * 8L);
            long target = currentProgram.getMemory().getLong(slotAddress);
            Address targetAddress = currentProgram.getAddressFactory().getDefaultAddressSpace()
                .getAddress(target);
            if (currentProgram.getMemory().getBlock(targetAddress) == null
                || !currentProgram.getMemory().getBlock(targetAddress).isExecute()) {
                println("CALLBACK_TABLE_END\tcell=" + cell + "\tslot=" + slot
                    + "\tentry=" + targetAddress);
                break;
            }
            Function targetFunction = currentProgram.getFunctionManager().getFunctionAt(targetAddress);
            println("CALLBACK_TABLE_SLOT\tcell=" + cell + "\tslot=" + slot
                + "\taddress=" + slotAddress + "\ttarget=" + targetAddress
                + "\tfunction=" + (targetFunction == null ? "<none>" : targetFunction.getName()));
        }
    }

    private void inspectDispatchTable(String cellText, int maxSlots) throws Exception {
        Address cell = currentProgram.getAddressFactory().getAddress(cellText);
        long table = currentProgram.getMemory().getLong(cell);
        Address tableAddress = currentProgram.getAddressFactory().getDefaultAddressSpace()
            .getAddress(table);
        println("DISPATCH_TABLE\tcell=" + cell + "\ttable=" + tableAddress
            + "\tmax_slots=" + maxSlots);
        int executableTargets = 0;
        int nonExecutableRun = 0;
        int inspected = 0;
        for (int slot = 0; slot < maxSlots; slot++) {
            Address slotAddress = tableAddress.add(slot * 8L);
            long target = currentProgram.getMemory().getLong(slotAddress);
            Address targetAddress = currentProgram.getAddressFactory().getDefaultAddressSpace()
                .getAddress(target);
            boolean executable = currentProgram.getMemory().getBlock(targetAddress) != null
                && currentProgram.getMemory().getBlock(targetAddress).isExecute();
            Function targetFunction = executable
                ? currentProgram.getFunctionManager().getFunctionAt(targetAddress) : null;
            println("DISPATCH_SLOT\tindex=" + slot + "\taddress=" + slotAddress
                + "\ttarget=" + targetAddress + "\texecutable=" + executable
                + "\tfunction=" + (targetFunction == null ? "<none>" : targetFunction.getName()));
            inspected++;
            if (executable) {
                executableTargets++;
                nonExecutableRun = 0;
            } else {
                nonExecutableRun++;
                if (nonExecutableRun >= 8) break;
            }
        }
        println("DISPATCH_TABLE_SUMMARY\tcell=" + cell + "\tinspected=" + inspected
            + "\texecutable_targets=" + executableTargets
            + "\tterminating_nonexec_run=" + nonExecutableRun);
    }

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

        DecompInterface decompiler = new DecompInterface();
        decompiler.openProgram(currentProgram);

        Address vtableCell = currentProgram.getAddressFactory().getAddress("71015fb380");
        long vtable = currentProgram.getMemory().getLong(vtableCell);
        long addressPoint = vtable + 0x10;
        long slot38 = currentProgram.getMemory().getLong(
            currentProgram.getAddressFactory().getDefaultAddressSpace().getAddress(addressPoint + 0x38));
        long slot40 = currentProgram.getMemory().getLong(
            currentProgram.getAddressFactory().getDefaultAddressSpace().getAddress(addressPoint + 0x40));
        if (vtable != 0x71015287e8L || slot38 != 0x7100026070L || slot40 != 0x7100026610L) {
            throw new IllegalStateException("resource request vtable targets differ from the recorded 1.0.2 trace");
        }
        println("REQUEST_VTABLE\tglobal_cell=" + vtableCell
            + "\tglobal_value=" + currentProgram.getAddressFactory().getDefaultAddressSpace().getAddress(vtable)
            + "\taddress_point=" + currentProgram.getAddressFactory().getDefaultAddressSpace().getAddress(addressPoint)
            + "\tslot_38=" + currentProgram.getAddressFactory().getDefaultAddressSpace().getAddress(slot38)
            + "\tslot_40=" + currentProgram.getAddressFactory().getDefaultAddressSpace().getAddress(slot40)
            + "\tread_only=true");

        Address sequenceVtableCell = currentProgram.getAddressFactory().getAddress("71015fe628");
        long sequenceVtable = currentProgram.getMemory().getLong(sequenceVtableCell);
        long sequenceAddressPoint = sequenceVtable + 0x10;
        long sequenceSlot0 = currentProgram.getMemory().getLong(
            currentProgram.getAddressFactory().getDefaultAddressSpace().getAddress(sequenceAddressPoint));
        long sequenceSlot1 = currentProgram.getMemory().getLong(
            currentProgram.getAddressFactory().getDefaultAddressSpace().getAddress(sequenceAddressPoint + 8));
        if (sequenceVtable != 0x7101541e30L
            || sequenceSlot0 != 0x71002109e0L || sequenceSlot1 != 0x7100210ae0L) {
            throw new IllegalStateException("BSEQ object vtable targets differ from the recorded 1.0.2 trace");
        }
        println("SEQUENCE_OBJECT_VTABLE\tglobal_cell=" + sequenceVtableCell
            + "\tglobal_value=" + currentProgram.getAddressFactory().getDefaultAddressSpace().getAddress(sequenceVtable)
            + "\taddress_point=" + currentProgram.getAddressFactory().getDefaultAddressSpace().getAddress(sequenceAddressPoint)
            + "\tread_only=true");
        for (int slot = 0; slot < 24; slot++) {
            Address slotAddress = currentProgram.getAddressFactory().getDefaultAddressSpace()
                .getAddress(sequenceAddressPoint + slot * 8L);
            long target = currentProgram.getMemory().getLong(slotAddress);
            Address targetAddress = currentProgram.getAddressFactory().getDefaultAddressSpace().getAddress(target);
            if (currentProgram.getMemory().getBlock(targetAddress) == null
                || !currentProgram.getMemory().getBlock(targetAddress).isExecute()) {
                println("SEQUENCE_OBJECT_VTABLE_END\tslot=" + slot + "\tentry=" + targetAddress);
                break;
            }
            Function targetFunction = currentProgram.getFunctionManager().getFunctionAt(targetAddress);
            println("SEQUENCE_OBJECT_VTABLE_SLOT\tindex=" + slot
                + "\taddress=" + slotAddress
                + "\ttarget=" + targetAddress
                + "\tfunction=" + (targetFunction == null ? "<none>" : targetFunction.getName())
                + "\tfunction_entry=" + (targetFunction == null ? "<none>" : targetFunction.getEntryPoint()));
        }

        int decompiled = 0;
        int failures = 0;
        inspectCallbackTable("7101608de8");
        inspectCallbackTable("7101608df0");
        inspectDispatchTable("7101608df8", 256);
        scanCallbackFieldOffset();
        dumpInstructionWindow("7100a789ac", 0x180);
        dumpInstructionWindow("7100a7c7b4", 0x40);
        for (String target : TARGETS) {
            Address address = currentProgram.getAddressFactory().getAddress(target);
            Function function = currentProgram.getFunctionManager().getFunctionAt(address);
            if (function == null) {
                println("FUNCTION_NOT_FOUND\t" + target);
                failures++;
                continue;
            }
            inspect(function, decompiler);
            decompiled++;
        }
        decompiler.dispose();
        println("SUMMARY\tmain_sha256=" + actualHash
            + "\timage_base=0x" + Long.toHexString(currentProgram.getImageBase().getOffset())
            + "\tselected_functions=" + TARGETS.length
            + "\tdecompiled=" + decompiled
            + "\tfunction_failures=" + failures
            + "\tread_only=true");
    }
}
