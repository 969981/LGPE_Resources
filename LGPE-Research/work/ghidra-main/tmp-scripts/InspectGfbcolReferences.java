import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Data;
import ghidra.program.model.listing.DataIterator;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import ghidra.program.model.mem.MemoryBlock;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;
import java.nio.charset.StandardCharsets;
import java.util.LinkedHashMap;
import java.util.Locale;
import java.util.Map;

public class InspectGfbcolReferences extends GhidraScript {
    private static final String[] NEEDLES = {
        "gfbcol", ".gfbcol", "gfbmdl", ".gfbmdl", "gfbanm", ".gfbanm",
        "ptcl", ".ptcl", "collision", "collider", "gflx"
    };

    @Override
    public void run() throws Exception {
        println("PROGRAM\t" + currentProgram.getName() + "\t" + currentProgram.getExecutablePath());
        println("IMAGE_BASE\t" + currentProgram.getImageBase());
        Map<String, Function> functions = new LinkedHashMap<>();
        int matchedStrings = 0;
        int xrefCount = 0;

        DataIterator iterator = currentProgram.getListing().getDefinedData(true);
        while (iterator.hasNext()) {
            Data data = iterator.next();
            Object value = data.getValue();
            if (!(value instanceof String)) continue;
            String text = (String) value;
            String lower = text.toLowerCase(Locale.ROOT);
            boolean match = false;
            for (String needle : NEEDLES) {
                if (lower.contains(needle)) { match = true; break; }
            }
            if (!match) continue;
            matchedStrings++;
            println("STRING\t" + data.getAddress() + "\t" + escape(text));
            ReferenceIterator refs = currentProgram.getReferenceManager().getReferencesTo(data.getAddress());
            while (refs.hasNext()) {
                Reference ref = refs.next();
                Function function = currentProgram.getFunctionManager().getFunctionContaining(ref.getFromAddress());
                String entry = function == null ? "<no-function>" : function.getEntryPoint().toString();
                println("STRING_XREF\t" + data.getAddress() + "\t" + ref.getFromAddress()
                    + "\t" + ref.getReferenceType() + "\t" + entry);
                if (function != null) functions.put(entry, function);
                xrefCount++;
            }
        }

        for (MemoryBlock block : currentProgram.getMemory().getBlocks()) {
            if (!block.isInitialized() || block.getSize() > Integer.MAX_VALUE) continue;
            byte[] bytes = new byte[(int) block.getSize()];
            currentProgram.getMemory().getBytes(block.getStart(), bytes);
            String ascii = new String(bytes, StandardCharsets.ISO_8859_1).toLowerCase(Locale.ROOT);
            String wide = new String(bytes, StandardCharsets.UTF_16LE).toLowerCase(Locale.ROOT);
            for (String needle : NEEDLES) {
                int index = ascii.indexOf(needle);
                while (index >= 0) {
                    println("RAW_ASCII\t" + block.getName() + "\t" + block.getStart().add(index) + "\t" + needle);
                    index = ascii.indexOf(needle, index + 1);
                }
                index = wide.indexOf(needle);
                while (index >= 0) {
                    println("RAW_UTF16LE\t" + block.getName() + "\t" + block.getStart().add(index * 2L) + "\t" + needle);
                    index = wide.indexOf(needle, index + 1);
                }
            }
        }

        for (Function function : functions.values()) {
            println("FUNCTION\t" + function.getEntryPoint() + "\t" + function.getName()
                + "\tbytes=" + function.getBody().getNumAddresses());
            ReferenceIterator incoming = currentProgram.getReferenceManager().getReferencesTo(function.getEntryPoint());
            while (incoming.hasNext()) {
                Reference ref = incoming.next();
                Function caller = currentProgram.getFunctionManager().getFunctionContaining(ref.getFromAddress());
                println("CALLER\t" + function.getEntryPoint() + "\t" + ref.getFromAddress()
                    + "\t" + (caller == null ? "<no-function>" : caller.getEntryPoint()));
            }
            InstructionIterator instructions = currentProgram.getListing().getInstructions(function.getBody(), true);
            while (instructions.hasNext()) {
                Instruction instruction = instructions.next();
                for (Reference ref : instruction.getReferencesFrom()) {
                    if (!ref.getReferenceType().isCall()) continue;
                    Function callee = currentProgram.getFunctionManager().getFunctionContaining(ref.getToAddress());
                    println("CALLEE\t" + function.getEntryPoint() + "\t" + instruction.getAddress()
                        + "\t" + ref.getToAddress() + "\t" + (callee == null ? "<no-function>" : callee.getEntryPoint()));
                }
            }
        }
        println("SUMMARY\tdefined_strings=" + matchedStrings + "\txrefs=" + xrefCount
            + "\tfunctions=" + functions.size() + "\tprogram=" + currentProgram.getName());
    }

    private static String escape(String value) {
        return value.replace("\\", "\\\\").replace("\r", "\\r")
            .replace("\n", "\\n").replace("\t", "\\t");
    }
}
