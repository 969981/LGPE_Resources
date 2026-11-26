import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
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
import java.util.Locale;

public class InspectNexMatchmakingChain extends GhidraScript {
    private static final String EXPECTED_MAIN_SHA256 =
        "1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8";
    private static final long EXPECTED_BASE = 0x7100000000L;
    private static final String EXPECTED_NCA_ID = "2b7730a9e56498bbafac2002d4908c6b";
    private static final long[] OFFSETS = {0xb36610L, 0xb402f0L, 0x50d730L};

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

        DecompInterface decompiler = new DecompInterface();
        decompiler.openProgram(currentProgram);
        for (long offset : OFFSETS) {
            Address address = currentProgram.getImageBase().add(offset);
            Function function = currentProgram.getFunctionManager().getFunctionAt(address);
            println("TARGET\tmain+0x" + Long.toHexString(offset) + "\t" + address
                + "\tfunction=" + (function == null ? "<none>" : function.getEntryPoint())
                + "\tname=" + (function == null ? "<none>" : function.getName()));
            ReferenceIterator incoming = currentProgram.getReferenceManager().getReferencesTo(address);
            while (incoming.hasNext()) {
                Reference reference = incoming.next();
                Function caller = currentProgram.getFunctionManager()
                    .getFunctionContaining(reference.getFromAddress());
                println("INCOMING\t" + reference.getFromAddress() + "\t"
                    + reference.getReferenceType() + "\tcaller="
                    + (caller == null ? "<no-function>" : caller.getEntryPoint()));
            }
            if (function == null) continue;
            InstructionIterator instructions = currentProgram.getListing()
                .getInstructions(function.getBody(), true);
            while (instructions.hasNext()) {
                Instruction instruction = instructions.next();
                for (Reference reference : instruction.getReferencesFrom()) {
                    if (!reference.getReferenceType().isCall()) continue;
                    Function callee = currentProgram.getFunctionManager()
                        .getFunctionContaining(reference.getToAddress());
                    println("CALL\t" + instruction.getAddress() + "\t" + reference.getToAddress()
                        + "\tcallee=" + (callee == null ? "<no-function>" : callee.getEntryPoint()));
                }
            }
            DecompileResults result = decompiler.decompileFunction(function, 120, monitor);
            if (!result.decompileCompleted() || result.getDecompiledFunction() == null) {
                println("DECOMPILE_FAILED\t" + address + "\t" + result.getErrorMessage());
            } else {
                println("DECOMPILED_BEGIN\t" + address);
                println(result.getDecompiledFunction().getC());
                println("DECOMPILED_END\t" + address);
            }
        }
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
