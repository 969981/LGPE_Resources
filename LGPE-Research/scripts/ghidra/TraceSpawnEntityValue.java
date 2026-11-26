import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;

public class TraceSpawnEntityValue extends GhidraScript {
    private static final String EXPECTED_SHA256 =
        "1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8";
    private static final long EXPECTED_BASE = 0x7100000000L;
    private static final long[] OFFSETS = {
        0x218470L, 0x00d4af0L, 0x00a87a0L, 0x00b84d0L,
        0x00d22b0L, 0x02175e0L, 0x0216f90L, 0x026f930L,
        0x02334d0L, 0x0139260L, 0x2fd8a0L, 0x2f8a50L,
        0x2fdf90L, 0x300e40L
    };

    private String sha256(Path path) throws Exception {
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        try (InputStream input = Files.newInputStream(path)) {
            byte[] buffer = new byte[1024 * 1024];
            int count;
            while ((count = input.read(buffer)) != -1) digest.update(buffer, 0, count);
        }
        StringBuilder value = new StringBuilder();
        for (byte b : digest.digest()) value.append(String.format("%02x", b & 0xff));
        return value.toString();
    }

    private int printReferences(Address target) throws Exception {
        int count = 0;
        ReferenceIterator references = currentProgram.getReferenceManager().getReferencesTo(target);
        while (references.hasNext()) {
            monitor.checkCancelled();
            Reference reference = references.next();
            count++;
            Function owner = currentProgram.getFunctionManager()
                .getFunctionContaining(reference.getFromAddress());
            println("REFERENCE\t" + target + "\tfrom=" + reference.getFromAddress()
                + "\ttype=" + reference.getReferenceType() + "\towner="
                + (owner == null ? "<none>" : owner.getEntryPoint()));
        }
        println("REFERENCE_COUNT\t" + target + "\t" + count);
        return count;
    }

    @Override
    public void run() throws Exception {
        String executable = currentProgram.getExecutablePath();
        String actualSha = sha256(Path.of(executable));
        println("PROGRAM\t" + executable + "\tbase=" + currentProgram.getImageBase()
            + "\tsha256=" + actualSha);
        if (currentProgram.getImageBase().getOffset() != EXPECTED_BASE
            || !EXPECTED_SHA256.equals(actualSha)
            || !executable.replace('\\', '/').toLowerCase().endsWith("/0/main")) {
            throw new IllegalStateException("not the exact local Let's Go Pikachu 1.0.2 main");
        }

        DecompInterface decompiler = new DecompInterface();
        decompiler.openProgram(currentProgram);
        Path decompDirectory = Path.of("logs", "ghidra-spawn-entity-value-v1-functions");
        Files.createDirectories(decompDirectory);
        for (long offset : OFFSETS) {
            Address address = currentProgram.getImageBase().add(offset);
            Function function = currentProgram.getFunctionManager().getFunctionAt(address);
            println("FUNCTION\t" + address + "\tname="
                + (function == null ? "<none>" : function.getName()) + "\tbytes="
                + (function == null ? 0 : function.getBody().getNumAddresses()));
            if (function == null) continue;
            printReferences(address);
            DecompileResults result = decompiler.decompileFunction(function, 120, monitor);
            if (!result.decompileCompleted() || result.getDecompiledFunction() == null) {
                println("DECOMPILE_FAILED\t" + address + "\t" + result.getErrorMessage());
                continue;
            }
            String code = result.getDecompiledFunction().getC();
            println("DECOMPILED_BEGIN\t" + address + "\tchars=" + code.length());
            Path decompPath = decompDirectory.resolve("function-"
                + Long.toHexString(offset) + ".c");
            Files.writeString(decompPath, code, StandardCharsets.UTF_8);
            println("DECOMPILED_FILE\t" + decompPath.toAbsolutePath());
            println("DECOMPILED_END\t" + address);
        }
        decompiler.dispose();
        println("SUMMARY\tsha256=" + actualSha + "\tbase=0x"
            + Long.toHexString(currentProgram.getImageBase().getOffset()) + "\tread_only=true");
    }
}
