import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Data;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

public class InspectScriptFunctionRegistry extends GhidraScript {
    private static final String PAGE_BASE = "0x710153c000";
    private static final String TABLE_START = "0x710153c870";
    private static final int TABLE_BYTES = 0x90;
    private static final String[] OWNERS = {
        "0x71001a61d0", "0x71001a7b70", "0x71001a8710", "0x71001abe40"
    };

    private String clean(String value) {
        return value.replace("\\", "\\\\").replace("\r", "\\r")
            .replace("\n", "\\n").replace("\t", "\\t");
    }

    private void reportContext(Instruction instruction) {
        List<Instruction> context = new ArrayList<>();
        Instruction cursor = instruction;
        for (int i = 0; i < 6; i++) {
            Instruction previous = currentProgram.getListing()
                .getInstructionBefore(cursor.getAddress());
            if (previous == null) {
                break;
            }
            context.add(0, previous);
            cursor = previous;
        }
        context.add(instruction);
        cursor = instruction;
        for (int i = 0; i < 6; i++) {
            Instruction next = currentProgram.getListing()
                .getInstructionAfter(cursor.getAddress());
            if (next == null) {
                break;
            }
            context.add(next);
            cursor = next;
        }
        println("CONTEXT_BEGIN\t" + instruction.getAddress());
        for (Instruction item : context) {
            println("CONTEXT\t" + item.getAddress() + "\t" + item);
        }
        println("CONTEXT_END\t" + instruction.getAddress());
    }

    private void report(Address target, Set<String> emitted) {
        ReferenceIterator references = currentProgram.getReferenceManager().getReferencesTo(target);
        while (references.hasNext()) {
            Reference reference = references.next();
            Function owner = currentProgram.getFunctionManager()
                .getFunctionContaining(reference.getFromAddress());
            Instruction instruction = currentProgram.getListing()
                .getInstructionAt(reference.getFromAddress());
            Data sourceData = currentProgram.getListing().getDataAt(reference.getFromAddress());
            String key = reference.getFromAddress() + "\t" + target;
            if (!emitted.add(key)) {
                continue;
            }
            String kind = instruction != null ? "CODE_REF"
                : owner != null ? "FUNCTION_DATA_REF" : "NON_CODE_REF";
            println(kind + "\t"
                + reference.getFromAddress() + "\t" + target + "\t"
                + reference.getReferenceType() + "\t"
                + (owner == null ? "<no-function>" : owner.getEntryPoint()) + "\t"
                + (instruction == null ? "<no-instruction>" : instruction.toString()) + "\t"
                + (sourceData == null ? "<no-defined-data>" : sourceData.getDataType().getName()));
            if (owner == null && instruction != null) {
                reportContext(instruction);
            }
        }
    }

    @Override
    public void run() throws Exception {
        println("PROGRAM\t" + currentProgram.getName() + "\tbase="
            + currentProgram.getImageBase() + "\t" + currentProgram.getExecutablePath());
        Set<String> emitted = new HashSet<>();
        Address pageBase = toAddr(PAGE_BASE);
        report(pageBase, emitted);

        Address table = toAddr(TABLE_START);
        for (int offset = 0; offset < TABLE_BYTES; offset += 4) {
            report(table.add(offset), emitted);
        }

        DecompInterface decompiler = new DecompInterface();
        decompiler.openProgram(currentProgram);
        for (String target : OWNERS) {
            Address entry = toAddr(target);
            Function function = currentProgram.getFunctionManager().getFunctionAt(entry);
            if (function == null) {
                println("FUNCTION_NOT_FOUND\t" + entry);
                continue;
            }
            println("FUNCTION\t" + entry + "\t" + function.getName()
                + "\tbytes=" + function.getBody().getNumAddresses());
            InstructionIterator instructions = currentProgram.getListing()
                .getInstructions(function.getBody(), true);
            while (instructions.hasNext()) {
                Instruction instruction = instructions.next();
                for (Reference reference : instruction.getReferencesFrom()) {
                    if (reference.getReferenceType().isCall()) {
                        Function callee = currentProgram.getFunctionManager()
                            .getFunctionContaining(reference.getToAddress());
                        println("CALL\t" + instruction.getAddress() + "\t"
                            + reference.getToAddress() + "\t"
                            + (callee == null ? "<no-function>" : callee.getEntryPoint()));
                    }
                    Data data = currentProgram.getListing().getDataAt(reference.getToAddress());
                    if (data != null && data.getValue() instanceof String) {
                        println("STRING_REF\t" + instruction.getAddress() + "\t"
                            + reference.getToAddress() + "\t" + clean((String) data.getValue()));
                    }
                }
            }
            DecompileResults result = decompiler.decompileFunction(function, 120, monitor);
            if (!result.decompileCompleted() || result.getDecompiledFunction() == null) {
                println("DECOMPILE_FAILED\t" + entry + "\t" + result.getErrorMessage());
            } else {
                String code = result.getDecompiledFunction().getC();
                println("DECOMPILED_BEGIN\t" + entry + "\tchars=" + code.length());
                println(code);
                println("DECOMPILED_END\t" + entry);
            }
        }
        decompiler.dispose();
        println("SUMMARY\tpageBase=" + pageBase + "\ttableStart=" + table
            + "\ttableBytes=" + TABLE_BYTES + "\txrefs=" + emitted.size());
    }
}
