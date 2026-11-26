import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;

public class InspectTradeNetworkFunctions extends GhidraScript {
    private static final String[] TARGETS = {
        "0x7100117040", "0x7100344370", "0x7100344450", "0x71008f8d70",
        "0x71004d9030", "0x71004d9450", "0x71004d94d0", "0x71004d94e0",
        "0x71004d9570", "0x71004da820", "0x710051c110", "0x710051e790",
        "0x710051e810"
    };

    @Override
    public void run() throws Exception {
        println("PROGRAM\t" + currentProgram.getName() + "\tbase="
            + currentProgram.getImageBase() + "\t" + currentProgram.getExecutablePath());
        DecompInterface decompiler = new DecompInterface();
        decompiler.openProgram(currentProgram);
        for (String target : TARGETS) {
            Address address = toAddr(target);
            Function function = currentProgram.getFunctionManager().getFunctionContaining(address);
            if (function == null) {
                println("FUNCTION_NOT_FOUND\t" + target);
                continue;
            }
            println("FUNCTION\t" + address + "\tentry=" + function.getEntryPoint()
                + "\t" + function.getName() + "\tbytes=" + function.getBody().getNumAddresses());
            ReferenceIterator incoming =
                currentProgram.getReferenceManager().getReferencesTo(function.getEntryPoint());
            while (incoming.hasNext()) {
                Reference reference = incoming.next();
                Function caller = currentProgram.getFunctionManager()
                    .getFunctionContaining(reference.getFromAddress());
                println("INCOMING\t" + reference.getFromAddress() + "\t"
                    + (caller == null ? "<no-function>" : caller.getEntryPoint()));
            }
            InstructionIterator instructions =
                currentProgram.getListing().getInstructions(function.getBody(), true);
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
                }
            }
            DecompileResults result = decompiler.decompileFunction(function, 120, monitor);
            if (!result.decompileCompleted() || result.getDecompiledFunction() == null) {
                println("DECOMPILE_FAILED\t" + function.getEntryPoint() + "\t"
                    + result.getErrorMessage());
            } else {
                String code = result.getDecompiledFunction().getC();
                println("DECOMPILED_BEGIN\t" + function.getEntryPoint() + "\tchars="
                    + code.length());
                println(code);
                println("DECOMPILED_END\t" + function.getEntryPoint());
            }
        }
        decompiler.dispose();
        println("SUMMARY\timage=" + currentProgram.getExecutablePath());
    }
}
