import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import ghidra.program.model.listing.Data;
import ghidra.program.model.mem.MemoryBlock;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

/** Read-only exact-build operand-text scan for explicit script registry page references. */
public class InspectScriptRegistryOperandScan extends GhidraScript {
    private static final String PAGE_FRAGMENT = "710153c";
    private static final String[][] DATA_CELLS = {
        {"MapChangeCoreNamePointer", "0x710153c878", "false"},
        {"CaptureCallFunctionPointer", "0x710153c880", "false"},
        {"GetCaptureResultFunctionPointer", "0x710153c890", "false"},
        {"OperandPageCandidate_153ced8", "0x710153ced8", "true"},
        {"OperandPageCandidate_153cf20", "0x710153cf20", "true"},
        {"OperandPageCandidate_153cf68", "0x710153cf68", "true"},
        {"OperandPageCandidate_153cfb0", "0x710153cfb0", "true"}
    };

    private String entry(Function function) {
        return function == null ? "NONE" : function.getEntryPoint().toString();
    }

    private String blockName(Address address) {
        MemoryBlock block = currentProgram.getMemory().getBlock(address);
        return block == null ? "NONE" : block.getName();
    }

    private boolean executable(Address address) {
        MemoryBlock block = currentProgram.getMemory().getBlock(address);
        return block != null && block.isExecute();
    }

    private List<Address> inspectDataCells() throws Exception {
        List<Address> codeTargets = new ArrayList<>();
        for (String[] probe : DATA_CELLS) {
            String label = probe[0];
            Address cell = toAddr(probe[1]);
            boolean inspectTargetSlots = Boolean.parseBoolean(probe[2]);
            long rawValue = currentProgram.getMemory().getLong(cell);
            Address target = toAddr(rawValue);
            boolean mapped = currentProgram.getMemory().contains(target);
            Function exact = mapped ? currentProgram.getFunctionManager().getFunctionAt(target) : null;
            Function owner = mapped ? currentProgram.getFunctionManager().getFunctionContaining(target) : null;
            Data data = currentProgram.getListing().getDataAt(cell);
            String dataType = data == null ? "NONE" : data.getDataType().getName();
            println("DATA_VALUE\t" + label + "\t" + cell + "\t0x"
                + Long.toHexString(rawValue) + "\t" + mapped + "\t"
                + blockName(target) + "\t" + executable(target) + "\t"
                + entry(exact) + "\t" + entry(owner) + "\t" + dataType);
            if (label.startsWith("OperandPageCandidate_") && mapped
                && executable(target) && !codeTargets.contains(target)) {
                codeTargets.add(target);
            }

            ReferenceIterator references = currentProgram.getReferenceManager().getReferencesTo(cell);
            while (references.hasNext()) {
                Reference reference = references.next();
                Function referenceOwner = currentProgram.getFunctionManager()
                    .getFunctionContaining(reference.getFromAddress());
                println("DATA_REF\t" + label + "\t" + cell + "\t"
                    + reference.getFromAddress() + "\t" + reference.getReferenceType()
                    + "\t" + entry(referenceOwner));
            }

            if (!inspectTargetSlots || !mapped || executable(target)) continue;
            for (int index = 0; index < 8; index++) {
                Address slot = target.add(index * 8L);
                if (!currentProgram.getMemory().contains(slot)
                    || !currentProgram.getMemory().contains(slot.add(7))) {
                    break;
                }
                long slotValue;
                try {
                    slotValue = currentProgram.getMemory().getLong(slot);
                } catch (Exception error) {
                    println("POINTER_SLOT_ERROR\t" + label + "\t" + index + "\t"
                        + slot + "\t" + error.getClass().getSimpleName());
                    break;
                }
                Address slotTarget = toAddr(slotValue);
                boolean slotMapped = currentProgram.getMemory().contains(slotTarget);
                Function slotExact = slotMapped
                    ? currentProgram.getFunctionManager().getFunctionAt(slotTarget) : null;
                Function slotOwner = slotMapped
                    ? currentProgram.getFunctionManager().getFunctionContaining(slotTarget) : null;
                println("POINTER_SLOT\t" + label + "\t" + index + "\t" + slot
                    + "\t0x" + Long.toHexString(slotValue) + "\t" + slotMapped
                    + "\t" + blockName(slotTarget) + "\t" + executable(slotTarget)
                    + "\t" + entry(slotExact) + "\t" + entry(slotOwner));
            }
        }
        return codeTargets;
    }

