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

public class InspectOpaqueRequestBuilder extends GhidraScript {
    private static final String[] TARGETS = {
        "0x7100210de0", "0x7100210e20", "0x710024a230",
        "0x710024a4a0", "0x710028fa10"
    };

    private String clean(String value) {
        return value.replace("\\", "\\\\").replace("\r", "\\r")
            .replace("\n", "\\n").replace("\t", "\\t");
    }

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
                println("FUNCTION_NOT_FOUND\t" + address);
                continue;
            }
            println("FUNCTION\t" + address + "\t" + function.getName()
                + "\tbytes=" + function.getBody().getNumAddresses());
            ReferenceIterator incoming = currentProgram.getReferenceManager()
                .getReferencesTo(function.getEntryPoint());
            while (incoming.hasNext()) {
                Reference reference = incoming.next();
                Function caller = currentProgram.getFunctionManager()
                    .getFunctionContaining(reference.getFromAddress());
                Instruction instruction = currentProgram.getListing()
                    .getInstructionAt(reference.getFromAddress());
                println("INCOMING\t" + reference.getFromAddress() + "\t"
                    + (caller == null ? "<no-function>" : caller.getEntryPoint()) + "\t"
                    + reference.getReferenceType() + "\t"
                    + (instruction == null ? "<no-instruction>" : instruction.toString()));
            }
            InstructionIterator instructions = currentProgram.getListing()
                .getInstructions(function.getBody(), true);
            while (instructions.hasNext()) {
                Instruction instruction = instructions.next();
                for (Reference reference : instruction.getReferencesFrom()) {
                    Address destination = reference.getToAddress();
                    if (reference.getReferenceType().isCall()) {
                        Function callee = currentProgram.getFunctionManager()
                            .getFunctionContaining(destination);
                        println("CALL\t" + instruction.getAddress() + "\t" + destination
                            + "\t" + (callee == null ? "<no-function>" : callee.getEntryPoint()));
                    }
                    Data data = currentProgram.getListing().getDataAt(destination);
                    if (data != null && data.getValue() instanceof String) {
                        println("STRING_REF\t" + instruction.getAddress() + "\t"
                            + destination + "\t" + clean((String) data.getValue()));
                    }
                }
            }
            DecompileResults result = decompiler.decompileFunction(function, 120, monitor);
            if (!result.decompileCompleted() || result.getDecompiledFunction() == null) {
                println("DECOMPILE_FAILED\t" + address + "\t" + result.getErrorMessage());
            } else {
                String code = result.getDecompiledFunction().getC();
                println("DECOMPILED_BEGIN\t" + address + "\tchars=" + code.length());
                println(code);
                println("DECOMPILED_END\t" + address);
            }
        }
        decompiler.dispose();
    }
}
