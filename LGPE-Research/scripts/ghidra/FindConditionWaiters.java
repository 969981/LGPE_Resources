import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionIterator;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;
import java.util.HashSet;
import java.util.Set;

public class FindConditionWaiters extends GhidraScript {
    private static final String NEEDLE = "WaitConditionVariable";

    @Override
    public void run() throws Exception {
        println("PROGRAM\t" + currentProgram.getName() + "\t" + currentProgram.getExecutablePath());
        Set<Address> callers = new HashSet<>();
        FunctionIterator functions = currentProgram.getFunctionManager().getFunctions(true);
        while (functions.hasNext()) {
            Function function = functions.next();
            if (!function.getName().contains(NEEDLE)) {
                continue;
            }
            println("TARGET_FUNCTION\t" + function.getEntryPoint() + "\t" + function.getName());
            ReferenceIterator incoming = currentProgram.getReferenceManager()
                .getReferencesTo(function.getEntryPoint());
            while (incoming.hasNext()) {
                Reference reference = incoming.next();
                Function caller = currentProgram.getFunctionManager()
                    .getFunctionContaining(reference.getFromAddress());
                if (caller == null) {
                    println("CALLER\t" + reference.getFromAddress() + "\t<no-function>");
                    continue;
                }
                println("CALLER\t" + reference.getFromAddress() + "\t" + caller.getEntryPoint()
                    + "\t" + caller.getName());
                callers.add(caller.getEntryPoint());
            }
        }

        DecompInterface decompiler = new DecompInterface();
        decompiler.openProgram(currentProgram);
        for (Address address : callers) {
            Function caller = currentProgram.getFunctionManager().getFunctionAt(address);
            if (caller == null) {
                continue;
            }
            println("CALLER_FUNCTION\t" + caller.getEntryPoint() + "\t" + caller.getName()
                + "\tbytes=" + caller.getBody().getNumAddresses());
            InstructionIterator instructions =
                currentProgram.getListing().getInstructions(caller.getBody(), true);
            while (instructions.hasNext()) {
                Instruction instruction = instructions.next();
                if (instruction.toString().contains("#0x360")) {
                    println("QUEUE_OFFSET_INSN\t" + instruction.getAddress() + "\t" + instruction);
                }
            }
            DecompileResults result = decompiler.decompileFunction(caller, 120, monitor);
            if (!result.decompileCompleted() || result.getDecompiledFunction() == null) {
                println("DECOMPILE_FAILED\t" + caller.getEntryPoint() + "\t" + result.getErrorMessage());
            } else {
                String code = result.getDecompiledFunction().getC();
                println("DECOMPILED_BEGIN\t" + caller.getEntryPoint() + "\tchars=" + code.length());
                println(code);
                println("DECOMPILED_END\t" + caller.getEntryPoint());
            }
        }
        decompiler.dispose();
        println("SUMMARY\twait_target=" + NEEDLE + "\tcallers=" + callers.size()
            + "\timage=" + currentProgram.getExecutablePath());
    }
}
