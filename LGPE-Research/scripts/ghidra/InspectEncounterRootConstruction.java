import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;

import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.security.MessageDigest;
import java.util.Locale;

public class InspectEncounterRootConstruction extends GhidraScript {
    private static final String EXPECTED_MAIN_SHA256 =
        "1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8";
    private static final long EXPECTED_BASE = 0x7100000000L;
    private static final String EXPECTED_NCA_ID = "2b7730a9e56498bbafac2002d4908c6b";
    private static final long TARGET_OFFSET = 0x5bd0L;

    @Override
    public void run() throws Exception {
        String executable = currentProgram.getExecutablePath();
        String normalized = executable == null ? "" : executable.trim().replace('\\', '/');
        if (currentProgram.getImageBase().getOffset() != EXPECTED_BASE
            || !normalized.toLowerCase(Locale.ROOT).contains(EXPECTED_NCA_ID)
            || !normalized.toLowerCase(Locale.ROOT).endsWith("/0/main")) {
            throw new IllegalStateException("not the recorded LGPE 1.0.2 main program");
        }
        String actualHash = sha256(executable.trim());
        println("PROGRAM\tbase=" + currentProgram.getImageBase() + "\tsha256=" + actualHash);
        if (!EXPECTED_MAIN_SHA256.equals(actualHash)) {
            throw new IllegalStateException("source main SHA-256 mismatch: " + actualHash);
        }

        Address address = currentProgram.getImageBase().add(TARGET_OFFSET);
        Function function = currentProgram.getFunctionManager().getFunctionAt(address);
        if (function == null) throw new IllegalStateException("caller function not found: " + address);
        println("FUNCTION\tmain+0x" + Long.toHexString(TARGET_OFFSET) + "\t"
            + function.getEntryPoint() + "\t" + function.getName());
        ReferenceIterator incoming = currentProgram.getReferenceManager()
            .getReferencesTo(function.getEntryPoint());
        while (incoming.hasNext()) {
            Reference ref = incoming.next();
            Function caller = currentProgram.getFunctionManager()
                .getFunctionContaining(ref.getFromAddress());
            println("INCOMING\t" + ref.getFromAddress() + "\t" + ref.getReferenceType()
                + "\tcaller=" + (caller == null ? "<no-function>" : caller.getEntryPoint()));
        }

        DecompInterface decompiler = new DecompInterface();
        decompiler.openProgram(currentProgram);
        DecompileResults result = decompiler.decompileFunction(function, 120, monitor);
        if (!result.decompileCompleted() || result.getDecompiledFunction() == null) {
            throw new IllegalStateException("decompile failed: " + result.getErrorMessage());
        }
        String[] lines = result.getDecompiledFunction().getC().split("\\R", -1);
        println("DECOMPILED_BEGIN\t" + function.getEntryPoint() + "\tchars="
            + result.getDecompiledFunction().getC().length());
        boolean[] selected = new boolean[lines.length];
        for (int i = 0; i < lines.length; i++) {
            if (!lines[i].contains("FUN_710013b650")) continue;
            for (int j = Math.max(0, i - 18); j <= Math.min(lines.length - 1, i + 18); j++) {
                selected[j] = true;
            }
        }
        boolean previous = false;
        for (int i = 0; i < lines.length; i++) {
            if (selected[i]) {
                if (!previous) println("CONTEXT_BEGIN");
                println(lines[i]);
            } else if (previous) {
                println("CONTEXT_END");
            }
            previous = selected[i];
        }
        if (previous) println("CONTEXT_END");
        println("DECOMPILED_END\t" + function.getEntryPoint());
        decompiler.dispose();
        println("SUMMARY\timage=" + normalized);
    }

    private String sha256(String path) throws Exception {
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        try (InputStream in = Files.newInputStream(Paths.get(path))) {
            byte[] buffer = new byte[65536];
            int n;
            while ((n = in.read(buffer)) >= 0) digest.update(buffer, 0, n);
        }
        StringBuilder hex = new StringBuilder();
        for (byte b : digest.digest()) hex.append(String.format("%02x", b & 0xff));
        return hex.toString();
    }
}
