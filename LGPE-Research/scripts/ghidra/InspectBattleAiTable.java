import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;
import java.util.LinkedHashSet;
import java.util.Set;

public class InspectBattleAiTable extends GhidraScript {
    private static final String PAGE_BASE = "0x71015d2000";
    private static final long TABLE_START = 0x71015d2c00L;
    private static final int TABLE_POINTERS = 7;

    @Override
    public void run() throws Exception {
        println("PROGRAM\t" + currentProgram.getName() + "\tbase="
            + currentProgram.getImageBase() + "\t" + currentProgram.getExecutablePath());
        Set<String> owners = new LinkedHashSet<>();
        report(toAddr(PAGE_BASE), owners);
        for (int i = 0; i < TABLE_POINTERS; i++) {
            report(toAddr(TABLE_START + i * 8L), owners);
        }
        owners.add("0x7100674ae0");
        owners.add("0x7100670450");
        owners.add("0x710066ff20");
        owners.add("0x710066fb20");
        owners.add("0x71006744b0");
        owners.add("0x7100673ff0");
        owners.add("0x7100673380");
        owners.add("0x71006749b0");
        owners.add("0x7100a771d0");
        DecompInterface decompiler = new DecompInterface();
        decompiler.openProgram(currentProgram);
        for (String ownerText : owners) {
            Function function = currentProgram.getFunctionManager().getFunctionAt(toAddr(ownerText));
            if (function == null) {
                println("FUNCTION_NOT_FOUND\t" + ownerText);
                continue;
            }
            println("FUNCTION\t" + function.getEntryPoint() + "\t" + function.getName()
                + "\tbytes=" + function.getBody().getNumAddresses());
            InstructionIterator instructions = currentProgram.getListing()
                .getInstructions(function.getBody(), true);
            while (instructions.hasNext()) {
                Instruction instruction = instructions.next();
                if (function.getEntryPoint().toString().equals("710066fb20")
                    && instruction.getAddress().getOffset() >= 0x710066fc00L
                    && instruction.getAddress().getOffset() <= 0x710066fe20L) {
                    println("AMX_COMPACT_INSN\t" + instruction.getAddress()
                        + "\t" + instruction);
                }
                for (Reference reference : instruction.getReferencesFrom()) {
                    if (reference.getReferenceType().isCall()) {
                        Function callee = currentProgram.getFunctionManager()
                            .getFunctionContaining(reference.getToAddress());
                        println("CALL\t" + instruction.getAddress() + "\t"
                            + reference.getToAddress() + "\t"
                            + (callee == null ? "<no-function>" : callee.getEntryPoint())
                            + "\t" + (callee == null ? "<no-function>" : callee.getName()));
                    }
                }
            }
            DecompileResults result = decompiler.decompileFunction(function, 120, monitor);
            if (!result.decompileCompleted() || result.getDecompiledFunction() == null) {
                println("DECOMPILE_FAILED\t" + function.getEntryPoint()
                    + "\t" + result.getErrorMessage());
            } else {
                String code = result.getDecompiledFunction().getC();
                println("DECOMPILED_BEGIN\t" + function.getEntryPoint()
                    + "\tchars=" + code.length());
                println(code);
                println("DECOMPILED_END\t" + function.getEntryPoint());
            }
        }
        decompiler.dispose();
    }

    private void report(Address target, Set<String> owners) {
        ReferenceIterator references = currentProgram.getReferenceManager().getReferencesTo(target);
        while (references.hasNext()) {
            Reference reference = references.next();
            Function owner = currentProgram.getFunctionManager()
                .getFunctionContaining(reference.getFromAddress());
            Instruction instruction = currentProgram.getListing()
                .getInstructionAt(reference.getFromAddress());
            String ownerEntry = owner == null ? "<no-function>" : owner.getEntryPoint().toString();
            println("REF\t" + reference.getFromAddress() + "\t" + target + "\t"
                + reference.getReferenceType() + "\t" + ownerEntry + "\t"
                + (instruction == null ? "<no-instruction>" : instruction.toString()));
            if (owner != null) {
                owners.add(ownerEntry);
            }
        }
    }
}
