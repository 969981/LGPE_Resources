import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;

public class InspectReferenceFunctions extends GhidraScript {
    // Comparison-only leads; resolve against the exact local 1.0.2 image before interpretation.
    private static final long[] OFFSETS = {
        0x116f30L, 0x1171d0L, 0x349200L, 0x34a3d0L,
        0x520c30L, 0x520ce0L, 0x520d30L
    };

    @Override
    public void run() throws Exception {
        println("PROGRAM\t" + currentProgram.getName() + "\tbase="
            + currentProgram.getImageBase() + "\t" + currentProgram.getExecutablePath());
        DecompInterface decompiler = new DecompInterface();
        decompiler.openProgram(currentProgram);
        for (long offset : OFFSETS) {
            Address address = currentProgram.getImageBase().add(offset);
            Function function = currentProgram.getFunctionManager().getFunctionContaining(address);
            println("OFFSET\tmain+0x" + Long.toHexString(offset) + "\taddress=" + address);
            if (function == null) {
                println("FUNCTION_NOT_FOUND\t" + address);
                continue;
            }
            println("FUNCTION\t" + function.getEntryPoint() + "\t" + function.getName()
                + "\tbytes=" + function.getBody().getNumAddresses());
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
