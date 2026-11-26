import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.mem.MemoryBlock;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.util.Locale;

public class TraceLocalizedSortVtableAccess extends GhidraScript {
    private static final long EXPECTED_BASE = 0x7100000000L;
    private static final String EXPECTED_NCA_ID = "2b7730a9e56498bbafac2002d4908c6b";
    private static final String EXPECTED_MAIN_SHA256 =
        "1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8";
    private static final long[] TARGETS = {
        0x7100b313c0L, 0x7100b313f0L,
        0x7100b31860L, 0x7100b31890L, 0x7100b31870L, 0x7100b318a0L,
        0x7100b31880L, 0x7100b318b0L,
        0x7100b321e0L, 0x7100b32310L, 0x7100b32320L, 0x7100b32330L
    };
    private static final String[] ROLES = {
        "item-sort vtable slot", "item-sort vtable slot",
        "item-sort vtable slot", "item-sort vtable slot",
        "item-sort vtable slot", "item-sort vtable slot",
        "waza-sort vtable slot", "waza-sort vtable slot",
        "waza-sort vtable slot", "waza-sort vtable slot",
        "waza-sort vtable slot", "waza-sort vtable slot"
    };
    private int decompiled;
    private int temporaryFunctions;

    @Override
    public void run() throws Exception {
        String executable = currentProgram.getExecutablePath();
        String normalized = executable == null ? "" : executable.trim().replace('\\', '/');
        if (currentProgram.getImageBase().getOffset() != EXPECTED_BASE
            || !normalized.toLowerCase(Locale.ROOT).contains(EXPECTED_NCA_ID)
            || !normalized.toLowerCase(Locale.ROOT).endsWith("/0/main")) {
            throw new IllegalStateException("not the recorded LGPE 1.0.2 main program");
        }
        String mainHash = sha256(Path.of(executable.trim()));
        if (!EXPECTED_MAIN_SHA256.equals(mainHash)) {
            throw new IllegalStateException("source main SHA-256 mismatch: " + mainHash);
        }
        println("PROGRAM\tversion=Pokemon Let's Go Pikachu 1.0.2\tbase="
            + currentProgram.getImageBase() + "\tmain_sha256=" + mainHash);
        println("SCOPE\tfunctions are selected from exact-build item/waza sort vtable entries"
            + " recorded by InspectSortStringReferences.java; decompilation and xrefs"
            + " do not imply runtime execution");

        for (int i = 0; i < TARGETS.length; i++) {
            inspectFunction(TARGETS[i], ROLES[i]);
        }
        println("SUMMARY\tdecompiled_functions=" + decompiled
            + "\ttemporary_functions=" + temporaryFunctions
            + "\tprogram=" + currentProgram.getName());
        if (!EXPECTED_MAIN_SHA256.equals(sha256(Path.of(executable.trim())))) {
            throw new IllegalStateException("source main hash changed during inspection");
        }
    }

    private Address address(long offset) {
        return currentProgram.getImageBase().add(offset - EXPECTED_BASE);
    }

    private void inspectFunction(long offset, String role) throws Exception {
        Address target = address(offset);
        MemoryBlock block = currentProgram.getMemory().getBlock(target);
        if (block == null || !block.isExecute()) {
            throw new IllegalStateException("vtable target is not in executable memory: " + target);
        }
        Function function = currentProgram.getFunctionManager().getFunctionAt(target);
        boolean temporary = false;
        if (function == null) {
            if (currentProgram.getListing().getInstructionAt(target) == null) disassemble(target);
            if (currentProgram.getListing().getInstructionAt(target) != null) {
                function = createFunction(target, null);
                temporary = function != null;
            }
        }
        if (function == null) {
            println("FUNCTION_NOT_FOUND\trole=" + role + "\taddress=" + target);
            return;
        }
        println("FUNCTION\trole=" + role + "\trequested=" + target
            + "\tentry=" + function.getEntryPoint() + "\tname=" + function.getName()
            + "\ttemporary=" + temporary + "\tblock=" + block.getName());
        if (temporary) temporaryFunctions++;
        ReferenceIterator references = currentProgram.getReferenceManager()
            .getReferencesTo(target);
        int incoming = 0;
        while (references.hasNext()) {
            monitor.checkCancelled();
            Reference reference = references.next();
            Function caller = currentProgram.getFunctionManager()
                .getFunctionContaining(reference.getFromAddress());
            println("INCOMING\trole=" + role + "\tfrom=" + reference.getFromAddress()
                + "\ttype=" + reference.getReferenceType() + "\tcaller="
                + (caller == null ? "<no-function>" : caller.getEntryPoint()));
            incoming++;
        }
        println("INCOMING_COUNT\trole=" + role + "\tcount=" + incoming);

        DecompInterface decompiler = new DecompInterface();
        decompiler.openProgram(currentProgram);
        DecompileResults result = decompiler.decompileFunction(function, 60, monitor);
        if (result != null && result.decompileCompleted()
            && result.getDecompiledFunction() != null) {
            String[] lines = result.getDecompiledFunction().getC().split("\\n");
            for (int i = 0; i < lines.length; i++) {
                println("CODE\t" + function.getEntryPoint() + "\t" + i + "\t" + lines[i]);
            }
            decompiled++;
        } else {
            println("DECOMPILE_FAILED\trole=" + role + "\taddress=" + target
                + "\tmessage=" + (result == null ? "null result" : result.getErrorMessage()));
        }
        decompiler.dispose();
    }

    private static String sha256(Path file) throws Exception {
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        try (java.io.InputStream in = Files.newInputStream(file)) {
            byte[] buffer = new byte[1024 * 1024];
            int read;
            while ((read = in.read(buffer)) >= 0) digest.update(buffer, 0, read);
        }
        StringBuilder hex = new StringBuilder();
        for (byte b : digest.digest()) hex.append(String.format("%02x", b & 0xff));
        return hex.toString();
    }
}
