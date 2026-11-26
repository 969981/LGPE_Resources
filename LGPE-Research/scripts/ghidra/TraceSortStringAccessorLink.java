import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionIterator;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import ghidra.program.model.mem.MemoryBlock;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.util.Locale;

public class TraceSortStringAccessorLink extends GhidraScript {
    private static final long EXPECTED_BASE = 0x7100000000L;
    private static final String EXPECTED_NCA_ID = "2b7730a9e56498bbafac2002d4908c6b";
    private static final String EXPECTED_MAIN_SHA256 =
        "1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8";
    private static final long[] TARGETS = {
        0x7100176550L, 0x7100176940L, 0x7100176c50L, 0x7100176c70L,
        0x7100b094e0L, 0x7100b09810L, 0x7100b0a200L, 0x7100b315e0L,
        0x7100374530L, 0x7100377820L, 0x7100377a50L, 0x7100377c60L,
        0x7100377e70L, 0x7100377a30L, 0x7100377a40L, 0x7100377a20L,
        0x7100377c50L, 0x7100377e60L,
        0x7100176ce0L, 0x7100176e40L, 0x7100176fa0L, 0x7100177100L,
        0x7100b09900L, 0x7100b0b560L,
        0x7100b071d0L, 0x7100b07730L, 0x7100b07d10L, 0x7100b07d80L,
        0x7100b07e00L, 0x7100b07e80L, 0x7100b07d60L, 0x7100b07dc0L,
        0x7100b07e40L, 0x7100b07ee0L, 0x7100b07f80L, 0x7100b07fc0L,
        0x7100b0b6a0L, 0x7100b0b6b0L, 0x7100b0b6c0L, 0x7100b0b6d0L,
        0x7100b0b6e0L,
        0x7100b09cc0L, 0x7100b0a000L, 0x7100b0a060L,
        0x7100374a90L, 0x7100374ad0L, 0x7100374ac0L,
        0x7100b31400L, 0x7100b318c0L,
        0x7100750320L, 0x710074eeb0L,
        0x71007774a0L, 0x71007775b0L, 0x7100b06f10L
    };
    private static final String[] ROLES = {
        "sort helper constructor called with parent resource manager",
        "sort helper initializer called before localized resource request",
        "sort helper 32-bit indexed accessor",
        "sort helper 16-bit element search accessor",
        "monsname owner constructor",
        "monsname owner allocates and initializes sort helper",
        "owner table query calls helper accessors",
        "monsname localized three-file resource request",
        "generic three-resource buffer helper",
        "helper binds first indexed object",
        "helper binds fixed-index object 2",
        "helper binds fixed-index object 3",
        "helper binds fixed-index object 4",
        "helper reads raw data pointer from resource",
        "helper reads resource element count",
        "helper reads indexed 16-bit value",
        "helper reads secondary resource pointer",
        "helper reads tertiary resource pointer",
        "helper loads resource family A",
        "helper loads resource family B",
        "helper loads resource family C",
        "helper loads resource family D",
        "owner initialization after localized resource request",
        "localized resource object construction",
        "derived owner vtable method slot 0",
        "derived owner vtable method slot 1",
        "derived owner vtable method slot 12",
        "derived owner vtable method slot 13",
        "derived owner vtable method slot 14",
        "derived owner vtable method slot 15",
        "derived owner secondary vtable slot 0",
        "derived owner secondary vtable slot 1",
        "derived owner secondary vtable slot 2",
        "derived owner secondary vtable slot 3",
        "derived owner secondary vtable slot 4",
        "derived owner secondary vtable slot 5",
        "resource container vtable slot 4",
        "resource container vtable slot 5",
        "resource container vtable slot 11",
        "resource container vtable slot 12",
        "resource request object factory",
        "localized owner indexed child-resource accessor caller",
        "localized owner child-resource lookup caller",
        "localized owner child-resource count and iterator caller",
        "generic indexed child-resource accessor",
        "generic child-resource lookup accessor",
        "generic child-resource count accessor",
        "second localized three-file resource request caller",
        "third localized three-file resource request caller",
        "indexed localized sort accessor caller 2",
        "indexed localized sort accessor caller 3",
        "item localized resource owner request caller",
        "waza localized resource owner request caller",
        "monsname owner function with direct +0x350/+0x358 loads"
    };
    private int decompiled;
    private int temporaryFunctions;
    private int ownerRangeFunctions;
    private int ownerRangeDecompiled;
    private int ownerRangeFieldCandidates;
    private int resourceRangeFunctions;
    private int resourceRangeDecompiled;
    private int resourceRangeFieldCandidates;
    private int offsetOperandFunctions;
    private int offsetOperandDecompiled;
    private int offsetOperandCodeCandidates;
    private int localizedOwnerInboundReferences;

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
            + currentProgram.getImageBase() + "\tlanguage="
            + currentProgram.getLanguage().getLanguageID() + "\tmain_sha256=" + mainHash);
        println("SCOPE\tread-only exact-build trace follows the 1.0.2 owner/helper initialization, "
            + "resource-family loads, indexed accessors, localized owner callers, "
            + "generic child-resource accessors, derived-owner vtable methods, "
            + "owner-range field-use scan, shared-resource field-use scan, "
            + "and separate monsname resource request; "
            + "no runtime execution is inferred");

        for (int i = 0; i < TARGETS.length; i++) inspectFunction(TARGETS[i], ROLES[i]);
        scanOwnerRangeForChildFieldUses();
        scanSharedResourceObjectFieldUses();
        scanFunctionsWithLiteralPointerOffsetOperand();
        dumpLocalizedOwnerInstructionContext();
        inspectReferencesTo(0x7100176550L, "sort helper constructor");
        inspectReferencesTo(0x7100176940L, "sort helper initializer");
        inspectReferencesTo(0x7100176c50L, "sort helper 32-bit accessor");
        inspectReferencesTo(0x7100176c70L, "sort helper 16-bit accessor");
        inspectReferencesTo(0x71016093c8L, "monsname owner vtable global");
        inspectReferencesTo(0x7101609330L, "monsname list vtable global");
        inspectReferencesTo(0x7101609450L, "localized resource container vtable global");
        inspectPointerTable(0x7101609450L, "localized resource container vtable",
            0x10L, 0x30L, 0x68L);

        println("SUMMARY\tdecompiled_functions=" + decompiled
            + "\ttemporary_functions=" + temporaryFunctions
            + "\towner_range_functions=" + ownerRangeFunctions
            + "\towner_range_decompiled=" + ownerRangeDecompiled
            + "\towner_range_field_candidates=" + ownerRangeFieldCandidates
            + "\tresource_range_functions=" + resourceRangeFunctions
            + "\tresource_range_decompiled=" + resourceRangeDecompiled
            + "\tresource_range_field_candidates=" + resourceRangeFieldCandidates
            + "\toffset_operand_functions=" + offsetOperandFunctions
            + "\toffset_operand_decompiled=" + offsetOperandDecompiled
            + "\toffset_operand_c_literal_candidates=" + offsetOperandCodeCandidates
            + "\tlocalized_owner_inbound_references=" + localizedOwnerInboundReferences
            + "\tprogram=" + currentProgram.getName());
        if (!EXPECTED_MAIN_SHA256.equals(sha256(Path.of(executable.trim())))) {
            throw new IllegalStateException("source main hash changed during inspection");
        }
    }

    private Address address(long offset) {
        return currentProgram.getImageBase().add(offset - EXPECTED_BASE);
    }

    private Function functionAt(long offset) throws Exception {
        Address target = address(offset);
        Function function = currentProgram.getFunctionManager().getFunctionAt(target);
        if (function == null) function = currentProgram.getFunctionManager().getFunctionContaining(target);
        if (function == null) {
            Instruction instruction = currentProgram.getListing().getInstructionAt(target);
            if (instruction == null) {
                MemoryBlock block = currentProgram.getMemory().getBlock(target);
                if (block != null && block.isExecute()) disassemble(target);
            }
            if (currentProgram.getListing().getInstructionAt(target) != null) {
                function = createFunction(target, null);
                if (function != null) temporaryFunctions++;
            }
        }
        return function;
    }

    private void inspectFunction(long offset, String role) throws Exception {
        Address target = address(offset);
        Function function = functionAt(offset);
        if (function == null) {
            println("FUNCTION_NOT_FOUND\trole=" + role + "\taddress=" + target);
            return;
        }
        println("FUNCTION\trole=" + role + "\trequested=" + target
            + "\tentry=" + function.getEntryPoint() + "\tname=" + function.getName());
        DecompInterface decompiler = new DecompInterface();
        decompiler.openProgram(currentProgram);
        DecompileResults result = decompiler.decompileFunction(function, 60, monitor);
        if (result != null && result.decompileCompleted()
            && result.getDecompiledFunction() != null) {
            String[] lines = result.getDecompiledFunction().getC().split("\\n");
            for (int i = 0; i < lines.length; i++) {
                println("CODE\t" + function.getEntryPoint() + "\t" + i + "\t" + lines[i]);
            }
            decompiled++;
        } else {
            println("DECOMPILE_FAILED\trole=" + role + "\taddress=" + target
                + "\tmessage=" + (result == null ? "null result" : result.getErrorMessage()));
        }
        decompiler.dispose();
        ReferenceIterator references = currentProgram.getReferenceManager()
            .getReferencesTo(function.getEntryPoint());
        int count = 0;
        while (references.hasNext()) {
            monitor.checkCancelled();
            Reference reference = references.next();
            Function caller = currentProgram.getFunctionManager()
                .getFunctionContaining(reference.getFromAddress());
            println("INCOMING\trole=" + role + "\tfrom=" + reference.getFromAddress()
                + "\ttype=" + reference.getReferenceType() + "\tcaller="
                + (caller == null ? "<no-function>" : caller.getEntryPoint())
                + "\tname=" + (caller == null ? "<no-function>" : caller.getName()));
            count++;
        }
        println("INCOMING_COUNT\trole=" + role + "\tcount=" + count);
    }

    private void inspectReferencesTo(long offset, String role) throws Exception {
        Address target = address(offset);
        println("REFERENCES_BEGIN\trole=" + role + "\ttarget=" + target);
        ReferenceIterator references = currentProgram.getReferenceManager().getReferencesTo(target);
        int count = 0;
        while (references.hasNext()) {
            monitor.checkCancelled();
            Reference reference = references.next();
            Function function = currentProgram.getFunctionManager()
                .getFunctionContaining(reference.getFromAddress());
            println("REFERENCE\trole=" + role + "\tfrom=" + reference.getFromAddress()
                + "\ttype=" + reference.getReferenceType() + "\tfunction="
                + (function == null ? "<no-function>" : function.getEntryPoint())
                + "\tname=" + (function == null ? "<no-function>" : function.getName()));
            count++;
        }
        println("REFERENCES_COUNT\trole=" + role + "\tcount=" + count);
    }

    private void inspectPointerTable(long globalOffset, String role, long... tableOffsets)
        throws Exception {
        Address global = address(globalOffset);
        long baseOffset = currentProgram.getMemory().getLong(global);
        Address base = currentProgram.getAddressFactory().getDefaultAddressSpace()
            .getAddress(baseOffset);
        println("POINTER_TABLE_GLOBAL\trole=" + role + "\tglobal=" + global
            + "\tvalue=" + base);
        for (long tableOffset : tableOffsets) {
            Address table = base.add(tableOffset);
            println("POINTER_TABLE_BEGIN\trole=" + role + "\ttable=" + table
                + "\tbase_offset=0x" + Long.toHexString(tableOffset));
            for (int index = 0; index < 16; index++) {
                monitor.checkCancelled();
                Address slot = table.add(index * 8L);
                long value = currentProgram.getMemory().getLong(slot);
                Address target = currentProgram.getAddressFactory().getDefaultAddressSpace()
                    .getAddress(value);
                Function function = currentProgram.getFunctionManager().getFunctionAt(target);
                if (function == null) {
                    function = currentProgram.getFunctionManager().getFunctionContaining(target);
                }
                println("POINTER_TABLE_SLOT\tindex=" + index + "\taddress=" + slot
                    + "\tvalue=" + target + "\tfunction="
                    + (function == null ? "<no-function>" : function.getName()));
            }
            println("POINTER_TABLE_END\trole=" + role);
        }
    }

    private void scanOwnerRangeForChildFieldUses() throws Exception {
        Address start = address(0x7100b06d60L);
        Address end = address(0x7100b0b690L);
        println("OWNER_RANGE_BEGIN\tstart=" + start + "\tend=" + end
            + "\tsearch=decompiled references shaped as owner-plus-0x28 or owner-index-5");
        DecompInterface decompiler = new DecompInterface();
        decompiler.openProgram(currentProgram);
        FunctionIterator functions = currentProgram.getFunctionManager().getFunctions(start, true);
        while (functions.hasNext()) {
            monitor.checkCancelled();
            Function function = functions.next();
            if (function.getEntryPoint().compareTo(end) > 0) break;
            ownerRangeFunctions++;
            DecompileResults result = decompiler.decompileFunction(function, 30, monitor);
            if (result == null || !result.decompileCompleted()
                || result.getDecompiledFunction() == null) {
                println("OWNER_RANGE_DECOMPILE_FAILED\tfunction=" + function.getEntryPoint()
                    + "\tname=" + function.getName());
                continue;
            }
            ownerRangeDecompiled++;
            String[] lines = result.getDecompiledFunction().getC().split("\\n");
            for (int index = 0; index < lines.length; index++) {
                String line = lines[index];
                if (line.contains("+ 0x28") || line.contains("[5]")) {
                    if (ownerRangeFieldCandidates == 0
                        || !lastCandidateFunction.equals(function.getEntryPoint().toString())) {
                        ownerRangeFieldCandidates++;
                        lastCandidateFunction = function.getEntryPoint().toString();
                        println("OWNER_RANGE_FIELD_CANDIDATE\tfunction="
                            + function.getEntryPoint() + "\tname=" + function.getName());
                    }
                    println("OWNER_RANGE_FIELD_LINE\tfunction=" + function.getEntryPoint()
                        + "\tline=" + index + "\ttext=" + line);
                }
            }
        }
        decompiler.dispose();
        println("OWNER_RANGE_END\tfunctions=" + ownerRangeFunctions
            + "\tdecompiled=" + ownerRangeDecompiled
            + "\tfield_candidate_functions=" + ownerRangeFieldCandidates);
    }

    private String lastCandidateFunction = "";

    private void scanFunctionsWithLiteralPointerOffsetOperand() throws Exception {
        println("OFFSET_OPERAND_SCAN_BEGIN\tscope=all current function-manager bodies"
            + "\tcondition=literal load operand [base,#0x350]; base provenance is not assumed"
            + "\treports C lines and incoming references");
        DecompInterface decompiler = new DecompInterface();
        decompiler.openProgram(currentProgram);
        FunctionIterator functions = currentProgram.getFunctionManager().getFunctions(true);
        while (functions.hasNext()) {
            monitor.checkCancelled();
            Function function = functions.next();
            int offset350LoadCount = 0;
            int offset358LoadCount = 0;
            InstructionIterator instructions = currentProgram.getListing()
                .getInstructions(function.getBody(), true);
            while (instructions.hasNext()) {
                Instruction instruction = instructions.next();
                String text = instruction.toString().toLowerCase(Locale.ROOT);
                if (!isMemoryLoad(text)) continue;
                if (text.contains("#0x350]")) {
                    offset350LoadCount++;
                }
                if (text.contains("#0x358]")) {
                    offset358LoadCount++;
                }
            }
            if (offset350LoadCount == 0) continue;
            offsetOperandFunctions++;
            println("OFFSET_OPERAND_FUNCTION\tentry=" + function.getEntryPoint()
                + "\tname=" + function.getName()
                + "\tloads_350=" + offset350LoadCount
                + "\tloads_358=" + offset358LoadCount);
            DecompileResults result = decompiler.decompileFunction(function, 30, monitor);
            if (result == null || !result.decompileCompleted()
                || result.getDecompiledFunction() == null) {
                println("OFFSET_OPERAND_DECOMPILE_FAILED\tentry=" + function.getEntryPoint()
                    + "\tname=" + function.getName());
                continue;
            }
            offsetOperandDecompiled++;
            String[] lines = result.getDecompiledFunction().getC().split("\\n");
            boolean hasRelevantCodeLine = false;
            for (int index = 0; index < lines.length; index++) {
                String line = lines[index];
                if (!line.contains("0x350")) continue;
                if (!hasRelevantCodeLine) {
                    hasRelevantCodeLine = true;
                    offsetOperandCodeCandidates++;
                }
                println("OFFSET_OPERAND_CODE\tentry=" + function.getEntryPoint()
                    + "\tline=" + index + "\ttext=" + line);
            }
            if (!hasRelevantCodeLine) {
                println("OFFSET_OPERAND_NO_C_LITERAL\tentry=" + function.getEntryPoint()
                    + "\tname=" + function.getName());
            }
            ReferenceIterator incoming = currentProgram.getReferenceManager()
                .getReferencesTo(function.getEntryPoint());
            int incomingCount = 0;
            while (incoming.hasNext()) {
                monitor.checkCancelled();
                Reference reference = incoming.next();
                Function caller = currentProgram.getFunctionManager()
                    .getFunctionContaining(reference.getFromAddress());
                String callerName = caller == null ? "<no-function>" : caller.getName();
                Address callerEntry = caller == null ? null : caller.getEntryPoint();
                println("OFFSET_OPERAND_INCOMING\ttarget=" + function.getEntryPoint()
                    + "\tfrom=" + reference.getFromAddress()
                    + "\ttype=" + reference.getReferenceType()
                    + "\tcaller=" + (callerEntry == null ? "<no-function>" : callerEntry)
                    + "\tcaller_name=" + callerName);
                if (callerEntry != null
                    && isLocalizedOwnerOrRequestCode(callerEntry.getOffset())) {
                    localizedOwnerInboundReferences++;
                }
                incomingCount++;
            }
            println("OFFSET_OPERAND_INCOMING_COUNT\ttarget=" + function.getEntryPoint()
                + "\tcount=" + incomingCount);
        }
        decompiler.dispose();
        println("OFFSET_OPERAND_SCAN_END\tfunctions=" + offsetOperandFunctions
            + "\tdecompiled=" + offsetOperandDecompiled
            + "\tc_literal_candidate_functions=" + offsetOperandCodeCandidates
            + "\tlocalized_owner_inbound_references=" + localizedOwnerInboundReferences);
    }

    private static boolean isLocalizedOwnerOrRequestCode(long offset) {
        return (offset >= 0x7100b06d60L && offset <= 0x7100b0b690L)
            || (offset >= 0x7100b31300L && offset <= 0x7100b32330L)
            || offset == 0x710074eeb0L || offset == 0x7100750320L;
    }

    private void dumpLocalizedOwnerInstructionContext() throws Exception {
        Address start = address(0x7100b06f50L);
        Address end = address(0x7100b07080L);
        println("LOCALIZED_OWNER_INSN_CONTEXT_BEGIN\tstart=" + start + "\tend=" + end
            + "\tfunction=" + currentProgram.getFunctionManager()
                .getFunctionAt(address(0x7100b06f10L)));
        for (long offset = 0x7100b06f50L; offset <= 0x7100b07080L; offset += 4) {
            monitor.checkCancelled();
            Address instructionAddress = address(offset);
            Instruction instruction = currentProgram.getListing()
                .getInstructionAt(instructionAddress);
            if (instruction != null) {
                println("LOCALIZED_OWNER_INSN_CONTEXT\taddress=" + instructionAddress
                    + "\tinstruction=" + instruction);
            }
        }
        println("LOCALIZED_OWNER_INSN_CONTEXT_END");
    }

    private static boolean isMemoryLoad(String instruction) {
        String mnemonic = instruction.split("\\s+", 2)[0];
        return mnemonic.equals("ldr") || mnemonic.equals("ldur")
            || mnemonic.equals("ldp") || mnemonic.equals("ldnp")
            || mnemonic.equals("ldrsw") || mnemonic.equals("ldrb")
            || mnemonic.equals("ldrh") || mnemonic.equals("ldrsb")
            || mnemonic.equals("ldrsh");
    }

    private void scanSharedResourceObjectFieldUses() throws Exception {
        Address start = address(0x7100373e00L);
        Address end = address(0x7100374b80L);
        println("RESOURCE_RANGE_BEGIN\tstart=" + start + "\tend=" + end
            + "\tsearch=shared resource object fields +0x340/+0x348, +0x350/+0x358, +0x360");
        DecompInterface decompiler = new DecompInterface();
        decompiler.openProgram(currentProgram);
        FunctionIterator functions = currentProgram.getFunctionManager().getFunctions(start, true);
        while (functions.hasNext()) {
            monitor.checkCancelled();
            Function function = functions.next();
            if (function.getEntryPoint().compareTo(end) > 0) break;
            resourceRangeFunctions++;
            DecompileResults result = decompiler.decompileFunction(function, 30, monitor);
            if (result == null || !result.decompileCompleted()
                || result.getDecompiledFunction() == null) {
                println("RESOURCE_RANGE_DECOMPILE_FAILED\tfunction=" + function.getEntryPoint()
                    + "\tname=" + function.getName());
                continue;
            }
            resourceRangeDecompiled++;
            String[] lines = result.getDecompiledFunction().getC().split("\\n");
            boolean candidate = false;
            for (int index = 0; index < lines.length; index++) {
                String line = lines[index];
                if (line.contains("0x340") || line.contains("0x348")
                    || line.contains("0x350") || line.contains("0x358")
                    || line.contains("0x360")) {
                    if (!candidate) {
                        candidate = true;
                        resourceRangeFieldCandidates++;
                        println("RESOURCE_RANGE_FIELD_CANDIDATE\tfunction="
                            + function.getEntryPoint() + "\tname=" + function.getName());
                    }
                    println("RESOURCE_RANGE_FIELD_LINE\tfunction=" + function.getEntryPoint()
                        + "\tline=" + index + "\ttext=" + line);
                }
            }
        }
        decompiler.dispose();
        println("RESOURCE_RANGE_END\tfunctions=" + resourceRangeFunctions
            + "\tdecompiled=" + resourceRangeDecompiled
            + "\tfield_candidate_functions=" + resourceRangeFieldCandidates);
    }

    private static String sha256(Path file) throws Exception {
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        try (java.io.InputStream in = Files.newInputStream(file)) {
            byte[] buffer = new byte[1024 * 1024];
            int read;
            while ((read = in.read(buffer)) >= 0) digest.update(buffer, 0, read);
        }
        StringBuilder hex = new StringBuilder();
        for (byte b : digest.digest()) hex.append(String.format("%02x", b & 0xff));
        return hex.toString();
    }
}
