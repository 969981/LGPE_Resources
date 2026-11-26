import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.mem.MemoryBlock;

public class InspectResourceVtables extends GhidraScript {
    private static final long[] GLOBALS = {
        0x71015fb348L, 0x71015fb380L, 0x71015fb030L, 0x71015fb058L,
        0x71015fad30L, 0x71015facd8L
    };
    private static final long[] FUNCTIONS = {0x71000238e0L, 0x7100023990L};

    @Override
    public void run() throws Exception {
        println("PROGRAM\t" + currentProgram.getName() + "\t" + currentProgram.getExecutablePath());
        for (long rawAddress : GLOBALS) {
            Address address = toAddr(rawAddress);
            MemoryBlock globalBlock = currentProgram.getMemory().getBlock(address);
            if (globalBlock == null || !globalBlock.isInitialized()) {
                println("GLOBAL_UNMAPPED\t" + address);
                continue;
            }
            long value = currentProgram.getMemory().getLong(address);
            Address target = toAddr(value);
            println("GLOBAL\t" + address + "\tvalue=" + target + "\tmapped="
                + currentProgram.getMemory().contains(target));
            MemoryBlock targetBlock = currentProgram.getMemory().getBlock(target);
            if (targetBlock == null || !targetBlock.isInitialized()) {
                println("TABLE_UNINITIALIZED\t" + address + "\t" + target);
                continue;
            }
            for (int offset = 0; offset < 0x200; offset += 8) {
                Address slot = target.add(offset);
                MemoryBlock slotBlock = currentProgram.getMemory().getBlock(slot);
                if (slotBlock == null || !slotBlock.isInitialized()) {
                    break;
                }
                long candidateValue = currentProgram.getMemory().getLong(slot);
                Address candidate = toAddr(candidateValue);
                Function function = currentProgram.getFunctionManager().getFunctionContaining(candidate);
                if (offset >= 0x10 && offset <= 0x70) {
                    println("TABLE_ENTRY\t" + address + "\t" + slot + "\tvalue=" + candidate
                        + "\t" + (function == null ? "<no-function>" : function.getName()));
                }
                for (long targetFunction : FUNCTIONS) {
                    if (candidateValue == targetFunction) {
                        println("TABLE_MATCH\t" + address + "\t" + slot + "\t" + candidate
                            + "\tfunction=" + (function == null ? "<none>" : function.getEntryPoint()));
                    }
                }
                if (function != null && offset < 0x80) {
                    println("TABLE_FUNCTION\t" + address + "\t" + slot + "\t" + candidate
                        + "\t" + function.getName());
                }
            }
        }
        println("SUMMARY\timage=" + currentProgram.getExecutablePath());
    }
}
