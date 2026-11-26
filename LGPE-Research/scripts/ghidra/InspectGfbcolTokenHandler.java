import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import ghidra.program.model.listing.Listing;
import ghidra.program.model.listing.Data;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.security.MessageDigest;
import java.util.Locale;

/** Read-only exact-build inspection of the helper called from six col_* labels. */
public class InspectGfbcolTokenHandler extends GhidraScript {
    private static final String EXPECTED_MAIN_SHA256 =
        "1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8";
    private static final long EXPECTED_BASE = 0x7100000000L;
    private static final String EXPECTED_NCA_ID = "2b7730a9e56498bbafac2002d4908c6b";
    private static final long HANDLER = 0x710000b660L;
    private static final long[] CALL_SITES = {
        0x710024f48cL, 0x710024f4e4L, 0x710024f534L,
        0x710024f584L, 0x710024f5d4L, 0x710024f624L
    };

    @Override
    public void run() throws Exception {
        String executable = currentProgram.getExecutablePath();
        String normalized = executable == null ? "" : executable.trim().replace('\\', '/');
        if (currentProgram.getImageBase().getOffset() != EXPECTED_BASE
            || !normalized.toLowerCase(Locale.ROOT).contains(EXPECTED_NCA_ID)
            || !normalized.toLowerCase(Locale.ROOT).endsWith("/0/main")) {
            throw new IllegalStateException("not the recorded LGPE Pikachu 1.0.2 main");
        }
        String sourceHashBefore = sha256(executable.trim());
        if (!EXPECTED_MAIN_SHA256.equals(sourceHashBefore)) {
            throw new IllegalStateException("source main SHA-256 mismatch: " + sourceHashBefore);
        }

        Address target = toAddr(HANDLER);
        Function function = currentProgram.getFunctionManager().getFunctionAt(target);
        if (function == null) throw new IllegalStateException("handler function missing at " + target);
        println("PROGRAM\t" + currentProgram.getName() + "\tbase=0x"
            + Long.toHexString(currentProgram.getImageBase().getOffset()) + "\t" + normalized);
        println("SOURCE\tmain_sha256=" + sourceHashBefore + "\timage=Let's Go Pikachu 1.0.2");
        println("FUNCTION\t" + relative(function.getEntryPoint()) + "\t" + function.getName()
            + "\tbytes=" + function.getBody().getNumAddresses());

        int incomingCount = 0;
        boolean[] expectedSitesSeen = new boolean[CALL_SITES.length];
        ReferenceIterator incoming = currentProgram.getReferenceManager().getReferencesTo(target);
        Listing listing = currentProgram.getListing();
        while (incoming.hasNext()) {
            Reference reference = incoming.next();
            incomingCount++;
            Address from = reference.getFromAddress();
            Instruction instruction = listing.getInstructionAt(from);
            Function caller = currentProgram.getFunctionManager().getFunctionContaining(from);
            for (int i = 0; i < CALL_SITES.length; i++) {
                if (from.getOffset() == CALL_SITES[i]) expectedSitesSeen[i] = true;
            }
            println("TARGET_XREF\tfrom=" + relative(from) + "\ttype="
                + reference.getReferenceType() + "\towner="
                + (caller == null ? "NONE" : relative(caller.getEntryPoint()))
                + "\tinstruction=" + (instruction == null ? "NONE" : instruction.toString()));
        }
        int expectedSites = 0;
        int contextInstructions = 0;
        for (int i = 0; i < CALL_SITES.length; i++) {
            if (expectedSitesSeen[i]) expectedSites++;
            println("EXPECTED_CALLSITE\t" + relative(toAddr(CALL_SITES[i]))
                + "\tghidra_reference=" + expectedSitesSeen[i]);

            Address site = toAddr(CALL_SITES[i]);
            Address begin = site.subtract(0x30);
            Address end = site.add(0x10);
            Instruction instruction = listing.getInstructionAt(begin);
            if (instruction == null) instruction = listing.getInstructionAfter(begin);
            while (instruction != null && instruction.getAddress().compareTo(end) <= 0) {
                Address instructionAddress = instruction.getAddress();
                Function owner = currentProgram.getFunctionManager()
                    .getFunctionContaining(instructionAddress);
                println("CALL_CONTEXT\tcallsite=" + relative(site)
                    + "\taddress=" + relative(instructionAddress)
                    + "\towner=" + (owner == null ? "NONE" : relative(owner.getEntryPoint()))
                    + "\tflow=" + instruction.getFlowType()
                    + "\tassembly=" + clean(instruction.toString()));
                for (Reference reference : instruction.getReferencesFrom()) {
                    if (reference.getReferenceType().isFlow()) {
                        println("CALL_CONTEXT_FLOW\tcallsite=" + relative(site)
                            + "\tfrom=" + relative(instructionAddress)
                            + "\tto=" + relative(reference.getToAddress())
                            + "\ttype=" + reference.getReferenceType());
                    }
                }
                contextInstructions++;
                instruction = listing.getInstructionAfter(instructionAddress);
            }
        }

        InstructionIterator instructions = listing.getInstructions(function.getBody(), true);
        int instructionCount = 0;
        int directCallCount = 0;
        while (instructions.hasNext()) {
            Instruction instruction = instructions.next();
            instructionCount++;
            for (Reference reference : instruction.getReferencesFrom()) {
                if (reference.getReferenceType().isCall()) {
                    directCallCount++;
                    Function callee = currentProgram.getFunctionManager()
                        .getFunctionContaining(reference.getToAddress());
                    println("HANDLER_CALL\tfrom=" + relative(instruction.getAddress())
                        + "\tto=" + relative(reference.getToAddress()) + "\tcallee="
                        + (callee == null ? "NONE" : relative(callee.getEntryPoint()))
                        + "\tname=" + (callee == null ? "NONE" : callee.getName()));
                }
                Data data = listing.getDataAt(reference.getToAddress());
                if (data != null && data.getValue() instanceof String) {
                    println("HANDLER_STRING_REF\tfrom=" + relative(instruction.getAddress())
                        + "\tto=" + relative(reference.getToAddress()) + "\tvalue="
                        + clean((String) data.getValue()));
                }
            }
        }

        DecompInterface decompiler = new DecompInterface();
        if (!decompiler.openProgram(currentProgram)) {
            throw new IllegalStateException("Ghidra decompiler failed to open exact-build program");
        }
        DecompileResults result = decompiler.decompileFunction(function, 180, monitor);
        if (!result.decompileCompleted() || result.getDecompiledFunction() == null) {
            decompiler.dispose();
            throw new IllegalStateException("handler decompile failed: " + result.getErrorMessage());
        }
        String source = result.getDecompiledFunction().getC();
        println("DECOMPILED_BEGIN\t" + relative(function.getEntryPoint()) + "\tchars=" + source.length());
        println(source);
        println("DECOMPILED_END\t" + relative(function.getEntryPoint()));
        decompiler.dispose();

        String sourceHashAfter = sha256(executable.trim());
        if (!sourceHashBefore.equals(sourceHashAfter)) {
            throw new IllegalStateException("source main changed during read-only inspection");
        }
        println("SUMMARY\tmain_sha256=" + sourceHashAfter + "\thandler=" + relative(target)
            + "\tincoming_references=" + incomingCount + "\texpected_call_sites="
            + expectedSites + "/" + CALL_SITES.length + "\tinstructions=" + instructionCount
            + "\tdirect_calls=" + directCallCount + "\tcontext_instructions="
            + contextInstructions
            + "\tsourceHashUnchanged=true\treadOnly=true\tsemantics=UNKNOWN");
    }

    private String relative(Address address) {
        return "main+0x" + Long.toHexString(address.getOffset() - EXPECTED_BASE);
    }

    private String clean(String value) {
        return value.replace("\\", "\\\\").replace("\r", "\\r")
            .replace("\n", "\\n").replace("\t", "\\t");
    }

    private String sha256(String path) throws Exception {
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        try (InputStream input = Files.newInputStream(Paths.get(path))) {
            byte[] buffer = new byte[1 << 20];
            int count;
            while ((count = input.read(buffer)) >= 0) digest.update(buffer, 0, count);
        }
        StringBuilder value = new StringBuilder();
        for (byte b : digest.digest()) value.append(String.format("%02x", b & 0xff));
        return value.toString();
    }
}
