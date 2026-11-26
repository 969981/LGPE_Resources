import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionIterator;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;

public class FindVirtualSlot38Calls extends GhidraScript {
    @Override
    public void run() throws Exception {
        println("PROGRAM\t" + currentProgram.getName() + "\t" + currentProgram.getExecutablePath());
        int matches = 0;
        FunctionIterator functions = currentProgram.getFunctionManager().getFunctions(true);
        while (functions.hasNext()) {
            Function function = functions.next();
            InstructionIterator instructions =
                currentProgram.getListing().getInstructions(function.getBody(), true);
            while (instructions.hasNext()) {
                Instruction instruction = instructions.next();
                String text = instruction.toString().toLowerCase();
                if (!text.startsWith("ldr ") || !text.contains("#0x38")) {
                    continue;
                }
                int space = text.indexOf(' ');
                int comma = text.indexOf(',', space + 1);
                if (comma < 0) {
                    continue;
                }
                String destination = text.substring(space + 1, comma).trim();
                Address cursor = instruction.getAddress();
                StringBuilder context = new StringBuilder();
                context.append(instruction.getAddress()).append("\t").append(instruction);
                boolean indirectCall = false;
                for (int n = 0; n < 4; n++) {
                    Instruction next = currentProgram.getListing().getInstructionAfter(cursor);
                    if (next == null || !function.getBody().contains(next.getAddress())) {
                        break;
                    }
                    cursor = next.getAddress();
                    String nextText = next.toString().toLowerCase().trim();
                    context.append("\n").append(next.getAddress()).append("\t").append(next);
                    if (nextText.startsWith("blr ") && nextText.substring(4).trim().equals(destination)) {
                        indirectCall = true;
                        break;
                    }
                    if (nextText.startsWith("bl ") || nextText.startsWith("b ")) {
                        break;
                    }
                }
                if (indirectCall) {
                    matches++;
                    println("SLOT38_CALL\tfunction=" + function.getEntryPoint() + "\t"
                        + function.getName() + "\n" + context);
                }
            }
        }
        println("SUMMARY\tslot38_indirect_calls=" + matches
            + "\timage=" + currentProgram.getExecutablePath());
    }
}
