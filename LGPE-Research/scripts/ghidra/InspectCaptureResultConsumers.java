import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.framework.Application;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
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

/** Read-only exact-build trace of the capture-result getter's direct consumers. */
public class InspectCaptureResultConsumers extends GhidraScript {
    private static final long BASE = 0x7100000000L;
    private static final String EXPECTED_SHA256 =
        "1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8";
    private static final long[] TARGETS = {
        0x28eb60L, 0x2f5a40L, 0x2f5ec0L, 0x2f5f60L,
        0x2f6000L, 0x2f6440L, 0x2f6470L, 0x2f6600L, 0x2f6b40L, 0x2f6b60L
    };
    private static final Pattern IMAGE_ADDRESS = Pattern.compile("(?i)(?:0x)?(71[0-9a-f]{8})");
    private int decompiled;
    private int instructions;
    private int directCalls;

    private String offset(Address address) {
        return String.format("main+0x%x", address.getOffset() - BASE);
    }

    private String pointer(long value) {
        return value >= BASE && value < BASE + 0x2000000L
            ? offset(toAddr(value)) : String.format("0x%x", value);
    }

    private String normalize(String text) {
        Matcher matcher = IMAGE_ADDRESS.matcher(text);
        StringBuffer result = new StringBuffer();
        while (matcher.find()) {
            long value = Long.parseUnsignedLong(matcher.group(1), 16);
            String replacement = pointer(value);
            matcher.appendReplacement(result, Matcher.quoteReplacement(replacement));
        }
        matcher.appendTail(result);
        return result.toString();
    }

    private String sourceHash(String path) throws Exception {
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        try (InputStream stream = Files.newInputStream(Paths.get(path))) {
            byte[] buffer = new byte[1024 * 1024];
            int count;
            while ((count = stream.read(buffer)) != -1) digest.update(buffer, 0, count);
        }
        return HexFormat.of().formatHex(digest.digest());
    }

    private void incoming(Address address) {
        ReferenceIterator refs = currentProgram.getReferenceManager().getReferencesTo(address);
        int count = 0;
        while (refs.hasNext()) {
            Reference ref = refs.next();
            Function owner = getFunctionContaining(ref.getFromAddress());
            Instruction instruction = getInstructionAt(ref.getFromAddress());
            println("XREF\ttarget=" + offset(address)
                + "\tfrom=" + offset(ref.getFromAddress())
                + "\ttype=" + ref.getReferenceType()
                + "\towner=" + (owner == null ? "NONE" : offset(owner.getEntryPoint()))
                + "\tinstruction=" + (instruction == null ? "NONE" : normalize(instruction.toString())));
            count++;
        }
        println("XREF_COUNT\t" + offset(address) + "\t" + count);
    }

    private void inspect(long targetOffset, DecompInterface decompiler) throws Exception {
        Address address = toAddr(BASE + targetOffset);
        incoming(address);
        Function function = getFunctionAt(address);
        if (function == null) {
            throw new IllegalStateException("expected exact function boundary missing at " + offset(address));
        }
        println("FUNCTION\t" + offset(address) + "\tbytes=" + function.getBody().getNumAddresses());
        InstructionIterator iterator = currentProgram.getListing().getInstructions(function.getBody(), true);
        while (iterator.hasNext()) {
            Instruction instruction = iterator.next();
            instructions++;
            println("INS\t" + offset(instruction.getAddress()) + "\t"
                + HexFormat.of().formatHex(instruction.getBytes()) + "\t"
                + normalize(instruction.toString()));
            if (instruction.getFlowType().isCall()) {
                Address[] flows = instruction.getFlows();
                if (flows == null || flows.length == 0) {
                    println("INDIRECT_CALL\t" + offset(instruction.getAddress())
                        + "\t" + normalize(instruction.toString()));
                } else {
                    for (Address flow : flows) {
                        Function callee = getFunctionAt(flow);
                        println("CALL\tfrom=" + offset(instruction.getAddress())
                            + "\ttarget=" + offset(flow)
                            + "\tcallee=" + (callee == null ? "NONE" : offset(callee.getEntryPoint())));
                        directCalls++;
                    }
                }
            }
        }
        DecompileResults result = decompiler.decompileFunction(function, 120, monitor);
        if (!result.decompileCompleted() || result.getDecompiledFunction() == null) {
            throw new IllegalStateException("decompilation failed at " + offset(address)
                + ": " + result.getErrorMessage());
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
        if (!EXPECTED_SHA256.equals(hash)) throw new IllegalStateException("source SHA-256 mismatch: " + hash);
        println("GUARD\tSHA256=" + hash + "\tbase=main+0x0\tprogram=" + currentProgram.getName());
        println("SCOPE\tDirect getter-result consumers only; no result-field semantics or runtime dispatch inferred.");

        DecompInterface decompiler = new DecompInterface();
        if (!decompiler.openProgram(currentProgram)) throw new IllegalStateException("decompiler could not open program");
        try {
            for (long target : TARGETS) inspect(target, decompiler);
        } finally {
            decompiler.dispose();
        }
        if (!EXPECTED_SHA256.equals(sourceHash(executable))) {
            throw new IllegalStateException("source hash changed during run");
        }
        println("SUMMARY\tdecompiled=" + decompiled + "\tinstructions=" + instructions
            + "\tdirectCallSites=" + directCalls + "\tsourceHashUnchanged=true\treadOnly=true");
    }
}
