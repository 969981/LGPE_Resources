import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.Data;
import ghidra.program.model.listing.DataIterator;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionIterator;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;
import java.util.Locale;

public class InspectRngCaptureSymbols extends GhidraScript {
    private static final String[] NEEDLES = {
        "random", "rng", "personality", "shiny", "encount", "capture", "catch", "spawn"
    };

    private boolean matches(String text) {
        String lower = text.toLowerCase(Locale.ROOT);
        for (String needle : NEEDLES) {
            if (lower.contains(needle)) {
                return true;
            }
        }
        return lower.matches(".*(^|[^a-z0-9])pid([^a-z0-9]|$).*")
            || lower.contains("_pid") || lower.contains("pid_");
    }

    private String clean(String value) {
        return value.replace("\\", "\\\\").replace("\r", "\\r")
            .replace("\n", "\\n").replace("\t", "\\t");
    }

    @Override
    public void run() throws Exception {
        println("PROGRAM\t" + currentProgram.getName() + "\tbase="
            + currentProgram.getImageBase() + "\t" + currentProgram.getExecutablePath());
        int strings = 0;
        int stringReferences = 0;
        DataIterator dataIterator = currentProgram.getListing().getDefinedData(true);
        while (dataIterator.hasNext()) {
            Data data = dataIterator.next();
            Object value = data.getValue();
            if (!(value instanceof String) || !matches((String) value)) {
                continue;
            }
            strings++;
            println("STRING\t" + data.getAddress() + "\t" + clean((String) value));
            ReferenceIterator references = currentProgram.getReferenceManager()
                .getReferencesTo(data.getAddress());
            while (references.hasNext()) {
                Reference reference = references.next();
                Function owner = currentProgram.getFunctionManager()
                    .getFunctionContaining(reference.getFromAddress());
                println("STRING_XREF\t" + reference.getFromAddress() + "\t"
                    + (owner == null ? "<no-function>" : owner.getEntryPoint()) + "\t"
                    + (owner == null ? "<no-function>" : owner.getName()));
                stringReferences++;
            }
        }

        int functions = 0;
        int functionReferences = 0;
        FunctionIterator functionIterator = currentProgram.getFunctionManager().getFunctions(true);
        while (functionIterator.hasNext()) {
            Function function = functionIterator.next();
            if (!matches(function.getName())) {
                continue;
            }
            functions++;
            println("FUNCTION\t" + function.getEntryPoint() + "\t" + function.getName()
                + "\texternal=" + function.isExternal());
            ReferenceIterator incoming = currentProgram.getReferenceManager()
                .getReferencesTo(function.getEntryPoint());
            while (incoming.hasNext()) {
                Reference reference = incoming.next();
                Function caller = currentProgram.getFunctionManager()
                    .getFunctionContaining(reference.getFromAddress());
                println("FUNCTION_XREF\t" + reference.getFromAddress() + "\t"
                    + (caller == null ? "<no-function>" : caller.getEntryPoint()) + "\t"
                    + (caller == null ? "<no-function>" : caller.getName()));
                functionReferences++;
            }
        }
        println("SUMMARY\tmatched_strings=" + strings + "\tstring_xrefs=" + stringReferences
            + "\tmatched_functions=" + functions + "\tfunction_xrefs=" + functionReferences);
    }
}
