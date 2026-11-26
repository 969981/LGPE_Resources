import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;

public class InspectLoaderFunctions extends GhidraScript {
    private static final String[] TARGETS = {
        "0x710012a730",
        "0x71001d3730",
        "0x71001d7210",
        "0x710073b330",
        "0x7100776e60",
        "0x7100135960",
        "0x71001afb60",
        "0x71000a6140",
        "0x71001d88b0",
        "0x710071d800",
        "0x710013b650",
        "0x71000adc70",
        "0x71000a63a0"
    };

    @Override
    public void run() throws Exception {
        DecompInterface decompiler = new DecompInterface();
        decompiler.openProgram(currentProgram);
        for (String target : TARGETS) {
            Address address = toAddr(target);
            Function function = currentProgram.getFunctionManager().getFunctionAt(address);
            if (function == null) {
                function = currentProgram.getFunctionManager().getFunctionContaining(address);
            }
            if (function == null) {
                println("FUNCTION_NOT_FOUND	" + target);
                continue;
            }
            println("FUNCTION	" + target + "	" + function.getEntryPoint()
                + "	" + function.getName()
                + "	bytes=" + function.getBody().getNumAddresses());

            ReferenceIterator incoming =
                currentProgram.getReferenceManager().getReferencesTo(function.getEntryPoint());
            while (incoming.hasNext()) {
                Reference reference = incoming.next();
                Function caller = currentProgram.getFunctionManager()
                    .getFunctionContaining(reference.getFromAddress());
                println("INCOMING	" + reference.getFromAddress()
                    + "	" + reference.getReferenceType()
                    + "	" + (caller == null ? "<no-function>" : caller.getEntryPoint()));
            }

            InstructionIterator instructions =
                currentProgram.getListing().getInstructions(function.getBody(), true);
            while (instructions.hasNext()) {
                Instruction instruction = instructions.next();
                for (Reference reference : instruction.getReferencesFrom()) {
                    if (reference.getReferenceType().isCall()) {
                        Function callee = currentProgram.getFunctionManager()
                            .getFunctionContaining(reference.getToAddress());
                        println("CALL	" + instruction.getAddress()
                            + "	" + reference.getToAddress()
                            + "	" + (callee == null ? "<no-function>" : callee.getEntryPoint()));
                    }
                }
            }

            DecompileResults result = decompiler.decompileFunction(function, 60, monitor);
            if (!result.decompileCompleted() || result.getDecompiledFunction() == null) {
                println("DECOMPILE_FAILED	" + function.getEntryPoint()
                    + "	" + result.getErrorMessage());
                continue;
            }
            String c = result.getDecompiledFunction().getC();
            println("DECOMPILED_BEGIN	" + function.getEntryPoint());
            println(c.length() > 16000 ? c.substring(0, 16000) : c);
            println("DECOMPILED_END	" + function.getEntryPoint());
        }
        decompiler.dispose();
        println("SUMMARY	program=" + currentProgram.getName()
            + "	image=" + currentProgram.getExecutablePath());
    }
}
