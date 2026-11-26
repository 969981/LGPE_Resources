import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Data;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import ghidra.program.model.symbol.Reference;

public class InspectAmxResourceHelpers extends GhidraScript {
    private static final String[] TARGETS = {
        "0x71000a63a0", "0x71000adc70", "0x710001dd60",
        "0x710001e080", "0x7100179030"
    };

    private static String clean(String value) {
        return value.replace("\\", "\\\\").replace("\r", "\\r")
            .replace("\n", "\\n").replace("\t", "\\t");
    }

    @Override
    public void run() throws Exception {
        println("PROGRAM\t" + currentProgram.getName() + "\tbase="
            + currentProgram.getImageBase() + "\t" + currentProgram.getExecutablePath());
        DecompInterface decompiler = new DecompInterface();
        decompiler.openProgram(currentProgram);
        for (String targetText : TARGETS) {
            Address entry = toAddr(targetText);
            Function function = currentProgram.getFunctionManager().getFunctionAt(entry);
            if (function == null) {
                function = currentProgram.getFunctionManager().getFunctionContaining(entry);
            }
            if (function == null) {
                println("FUNCTION_NOT_FOUND\t" + entry);
                continue;
            }
            println("FUNCTION\t" + function.getEntryPoint() + "\t" + function.getName()
                + "\tbytes=" + function.getBody().getNumAddresses());
            InstructionIterator instructions = currentProgram.getListing()
                .getInstructions(function.getBody(), true);
            while (instructions.hasNext()) {
                Instruction instruction = instructions.next();
                for (Reference reference : instruction.getReferencesFrom()) {
                    if (reference.getReferenceType().isCall()) {
                        Function callee = currentProgram.getFunctionManager()
                            .getFunctionContaining(reference.getToAddress());
                        println("CALL\t" + instruction.getAddress() + "\t"
                            + reference.getToAddress() + "\t"
                            + (callee == null ? "<no-function>" : callee.getEntryPoint())
                            + "\t" + (callee == null ? "<no-function>" : callee.getName()));
                    }
                    Data data = currentProgram.getListing().getDataAt(reference.getToAddress());
                    if (data != null && data.getValue() instanceof String) {
                        println("STRING_REF\t" + instruction.getAddress() + "\t"
                            + reference.getToAddress() + "\t"
                            + clean((String) data.getValue()));
                    }
                }
            }
            DecompileResults result = decompiler.decompileFunction(function, 120, monitor);
            if (!result.decompileCompleted() || result.getDecompiledFunction() == null) {
                println("DECOMPILE_FAILED\t" + function.getEntryPoint()
                    + "\t" + result.getErrorMessage());
            } else {
                String code = result.getDecompiledFunction().getC();
                println("DECOMPILED_BEGIN\t" + function.getEntryPoint()
                    + "\tchars=" + code.length());
                println(code);
                println("DECOMPILED_END\t" + function.getEntryPoint());
            }
        }
        decompiler.dispose();
    }
}
