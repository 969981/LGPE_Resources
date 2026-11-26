import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;

public class InspectRandomCallers extends GhidraScript {
    private static final String[] TARGETS = {
        "0x7100145310", "0x7100145380", "0x7100524ed0", "0x7100524f00",
        "0x71004e0040", "0x71004e0120", "0x71004e0150", "0x71004e02c0",
        "0x7100cf8cb0", "0x7100cfd450", "0x7100cfda50", "0x7100d030d0",
        "0x7100ce67e0", "0x7100d004f0", "0x7100500b20",
        "0x71004fe000", "0x7100cc96a0", "0x7100cf2190", "0x7100cca2b0",
        "0x7100ce8dd0", "0x7100d079e0", "0x7100cfbdc0", "0x7100cf7030"
    };

    @Override
    public void run() throws Exception {
        println("PROGRAM\t" + currentProgram.getName() + "\tbase="
            + currentProgram.getImageBase() + "\t" + currentProgram.getExecutablePath());
        DecompInterface decompiler = new DecompInterface();
        decompiler.openProgram(currentProgram);
        for (String target : TARGETS) {
            Address address = toAddr(target);
            Function function = currentProgram.getFunctionManager().getFunctionAt(address);
            if (function == null) {
                disassemble(address);
                function = createFunction(address, null);
            }
            if (function == null) {
                println("FUNCTION_NOT_FOUND\t" + target);
                continue;
            }
            println("FUNCTION\t" + address + "\tentry=" + function.getEntryPoint()
                + "\t" + function.getName() + "\tbytes=" + function.getBody().getNumAddresses());
            ReferenceIterator incoming = currentProgram.getReferenceManager()
                .getReferencesTo(function.getEntryPoint());
            while (incoming.hasNext()) {
                Reference ref = incoming.next();
                Function caller = currentProgram.getFunctionManager()
                    .getFunctionContaining(ref.getFromAddress());
                println("INCOMING\t" + ref.getFromAddress() + "\t"
                    + (caller == null ? "<no-function>" : caller.getEntryPoint()) + "\t"
                    + (caller == null ? "<no-function>" : caller.getName()));
            }
            InstructionIterator instructions = currentProgram.getListing()
                .getInstructions(function.getBody(), true);
            while (instructions.hasNext()) {
                Instruction instruction = instructions.next();
                for (Reference ref : instruction.getReferencesFrom()) {
                    if (ref.getReferenceType().isCall()) {
                        Function callee = currentProgram.getFunctionManager()
                            .getFunctionContaining(ref.getToAddress());
                        println("CALL\t" + instruction.getAddress() + "\t"
                            + ref.getToAddress() + "\t"
                            + (callee == null ? "<no-function>" : callee.getEntryPoint())
                            + "\t" + (callee == null ? "<no-function>" : callee.getName()));
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
