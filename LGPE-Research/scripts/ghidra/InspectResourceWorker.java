import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;

public class InspectResourceWorker extends GhidraScript {
    private static final String[] ENTRIES = {
        "0x710001d3c0", "0x710001d430", "0x71000238e0", "0x7100023990",
        "0x710001d1c0", "0x710001dd60", "0x710001e080", "0x7100020540", "0x7100020e80", "0x7100020f30", "0x71000218f0",
        "0x71000231a0", "0x7100023680", "0x71000237c0", "0x7100023880", "0x7100023a20",
        "0x71000276e0",
        "0x71000241e0", "0x7100024d70", "0x7100026070", "0x71006777e0"
    };

    @Override
    public void run() throws Exception {
        println("PROGRAM\t" + currentProgram.getName() + "\t" + currentProgram.getExecutablePath());
        DecompInterface decompiler = new DecompInterface();
        decompiler.openProgram(currentProgram);
        for (String entryText : ENTRIES) {
            Address entry = toAddr(entryText);
            Function function = currentProgram.getFunctionManager().getFunctionAt(entry);
            if (function == null) {
                println("FUNCTION_NOT_FOUND\t" + entryText);
                continue;
            }

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

            DecompileResults result = decompiler.decompileFunction(function, 120, monitor);
            if (!result.decompileCompleted() || result.getDecompiledFunction() == null) {
                println("DECOMPILE_FAILED\t" + function.getEntryPoint() + "\t" + result.getErrorMessage());
            } else {
                String code = result.getDecompiledFunction().getC();
                println("DECOMPILED_BEGIN\t" + function.getEntryPoint() + "\tchars=" + code.length());
                println(code);
                println("DECOMPILED_END\t" + function.getEntryPoint());
            }
        }
        decompiler.dispose();
        println("SUMMARY\tfunctions=" + ENTRIES.length + "\timage=" + currentProgram.getExecutablePath());
    }
}
