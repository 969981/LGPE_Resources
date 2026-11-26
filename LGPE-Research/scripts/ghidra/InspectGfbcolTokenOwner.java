import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.framework.Application;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import ghidra.program.model.mem.MemoryBlock;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.security.MessageDigest;
import java.util.HexFormat;
import java.util.Locale;

/** Temporary exact-build function-boundary probe for six col_* callsites. */
public class InspectGfbcolTokenOwner extends GhidraScript {
    private static final long BASE = 0x7100000000L;
    private static final long ENTRY = BASE + 0x24f460L;
    private static final long HANDLER = BASE + 0xb660L;
    private static final String EXPECTED_SHA256 =
        "1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8";
    private static final String EXPECTED_NCA_ID = "2b7730a9e56498bbafac2002d4908c6b";
    private static final long[] CALLS = {
        BASE + 0x24f48cL, BASE + 0x24f4e4L, BASE + 0x24f534L,
        BASE + 0x24f584L, BASE + 0x24f5d4L, BASE + 0x24f624L
    };

    private String offset(Address address) {
        return "main+0x" + Long.toHexString(address.getOffset() - BASE);
    }

    private String hash(String path) throws Exception {
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        try (InputStream input = Files.newInputStream(Paths.get(path))) {
            byte[] buffer = new byte[1 << 20];
            int count;
            while ((count = input.read(buffer)) >= 0) digest.update(buffer, 0, count);
        }
        return HexFormat.of().formatHex(digest.digest());
    }

    private String clean(String value) {
        return value.replace("\\", "\\\\").replace("\r", "\\r")
            .replace("\n", "\\n").replace("\t", "\\t");
    }

    @Override
    public void run() throws Exception {
        if (!"12.2".equals(Application.getApplicationVersion())) {
            throw new IllegalStateException("Ghidra 12.2 required: " + Application.getApplicationVersion());
        }
        String executable = currentProgram.getExecutablePath().trim();
        String normalized = executable.replace('\\', '/').toLowerCase(Locale.ROOT);
        if (currentProgram.getImageBase().getOffset() != BASE
            || !normalized.contains(EXPECTED_NCA_ID)
            || !normalized.endsWith("/0/main")) {
            throw new IllegalStateException("not the pinned Let's Go Pikachu 1.0.2 main");
        }
        String before = hash(executable);
        if (!EXPECTED_SHA256.equals(before)) {
            throw new IllegalStateException("main SHA-256 mismatch: " + before);
        }

        Address entry = toAddr(ENTRY);
        Function existing = currentProgram.getFunctionManager().getFunctionAt(entry);
        if (existing != null) {
            throw new IllegalStateException("expected undefined candidate entry, found " + existing.getName());
        }
        Instruction first = currentProgram.getListing().getInstructionAt(entry);
        if (first == null || !"sub".equals(first.getMnemonicString())
            || !first.toString().contains("sp,sp,#0x40")) {
            throw new IllegalStateException("candidate entry prologue mismatch at " + offset(entry));
        }

        int entryXrefs = 0;
        ReferenceIterator entryReferences = currentProgram.getReferenceManager().getReferencesTo(entry);
        while (entryReferences.hasNext()) {
            Reference reference = entryReferences.next();
            Address from = reference.getFromAddress();
            Function owner = currentProgram.getFunctionManager().getFunctionContaining(from);
            Instruction instruction = currentProgram.getListing().getInstructionAt(from);
            println("ENTRY_XREF\tfrom=" + offset(from) + "\ttype=" + reference.getReferenceType()
                + "\towner=" + (owner == null ? "NONE" : offset(owner.getEntryPoint()))
                + "\tinstruction=" + (instruction == null ? "NONE" : clean(instruction.toString())));
            if ("DATA".equals(reference.getReferenceType().toString())) {
                for (long delta = -0x20; delta <= 0x30; delta += 8) {
                    Address cell = from.add(delta);
                    MemoryBlock block = currentProgram.getMemory().getBlock(cell);
                    if (block == null || !block.isInitialized()) continue;
                    long value = getLong(cell);
                    println("ENTRY_DATA_WINDOW\tcell=" + offset(cell)
                        + "\tvalue=0x" + Long.toHexString(value)
                        + "\tblock=" + block.getName()
                        + "\twritable=" + block.isWrite()
                        + "\texecutable=" + block.isExecute());
                }
            }
            entryXrefs++;
        }

        Function candidate = createFunction(entry, null);
        if (candidate == null) throw new IllegalStateException("could not create temporary candidate function");
        int callSitesPresent = 0;
        for (long value : CALLS) {
            Address call = toAddr(value);
            if (!candidate.getBody().contains(call)) {
                throw new IllegalStateException("candidate boundary excludes observed callsite " + offset(call));
            }
            boolean reachesHandler = false;
            for (Reference reference : currentProgram.getReferenceManager().getReferencesFrom(call)) {
                if (reference.getReferenceType().isCall()
                    && reference.getToAddress().getOffset() == HANDLER) reachesHandler = true;
            }
            if (!reachesHandler) throw new IllegalStateException("expected call edge missing at " + offset(call));
            callSitesPresent++;
        }

        println("GUARD\tgame=Let's Go Pikachu 1.0.2\tmain_sha256=" + before
            + "\tbase=0x7100000000\tread_only=true");
        println("CANDIDATE_FUNCTION\tentry=" + offset(candidate.getEntryPoint())
            + "\tbytes=" + candidate.getBody().getNumAddresses()
            + "\tmin=" + offset(candidate.getBody().getMinAddress())
            + "\tmax=" + offset(candidate.getBody().getMaxAddress())
            + "\ttemporary_boundary=true");

        InstructionIterator instructions = currentProgram.getListing()
            .getInstructions(candidate.getBody(), true);
        int instructionCount = 0;
        while (instructions.hasNext()) {
            Instruction instruction = instructions.next();
            instructionCount++;
            println("INS\t" + offset(instruction.getAddress()) + "\t"
                + HexFormat.of().formatHex(instruction.getBytes()) + "\t"
                + clean(instruction.toString()));
        }

        DecompInterface decompiler = new DecompInterface();
        if (!decompiler.openProgram(currentProgram)) {
            throw new IllegalStateException("decompiler could not open pinned program");
        }
        DecompileResults result = decompiler.decompileFunction(candidate, 180, monitor);
        decompiler.dispose();
        if (!result.decompileCompleted() || result.getDecompiledFunction() == null) {
            throw new IllegalStateException("candidate decompile failed: " + result.getErrorMessage());
        }
        String code = result.getDecompiledFunction().getC();
        println("DECOMPILED_BEGIN\t" + offset(entry) + "\tchars=" + code.length());
        println(code);
        println("DECOMPILED_END\t" + offset(entry));

        String after = hash(executable);
        if (!before.equals(after)) throw new IllegalStateException("source main changed during inspection");
        println("SUMMARY\tmain_sha256=" + after + "\tentry=" + offset(entry)
            + "\tcall_sites=" + callSitesPresent + "/" + CALLS.length
            + "\tinstructions=" + instructionCount
            + "\tentry_xrefs=" + entryXrefs
            + "\ttemporary_boundary=true\tsourceHashUnchanged=true"
            + "\treadOnly=true\tsemantics=UNKNOWN");
    }
}
