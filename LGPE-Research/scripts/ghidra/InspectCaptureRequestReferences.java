import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.Listing;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;
import java.util.ArrayList;
import java.util.List;

public class InspectCaptureRequestReferences extends GhidraScript {
    private static final String[] TARGETS = {
        "0x71001a61e0", "0x71001a64c0", "0x710028fa10",
        "0x710028fd60", "0x710028fed0", "0x710028f910",
        "0x710028fc10", "0x7100292570"
    };

    private void reportContext(Instruction instruction) {
        Listing listing = currentProgram.getListing();
        List<Instruction> context = new ArrayList<>();
        Instruction cursor = instruction;
        for (int i = 0; i < 24; i++) {
            Instruction previous = listing.getInstructionBefore(cursor.getAddress());
            if (previous == null) {
                break;
            }
            context.add(0, previous);
            cursor = previous;
        }
        context.add(instruction);
        cursor = instruction;
        for (int i = 0; i < 16; i++) {
            Instruction next = listing.getInstructionAfter(cursor.getAddress());
            if (next == null) {
                break;
            }
            context.add(next);
            cursor = next;
        }
        println("CONTEXT_BEGIN\t" + instruction.getAddress());
        for (Instruction item : context) {
            println("CONTEXT\t" + item.getAddress() + "\t" + item);
        }
        println("CONTEXT_END\t" + instruction.getAddress());
    }

    @Override
    public void run() throws Exception {
        println("PROGRAM\t" + currentProgram.getName() + "\tbase="
            + currentProgram.getImageBase() + "\t" + currentProgram.getExecutablePath());
        for (String targetText : TARGETS) {
            Address target = toAddr(targetText);
            println("TARGET_BEGIN\t" + target);
            ReferenceIterator references = currentProgram.getReferenceManager()
                .getReferencesTo(target);
            while (references.hasNext()) {
                Reference reference = references.next();
                Address from = reference.getFromAddress();
                Function owner = currentProgram.getFunctionManager()
                    .getFunctionContaining(from);
                Instruction instruction = currentProgram.getListing().getInstructionAt(from);
                println("REF\t" + from + "\t" + target + "\t"
                    + reference.getReferenceType() + "\t"
                    + (owner == null ? "<no-function>" : owner.getEntryPoint()) + "\t"
                    + (instruction == null ? "<no-instruction>" : instruction.toString()));
                if (owner == null && instruction != null) {
                    Instruction cursor = instruction;
                    for (int i = 0; i < 512; i++) {
                        Instruction previous = currentProgram.getListing()
                            .getInstructionBefore(cursor.getAddress());
                        if (previous == null) {
                            break;
                        }
                        String text = previous.toString();
                        if (text.startsWith("stp x29,x30") || text.startsWith("mov x29,sp")) {
                            println("FRAME_CANDIDATE\t" + previous.getAddress() + "\t" + text);
                        }
                        cursor = previous;
                    }
                    reportContext(instruction);
                }
            }
            println("TARGET_END\t" + target);
        }
    }
}
