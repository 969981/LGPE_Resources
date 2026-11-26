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
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/** Exact-build static candidates only; run with -noanalysis -readOnly. */
public class InspectCaptureFlowCandidates extends GhidraScript {
    private static final long BASE = 0x7100000000L;
    private static final String EXPECTED_SHA256 =
        "1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8";
    private static final Pattern IMAGE_ADDRESS = Pattern.compile("(?i)(?:0x)?(71[0-9a-f]{8})");
    private int temporaryFunctions;
    private int decompiled;

    private String offset(Address address) {
        return String.format("main+0x%x", address.getOffset() - BASE);
    }

    private String pointer(long value) {
        return value >= BASE && value < BASE + 0x2000000L
            ? offset(toAddr(value)) : String.format("0x%x", value);
    }

    // The display is intentionally address-normalized, not compilable source.
    private String normalize(String text) {
        Matcher matcher = IMAGE_ADDRESS.matcher(text);
        StringBuffer result = new StringBuffer();
        while (matcher.find()) {
            long value = Long.parseUnsignedLong(matcher.group(1), 16);
            matcher.appendReplacement(result, Matcher.quoteReplacement(pointer(value)));
        }
        matcher.appendTail(result);
        return result.toString();
    }

    private String sourceHash(String path) throws Exception {
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        try (InputStream stream = Files.newInputStream(Paths.get(path))) {
            byte[] buffer = new byte[1024 * 1024];
            int count;
            while ((count = stream.read(buffer)) != -1) {
                digest.update(buffer, 0, count);
            }
        }
        return HexFormat.of().formatHex(digest.digest());
    }

    private void incoming(Address address) {
        int count = 0;
        ReferenceIterator references = currentProgram.getReferenceManager().getReferencesTo(address);
        while (references.hasNext()) {
            Reference reference = references.next();
            Function owner = getFunctionContaining(reference.getFromAddress());
            Instruction instruction = getInstructionAt(reference.getFromAddress());
            println("XREF\ttarget=" + offset(address) + "\tfrom="
                + offset(reference.getFromAddress()) + "\ttype=" + reference.getReferenceType()
                + "\towner=" + (owner == null ? "NONE" : offset(owner.getEntryPoint()))
                + "\tinstruction=" + (instruction == null ? "NONE" : normalize(instruction.toString())));
            count++;
        }
        println("XREF_COUNT\t" + offset(address) + "\t" + count);
    }

    private void table(long globalOffset, int qwords) throws Exception {
        Address global = toAddr(BASE + globalOffset);
        long tablePointer = getLong(global);
        println("GLOBAL\t" + offset(global) + "\tvalue=" + pointer(tablePointer));
        incoming(global);
        for (int index = 0; index < qwords; index++) {
            Address cell = toAddr(tablePointer + index * 8L);
            MemoryBlock block = currentProgram.getMemory().getBlock(cell);
            if (block == null || !block.isInitialized()) {
                throw new IllegalStateException("uninitialized table cell " + offset(cell));
            }
            println("CELL\t" + offset(cell) + "\tvalue=" + pointer(getLong(cell))
                + "\tblock=" + block.getName() + "\twritable=" + block.isWrite()
                + "\texecutable=" + block.isExecute());
        }
    }

    private void inspect(long targetOffset, DecompInterface decompiler) throws Exception {
        Address address = toAddr(BASE + targetOffset);
        incoming(address);
        Function function = getFunctionAt(address);
        boolean temporary = function == null;
        if (temporary) {
            if (getInstructionAt(address) == null) {
                println("NO_DEFINED_INSTRUCTION\t" + offset(address));
                return;
            }
            // Read-only headless mode discards these analysis aids at process exit.
            function = createFunction(address, null);
            if (function == null) {
                throw new IllegalStateException("cannot create temporary candidate " + offset(address));
            }
            temporaryFunctions++;
        }
        println("FUNCTION\t" + offset(address) + "\tbytes=" + function.getBody().getNumAddresses()
            + "\ttemporaryCandidate=" + temporary);
        InstructionIterator instructions = currentProgram.getListing().getInstructions(function.getBody(), true);
        while (instructions.hasNext()) {
            Instruction instruction = instructions.next();
            // Retain all instructions for byte-copy/field-offset verification.
            println("INS\t" + offset(instruction.getAddress()) + "\t"
                + HexFormat.of().formatHex(instruction.getBytes()) + "\t"
                + normalize(instruction.toString()));
            if (instruction.getFlowType().isCall() || "br".equals(instruction.getMnemonicString())) {
                println("FLOW\t" + offset(instruction.getAddress()) + "\t"
                    + normalize(instruction.toString()));
            }
        }
        DecompileResults result = decompiler.decompileFunction(function, 120, monitor);
        if (!result.decompileCompleted() || result.getDecompiledFunction() == null) {
            throw new IllegalStateException("decompilation failed " + offset(address) + ": " + result.getErrorMessage());
        }
        println("DECOMPILED_BEGIN\t" + offset(address) + "\taddress-normalized-display");
        println(normalize(result.getDecompiledFunction().getC()));
        println("DECOMPILED_END\t" + offset(address));
        decompiled++;
    }

    @Override
    public void run() throws Exception {
        if (!"12.2".equals(Application.getApplicationVersion())) {
            throw new IllegalStateException("Ghidra 12.2 required: " + Application.getApplicationVersion());
        }
        String executable = currentProgram.getExecutablePath().trim();
        String normalizedPath = executable.replace('\\', '/').toLowerCase(Locale.ROOT);
        if (currentProgram.getImageBase().getOffset() != BASE
            || !normalizedPath.contains("2b7730a9e56498bbafac2002d4908c6b")
            || !normalizedPath.endsWith("/0/main")) {
            throw new IllegalStateException("not the pinned Pikachu 1.0.2 main");
        }
        String hash = sourceHash(executable);
        if (!EXPECTED_SHA256.equals(hash)) {
            throw new IllegalStateException("source SHA-256 mismatch: " + hash);
        }
        println("GUARD\tSHA256=" + hash + "\tbase=main+0x0\tprogram=" + currentProgram.getName());
        println("LIMITATION\tDATA pointer targets are indirect candidates; no runtime dispatch or RNG/capture semantics inferred.");
        table(0x15ff078L, 26);
        table(0x15ff088L, 26);
        DecompInterface decompiler = new DecompInterface();
        if (!decompiler.openProgram(currentProgram)) {
            throw new IllegalStateException("decompiler could not open program");
        }
        try {
            for (long target : new long[] {
                0x1a61e0L, 0x1a64c0L, 0x1aae40L, 0x28e750L,
                0x28fa10L, 0x28fd60L, 0x28fed0L, 0x292640L,
                0x28e7d0L, 0x28e7e0L, 0x28e7f0L, 0x28eff0L,
                0x290200L, 0x290210L, 0x290420L, 0x292280L,
                0x28eb60L, 0x28ee10L
            }) {
                inspect(target, decompiler);
            }
        } finally {
            decompiler.dispose();
        }
        if (!EXPECTED_SHA256.equals(sourceHash(executable))) {
            throw new IllegalStateException("source hash changed during run");
        }
        println("SUMMARY\tdecompiled=" + decompiled + "\ttemporaryCandidates=" + temporaryFunctions
            + "\tsourceHashUnchanged=true\tdiscardRequired=true");
    }
}
