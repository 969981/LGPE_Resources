import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;

public class DumpTargetInstructions extends GhidraScript {
    private static final String[] TARGETS = {"0x710001d3c0", "0x7100020f30", "0x7100026070"};

    @Override
    public void run() throws Exception {
        for (String target : TARGETS) {
            Address address = toAddr(target);
            Function function = currentProgram.getFunctionManager().getFunctionAt(address);
            if (function == null) {
                println("FUNCTION_NOT_FOUND\t" + target);
                continue;
            }
            println("FUNCTION_BEGIN\t" + function.getEntryPoint() + "\t" + function.getName());
            InstructionIterator instructions =
                currentProgram.getListing().getInstructions(function.getBody(), true);
            while (instructions.hasNext()) {
                Instruction instruction = instructions.next();
                println("INSN\t" + instruction.getAddress() + "\t" + instruction);
            }
            println("FUNCTION_END\t" + function.getEntryPoint());
        }
        println("SUMMARY\timage=" + currentProgram.getExecutablePath());
    }
}
