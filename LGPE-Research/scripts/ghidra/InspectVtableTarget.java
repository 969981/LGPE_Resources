import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;

public class InspectVtableTarget extends GhidraScript {
    private static final String[] TARGETS = {"0x7100026610"};

    @Override
    public void run() throws Exception {
        DecompInterface decompiler = new DecompInterface();
        decompiler.openProgram(currentProgram);
        for (String target : TARGETS) {
            Address entry = toAddr(target);
            Function function = currentProgram.getFunctionManager().getFunctionAt(entry);
            if (function == null) {
                disassemble(entry);
                function = createFunction(entry, null);
            }
            if (function == null) {
                println("FUNCTION_CREATE_FAILED\t" + entry);
                continue;
            }
            println("FUNCTION_BEGIN\t" + function.getEntryPoint() + "\t" + function.getName()
                + "\tbytes=" + function.getBody().getNumAddresses());
            InstructionIterator instructions =
                currentProgram.getListing().getInstructions(function.getBody(), true);
            while (instructions.hasNext()) {
                Instruction instruction = instructions.next();
                println("INSN\t" + instruction.getAddress() + "\t" + instruction);
            }
            DecompileResults result = decompiler.decompileFunction(function, 120, monitor);
            if (!result.decompileCompleted() || result.getDecompiledFunction() == null) {
                println("DECOMPILE_FAILED\t" + entry + "\t" + result.getErrorMessage());
            } else {
                println("DECOMPILED_BEGIN\t" + entry);
                println(result.getDecompiledFunction().getC());
                println("DECOMPILED_END\t" + entry);
            }
            println("FUNCTION_END\t" + function.getEntryPoint());
        }
        decompiler.dispose();
        println("SUMMARY\timage=" + currentProgram.getExecutablePath());
    }
}
