import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.Data;
import ghidra.program.model.listing.DataIterator;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;
import java.util.Locale;

public class InspectAmxLoaderStrings extends GhidraScript {
    private static final String[] NEEDLES = {
        ".amx", "amx", "ai_script", "btl_ai", "battle_ai", "pawn"
    };

    @Override
    public void run() throws Exception {
        println("PROGRAM\t" + currentProgram.getName() + "\tbase="
            + currentProgram.getImageBase() + "\t" + currentProgram.getExecutablePath());
        int matched = 0;
        int xrefs = 0;
        DataIterator iterator = currentProgram.getListing().getDefinedData(true);
        while (iterator.hasNext()) {
            Data data = iterator.next();
            Object value = data.getValue();
            if (!(value instanceof String)) {
                continue;
            }
            String text = (String) value;
            String lower = text.toLowerCase(Locale.ROOT);
            boolean found = false;
            for (String needle : NEEDLES) {
                if (lower.contains(needle)) {
                    found = true;
                    break;
                }
            }
            if (!found) {
                continue;
            }
            matched++;
            println("STRING\t" + data.getAddress() + "\t" + escape(text));
            ReferenceIterator references = currentProgram.getReferenceManager()
                .getReferencesTo(data.getAddress());
            while (references.hasNext()) {
                Reference reference = references.next();
                Function function = currentProgram.getFunctionManager()
                    .getFunctionContaining(reference.getFromAddress());
                println("XREF\t" + reference.getFromAddress() + "\t"
                    + (function == null ? "<no-function>" : function.getEntryPoint().toString())
                    + "\t" + (function == null ? "<no-function>" : function.getName()));
                xrefs++;
            }
        }
        println("SUMMARY\tmatched_strings=" + matched + "\txrefs=" + xrefs
            + "\tprogram=" + currentProgram.getName());
    }

    private static String escape(String value) {
        return value.replace("\\", "\\\\").replace("\r", "\\r")
            .replace("\n", "\\n").replace("\t", "\\t");
    }
}
