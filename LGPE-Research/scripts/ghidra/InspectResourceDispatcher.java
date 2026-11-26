import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;

public class InspectResourceDispatcher extends GhidraScript {
    private static final String ENTRY = "0x71000276e0";

    @Override
    public void run() throws Exception {
        Address entry = toAddr(ENTRY);
        Function function = currentProgram.getFunctionManager().getFunctionAt(entry);
        if (function == null) {
            println("FUNCTION_NOT_FOUND\t" + ENTRY);
            return;
        }

        println("PROGRAM\t" + currentProgram.getName() + "\t" + currentProgram.getExecutablePath());
        println("FUNCTION\t" + function.getEntryPoint() + "\t" + function.getName()
            + "\tbytes=" + function.getBody().getNumAddresses());
        ReferenceIterator incoming = currentProgram.getReferenceManager().getReferencesTo(entry);
        while (incoming.hasNext()) {
            Reference reference = incoming.next();
            Function caller = currentProgram.getFunctionManager().getFunctionContaining(reference.getFromAddress());
            println("INCOMING\t" + reference.getFromAddress() + "\t" + reference.getReferenceType()
                + "\t" + (caller == null ? "<no-function>" : caller.getEntryPoint()));
        }

        InstructionIterator instructions = currentProgram.getListing().getInstructions(function.getBody(), true);
        while (instructions.hasNext()) {
            Instruction instruction = instructions.next();
            for (Reference reference : instruction.getReferencesFrom()) {
                if (reference.getReferenceType().isCall()) {
                    Function callee = currentProgram.getFunctionManager().getFunctionContaining(reference.getToAddress());
                    println("CALL\t" + instruction.getAddress() + "\t" + reference.getToAddress()
                        + "\t" + (callee == null ? "<no-function>" : callee.getEntryPoint()));
                }
            }
        }

        DecompInterface decompiler = new DecompInterface();
        decompiler.openProgram(currentProgram);
        DecompileResults result = decompiler.decompileFunction(function, 120, monitor);
        if (!result.decompileCompleted() || result.getDecompiledFunction() == null) {
            println("DECOMPILE_FAILED\t" + result.getErrorMessage());
        } else {
            String code = result.getDecompiledFunction().getC();
            println("DECOMPILED_BEGIN\tchars=" + code.length());
            println(code);
            println("DECOMPILED_END\t" + function.getEntryPoint());
        }
        decompiler.dispose();
        println("SUMMARY\tmain=" + ENTRY + "\timage=" + currentProgram.getExecutablePath());
    }
}
