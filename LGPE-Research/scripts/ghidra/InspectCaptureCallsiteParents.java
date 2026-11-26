import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;

public class InspectCaptureCallsiteParents extends GhidraScript {
    private static final String[] CANDIDATE_ENTRIES = {
        "0x710028a5e0", "0x7100325054", "0x71003277a4",
        "0x7100327e68", "0x7100328328"
    };
    private static final String[] CALLSITES = {
        "0x710028ab24", "0x710028ac1c", "0x7100325390",
        "0x7100327ae0", "0x7100327f94", "0x7100328444"
    };

    private boolean containsCallsite(Function function) {
        for (String callsite : CALLSITES) {
            if (function.getBody().contains(toAddr(callsite))) {
                return true;
            }
        }
        return false;
    }

    @Override
    public void run() throws Exception {
        println("PROGRAM\t" + currentProgram.getName() + "\tbase="
            + currentProgram.getImageBase() + "\t" + currentProgram.getExecutablePath());
        DecompInterface decompiler = new DecompInterface();
        decompiler.openProgram(currentProgram);
        for (String candidate : CANDIDATE_ENTRIES) {
            Address entry = toAddr(candidate);
            Function function = currentProgram.getFunctionManager().getFunctionAt(entry);
            if (function == null) {
                disassemble(entry);
                function = createFunction(entry, null);
            }
            if (function == null) {
                println("FUNCTION_NOT_FOUND\t" + entry);
                continue;
            }
            println("CANDIDATE_FUNCTION\t" + entry + "\tname=" + function.getName()
                + "\tbytes=" + function.getBody().getNumAddresses()
                + "\tcontainsCallsite=" + containsCallsite(function));
            InstructionIterator instructions = currentProgram.getListing()
                .getInstructions(function.getBody(), true);
            while (instructions.hasNext()) {
                Instruction instruction = instructions.next();
                for (String callsite : CALLSITES) {
                    if (instruction.getAddress().equals(toAddr(callsite))) {
                        println("MATCHED_CALLSITE\t" + instruction.getAddress()
                            + "\t" + instruction);
                    }
                }
            }
            if (!containsCallsite(function)) {
                continue;
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
    }
}
