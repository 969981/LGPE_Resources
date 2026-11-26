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

public class InspectCaptureCandidates extends GhidraScript {
    private static final String[] STRING_ADDRESSES = {
        "0x7100efc8ec", "0x7100efc946", "0x7100f24d8f",
        "0x7100f24da2", "0x7100f24ed6"
    };
    private static final String[] FUNCTION_ADDRESSES = {
        "0x7100173550", "0x71000d03e0", "0x710091baa0",
        "0x710091bbf0", "0x710091c140", "0x710091cfa0"
    };

    private String clean(String value) {
        return value.replace("\\", "\\\\").replace("\r", "\\r")
            .replace("\n", "\\n").replace("\t", "\\t");
    }

    @Override
    public void run() throws Exception {
        println("PROGRAM\t" + currentProgram.getName() + "\tbase="
            + currentProgram.getImageBase() + "\t" + currentProgram.getExecutablePath());
        for (String textAddress : STRING_ADDRESSES) {
            Address address = toAddr(textAddress);
            Data data = currentProgram.getListing().getDataAt(address);
            if (data == null) {
                println("STRING_NOT_FOUND\t" + address);
                continue;
            }
            Object value = data.getValue();
            println("STRING\t" + address + "\t" + clean(String.valueOf(value)));
            ReferenceIterator refs = currentProgram.getReferenceManager().getReferencesTo(address);
            while (refs.hasNext()) {
                Reference ref = refs.next();
                Function owner = currentProgram.getFunctionManager()
                    .getFunctionContaining(ref.getFromAddress());
                println("STRING_XREF\t" + ref.getFromAddress() + "\t"
                    + (owner == null ? "<no-function>" : owner.getEntryPoint()) + "\t"
                    + (owner == null ? "<no-function>" : owner.getName()));
            }
        }

        DecompInterface decompiler = new DecompInterface();
        decompiler.openProgram(currentProgram);
        for (String target : FUNCTION_ADDRESSES) {
            Address address = toAddr(target);
            Function function = currentProgram.getFunctionManager().getFunctionContaining(address);
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
                    + (caller == null ? "<no-function>" : caller.getEntryPoint()));
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
