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

public class InspectEncounterConsumer extends GhidraScript {
    private static final String[] TARGETS = {
        "0x710013b650", "0x710013bfa0", "0x710013d020"
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
            Address entry = toAddr(target);
            Function function = currentProgram.getFunctionManager().getFunctionAt(entry);
            if (function == null) {
                println("FUNCTION_NOT_FOUND\t" + target);
                continue;
            }
            println("FUNCTION\t" + entry + "\t" + function.getName()
                + "\tbytes=" + function.getBody().getNumAddresses());

            ReferenceIterator incoming = currentProgram.getReferenceManager()
                .getReferencesTo(entry);
            while (incoming.hasNext()) {
                Reference ref = incoming.next();
                Function caller = currentProgram.getFunctionManager()
                    .getFunctionContaining(ref.getFromAddress());
                println("INCOMING\t" + ref.getFromAddress() + "\t" + ref.getReferenceType()
                    + "\t" + (caller == null ? "<no-function>" : caller.getEntryPoint()));
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
                    Data data = currentProgram.getListing().getDataAt(ref.getToAddress());
                    if (data != null && data.getValue() instanceof String) {
                        println("STRING_REF\t" + instruction.getAddress() + "\t"
                            + ref.getToAddress() + "\t" + clean((String) data.getValue()));
                    }
                }
            }

            DecompileResults result = decompiler.decompileFunction(function, 120, monitor);
            if (!result.decompileCompleted() || result.getDecompiledFunction() == null) {
                println("DECOMPILE_FAILED\t" + entry + "\t" + result.getErrorMessage());
            } else {
                String code = result.getDecompiledFunction().getC();
                println("DECOMPILED_BEGIN\t" + entry + "\tchars=" + code.length());
                println(code);
                println("DECOMPILED_END\t" + entry);
            }
        }

        decompiler.dispose();
        println("SUMMARY\timage=" + currentProgram.getExecutablePath());
    }
}