    private String hex(byte[] bytes) {
        StringBuilder value = new StringBuilder(bytes.length * 2);
        for (byte item : bytes) value.append(String.format("%02x", item & 0xff));
        return value.toString();
    }

    private void inspectCodeTargets(List<Address> targets) throws Exception {
        DecompInterface targetDecompiler = new DecompInterface();
        targetDecompiler.openProgram(currentProgram);
        int created = 0;
        int decompiled = 0;
        int failures = 0;
        for (Address target : targets) {
            Function function = currentProgram.getFunctionManager().getFunctionAt(target);
            boolean temporary = false;
            if (function == null) {
                Function containing = currentProgram.getFunctionManager().getFunctionContaining(target);
                if (containing != null) {
                    println("CODE_TARGET_NOT_ENTRY\t" + target + "\t"
                        + containing.getEntryPoint());
                    continue;
                }
                if (currentProgram.getListing().getInstructionAt(target) == null) {
                    disassemble(target);
                }
                function = createFunction(target, null);
                if (function == null || !function.getEntryPoint().equals(target)) {
                    println("CODE_TARGET_CREATE_FAILED\t" + target);
                    failures++;
                    continue;
                }
                temporary = true;
                created++;
            }

            int bodyInstructionCount = 0;
            for (InstructionIterator iterator = currentProgram.getListing()
                    .getInstructions(function.getBody(), true); iterator.hasNext();) {
                Instruction instruction = iterator.next();
                bodyInstructionCount++;
            }
            println("CODE_TARGET\t" + target + "\t" + function.getEntryPoint()
                + "\tbytes=" + function.getBody().getNumAddresses()
                + "\tinstructions=" + bodyInstructionCount
                + "\ttemporary=" + temporary);

            ReferenceIterator incoming = currentProgram.getReferenceManager().getReferencesTo(target);
            while (incoming.hasNext()) {
                Reference reference = incoming.next();
                Function owner = currentProgram.getFunctionManager()
                    .getFunctionContaining(reference.getFromAddress());
                println("CODE_TARGET_INCOMING\t" + target + "\t"
                    + reference.getFromAddress() + "\t" + reference.getReferenceType()
                    + "\t" + entry(owner));
            }

            for (InstructionIterator iterator = currentProgram.getListing()
                    .getInstructions(function.getBody(), true); iterator.hasNext();) {
                Instruction instruction = iterator.next();
                println("CODE_TARGET_INSN\t" + target + "\t"
                    + instruction.getAddress() + "\t" + hex(instruction.getBytes())
                    + "\t" + instruction);
                if (!instruction.getFlowType().isCall()) continue;
                Address[] flows = instruction.getFlows();
                if (flows == null || flows.length == 0) {
                    println("CODE_TARGET_INDIRECT_CALL\t" + target + "\t"
                        + instruction.getAddress() + "\t" + instruction);
                } else {
                    for (Address flow : flows) {
                        println("CODE_TARGET_CALL\t" + target + "\t"
                            + instruction.getAddress() + "\t" + flow + "\t" + instruction);
                    }
                }
            }

            DecompileResults result = targetDecompiler.decompileFunction(function, 120, monitor);
            if (!result.decompileCompleted() || result.getDecompiledFunction() == null) {
                failures++;
                println("CODE_TARGET_DECOMPILE_FAILED\t" + target + "\t" + result.getErrorMessage());
            } else {
                decompiled++;
                String code = result.getDecompiledFunction().getC();
                println("CODE_TARGET_DECOMPILED_BEGIN\t" + target + "\tchars=" + code.length());
                println(code);
                println("CODE_TARGET_DECOMPILED_END\t" + target);
            }
        }
        targetDecompiler.dispose();
        println("CODE_TARGET_SUMMARY\tuniqueTargets=" + targets.size()
            + "\ttemporaryBoundaries=" + created
            + "\tdecompiled=" + decompiled
            + "\tfailures=" + failures);
    }

