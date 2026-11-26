import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;
import java.util.ArrayList;
import java.util.List;

public class InspectDataReferences extends GhidraScript {
    private static final String[] TARGETS = {
        "0x7100efdbe8",
        "0x7100f02955",
        "0x7100f02a59",
        "0x7100f1f4ab",
        "0x7100f1fd13"
    };

    @Override
    public void run() throws Exception {
        for (String target : TARGETS) {
            Address address = toAddr(target);
            ReferenceIterator references =
                currentProgram.getReferenceManager().getReferencesTo(address);
            while (references.hasNext()) {
                Reference reference = references.next();
                Function function = currentProgram.getFunctionManager()
                    .getFunctionContaining(reference.getFromAddress());
                println("STRING_XREF	" + address
                    + "	" + reference.getFromAddress()
                    + "	" + reference.getReferenceType()
                    + "	" + (function == null ? "<no-function>" : function.getEntryPoint()));
                if (function == null) {
                    continue;
                }
                List<String> before = new ArrayList<>();
                InstructionIterator iterator =
                    currentProgram.getListing().getInstructions(function.getBody(), true);
                boolean found = false;
                while (iterator.hasNext()) {
                    Instruction instruction = iterator.next();
                    if (instruction.getAddress().equals(reference.getFromAddress())) {
                        for (String line : before) {
                            println("INSN	" + line);
                        }
                        println("INSN	" + instruction.getAddress() + "	" + instruction);
                        for (int n = 0; n < 3 && iterator.hasNext(); n++) {
                            Instruction next = iterator.next();
                            println("INSN	" + next.getAddress() + "	" + next);
                        }
                        found = true;
                        break;
                    }
                    before.add(instruction.getAddress() + "	" + instruction);
                    if (before.size() > 8) {
                        before.remove(0);
                    }
                }
                if (!found) {
                    println("INSTRUCTION_NOT_FOUND	" + reference.getFromAddress());
                }
            }
        }
        println("SUMMARY	program=" + currentProgram.getName()
            + "	image=" + currentProgram.getExecutablePath());
    }
}
