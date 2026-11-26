import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.Data;
import ghidra.program.model.listing.DataIterator;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

public class FindSaveCaptureParkStrings extends GhidraScript {
    private static final String[] NEEDLES = {
        "gopark", "go park", "go_park", "go-park", "pokemonhome",
        "capture", "catch", "save", "savemanager", "storage", "transfer"
    };

    @Override
    public void run() throws Exception {
        int matched = 0;
        int xrefs = 0;
        DataIterator iterator = currentProgram.getListing().getDefinedData(true);
        while (iterator.hasNext()) {
            Data data = iterator.next();
            Object value = data.getValue();
            if (!(value instanceof String)) {
                continue;
            }
            String text = ((String) value).toLowerCase(Locale.ROOT);
            List<String> labels = new ArrayList<>();
            for (String needle : NEEDLES) {
                if (text.contains(needle)) {
                    labels.add(needle.replace(' ', '_').replace('-', '_'));
                }
            }
            if (labels.isEmpty()) {
                continue;
            }
            matched++;
            println("MATCH\t" + data.getAddress() + "\tlength=" + text.length()
                + "\tlabels=" + String.join(",", labels));
            ReferenceIterator references =
                currentProgram.getReferenceManager().getReferencesTo(data.getAddress());
            while (references.hasNext()) {
                Reference reference = references.next();
                Function function = currentProgram.getFunctionManager()
                    .getFunctionContaining(reference.getFromAddress());
                println("XREF\t" + reference.getFromAddress() + "\t"
                    + (function == null ? "<no-function>" : function.getEntryPoint()) + "\t"
                    + (function == null ? "<no-function>" : function.getName()));
                xrefs++;
            }
        }
        println("SUMMARY\tmatched_strings=" + matched + "\txrefs=" + xrefs
            + "\tprogram=" + currentProgram.getName() + "\timage="
            + currentProgram.getExecutablePath());
    }
}
