import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;

public class InspectEncounterLoader extends GhidraScript {
    private static final String ENTRY = "0x710012a730";
    private static final String[] STRING_XREFS = {"0x710012b8a0", "0x710012b908"};

    @Override
    public void run() throws Exception {
        Address entry = toAddr(ENTRY);
        Function function = currentProgram.getFunctionManager().getFunctionAt(entry);
        if (function == null) {
            println("FUNCTION_NOT_FOUND\t" + ENTRY);
            return;
        }

        println("PROGRAM\t" + currentProgram.getName() + "\t" + currentProgram.getExecutablePath());
        println("FUNCTION\t" + function.getEntryPoint() + "\tbytes=" + function.getBody().getNumAddresses());
        ReferenceIterator incoming = currentProgram.getReferenceManager().getReferencesTo(entry);
        while (incoming.hasNext()) {
            Reference reference = incoming.next();
            Function caller = currentProgram.getFunctionManager().getFunctionContaining(reference.getFromAddress());
            println("INCOMING\t" + reference.getFromAddress() + "\t" + reference.getReferenceType()
                + "\t" + (caller == null ? "<no-function>" : caller.getEntryPoint()));
        }

        for (String location : STRING_XREFS) {
            Address address = toAddr(location);
            Instruction instruction = currentProgram.getListing().getInstructionAt(address);
            println("STRING_XREF_INSN\t" + address + "\t"
                + (instruction == null ? "<no-instruction>" : instruction.toString()));
            if (instruction != null) {
                for (Reference reference : instruction.getReferencesFrom()) {
                    println("STRING_XREF_TARGET\t" + address + "\t" + reference.getToAddress()
                        + "\t" + reference.getReferenceType());
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