    private List<Instruction> context(Instruction instruction) {
        List<Instruction> result = new ArrayList<>();
        Instruction cursor = instruction;
        for (int i = 0; i < 8; i++) {
            Instruction previous = currentProgram.getListing()
                .getInstructionBefore(cursor.getAddress());
            if (previous == null) break;
            result.add(0, previous);
            cursor = previous;
        }
        result.add(instruction);
        cursor = instruction;
        for (int i = 0; i < 8; i++) {
            Instruction next = currentProgram.getListing()
                .getInstructionAfter(cursor.getAddress());
            if (next == null) break;
            result.add(next);
            cursor = next;
        }
        return result;
    }

    @Override
    public void run() throws Exception {
        println("PROGRAM\t" + currentProgram.getName() + "\tbase="
            + currentProgram.getImageBase() + "\t" + currentProgram.getExecutablePath());

        Map<String, Function> owners = new LinkedHashMap<>();
        List<String> hits = new ArrayList<>();
        long instructionCount = 0;
        InstructionIterator iterator = currentProgram.getListing().getInstructions(true);
        while (iterator.hasNext()) {
            monitor.checkCancelled();
            Instruction instruction = iterator.next();
            instructionCount++;
            String assembly = instruction.toString();
            if (!assembly.toLowerCase(Locale.ROOT).contains(PAGE_FRAGMENT)) continue;

            Function owner = currentProgram.getFunctionManager()
                .getFunctionContaining(instruction.getAddress());
            String ownerEntry = owner == null ? "NONE" : owner.getEntryPoint().toString();
            String hitKey = instruction.getAddress().toString();
            hits.add(hitKey);
            println("OPERAND_HIT\t" + instruction.getAddress() + "\t" + ownerEntry + "\t" + assembly);
            for (Instruction item : context(instruction)) {
                println("CONTEXT\t" + instruction.getAddress() + "\t"
                    + item.getAddress() + "\t" + item);
            }
            if (owner != null) owners.putIfAbsent(ownerEntry, owner);
        }

        DecompInterface decompiler = new DecompInterface();
        decompiler.openProgram(currentProgram);
        int decompiled = 0;
        int failures = 0;
        for (Map.Entry<String, Function> entry : owners.entrySet()) {
            Function function = entry.getValue();
            DecompileResults result = decompiler.decompileFunction(function, 120, monitor);
            if (!result.decompileCompleted() || result.getDecompiledFunction() == null) {
                failures++;
                println("DECOMPILE_FAILED\t" + entry.getKey() + "\t" + result.getErrorMessage());
                continue;
            }
            decompiled++;
            String code = result.getDecompiledFunction().getC();
            println("DECOMPILED_BEGIN\t" + entry.getKey() + "\tchars=" + code.length());
            println(code);
            println("DECOMPILED_END\t" + entry.getKey());
        }
        decompiler.dispose();
        List<Address> codeTargets = inspectDataCells();
        inspectCodeTargets(codeTargets);
        println("InspectScriptRegistryOperandScan.java> SUMMARY"
            + " instructionCount=" + instructionCount
            + " operandHits=" + hits.size()
            + " ownerCount=" + owners.size()
            + " decompiled=" + decompiled
            + " failures=" + failures
            + " readOnlySource=true readOnlyProject=true");
    }
}
