import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionIterator;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;
import java.util.Locale;

public class FindFilesystemFunctions extends GhidraScript {
    private static final String[] NEEDLES = {"nn::fs", "openfile", "readfile", "opendirectory", "mount"};

    @Override
    public void run() throws Exception {
        println("PROGRAM\t" + currentProgram.getName() + "\t" + currentProgram.getExecutablePath());
        int matches = 0;
        FunctionIterator functions = currentProgram.getFunctionManager().getFunctions(true);
        while (functions.hasNext()) {
            Function function = functions.next();
            String name = function.getName();
            String lower = name.toLowerCase(Locale.ROOT);
            boolean match = false;
            for (String needle : NEEDLES) {
                if (lower.contains(needle)) {
                    match = true;
                    break;
                }
            }
            if (!match) {
                continue;
            }
            matches++;
            println("FUNCTION\t" + function.getEntryPoint() + "\t" + name
                + "\tbytes=" + function.getBody().getNumAddresses());
            ReferenceIterator incoming = currentProgram.getReferenceManager()
                .getReferencesTo(function.getEntryPoint());
            while (incoming.hasNext()) {
                Reference reference = incoming.next();
                Function caller = currentProgram.getFunctionManager()
                    .getFunctionContaining(reference.getFromAddress());
                println("INCOMING\t" + reference.getFromAddress() + "\t"
                    + (caller == null ? "<no-function>" : caller.getEntryPoint()));
            }
        }
        println("SUMMARY\tfilesystem_named_functions=" + matches
            + "\timage=" + currentProgram.getExecutablePath());
    }
}
