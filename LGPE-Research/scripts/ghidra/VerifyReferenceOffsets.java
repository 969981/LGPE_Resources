import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;

public class VerifyReferenceOffsets extends GhidraScript {
    private static final long[] OFFSETS = {
        0x116f30L, 0x1171d0L, 0x349200L, 0x34a3d0L,
        0x520c30L, 0x520ce0L, 0x520d30L
    };

    @Override
    public void run() throws Exception {
        println("PROGRAM\t" + currentProgram.getName()
            + "\timageBase=" + currentProgram.getImageBase()
            + "\texecutable=" + currentProgram.getExecutablePath());
        for (long offset : OFFSETS) {
            Address address = currentProgram.getImageBase().add(offset);
            println("OFFSET_MAP\tmain+0x" + Long.toHexString(offset)
                + "\t" + address
                + "\tmemory=" + currentProgram.getMemory().contains(address));
            Function function = currentProgram.getFunctionManager().getFunctionContaining(address);
            if (function == null) {
                println("FUNCTION_NOT_FOUND\t" + address);
                continue;
            }
            println("FUNCTION\t" + address + "\t" + function.getEntryPoint()
                + "\t" + function.getName()
                + "\tbytes=" + function.getBody().getNumAddresses());
            ReferenceIterator incoming = currentProgram.getReferenceManager()
                .getReferencesTo(function.getEntryPoint());
            while (incoming.hasNext()) {
                Reference reference = incoming.next();
                Function caller = currentProgram.getFunctionManager()
                    .getFunctionContaining(reference.getFromAddress());
                println("INCOMING\t" + reference.getFromAddress()
                    + "\t" + reference.getReferenceType()
                    + "\t" + (caller == null ? "<no-function>" : caller.getEntryPoint()));
            }
            InstructionIterator instructions = currentProgram.getListing()
                .getInstructions(function.getBody(), true);
            int printed = 0;
            while (instructions.hasNext() && printed < 12) {
                Instruction instruction = instructions.next();
                if (instruction.getAddress().compareTo(address) < 0) {
                    continue;
                }
                println("INSN\t" + instruction.getAddress() + "\t" + instruction);
                printed++;
            }
            if (printed == 0) {
                println("NO_INSTRUCTIONS_AT_OR_AFTER_OFFSET\t" + address);
            }
        }
    }
}
