import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Data;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.Reference;

public class InspectCaptureSymbolTables extends GhidraScript {
    private static final String[] WINDOWS = {
        "0x710153bb80", "0x710153c800", "0x710153c940"
    };

    @Override
    public void run() throws Exception {
        println("PROGRAM\t" + currentProgram.getName() + "\tbase="
            + currentProgram.getImageBase() + "\t" + currentProgram.getExecutablePath());
        for (String startText : WINDOWS) {
            Address start = toAddr(startText);
            println("WINDOW\t" + start + "\tbytes=0x100");
            for (int offset = 0; offset < 0x100; offset += 8) {
                Address slot = start.add(offset);
                long raw = currentProgram.getMemory().getLong(slot);
                String rawHex = String.format("0x%016x", raw);
                Data data = currentProgram.getListing().getDataAt(slot);
                String type = data == null ? "<undefined>" : data.getDataType().getName();
                String value = data == null ? "" : String.valueOf(data.getValue());
                println("QWORD\t" + slot + "\t" + rawHex + "\t" + type + "\t" + value);
                for (Reference ref : currentProgram.getReferenceManager().getReferencesFrom(slot)) {
                    Function target = currentProgram.getFunctionManager()
                        .getFunctionContaining(ref.getToAddress());
                    println("OUTREF\t" + slot + "\t" + ref.getToAddress() + "\t"
                        + (target == null ? "<no-function>" : target.getEntryPoint())
                        + "\t" + (target == null ? "<no-function>" : target.getName()));
                }
            }
        }
        println("SUMMARY\timage=" + currentProgram.getExecutablePath());
    }
}
