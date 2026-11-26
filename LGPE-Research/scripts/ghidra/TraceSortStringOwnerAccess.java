import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.util.Locale;

public class TraceSortStringOwnerAccess extends GhidraScript {
    private static final long EXPECTED_BASE = 0x7100000000L;
    private static final String EXPECTED_NCA_ID = "2b7730a9e56498bbafac2002d4908c6b";
    private static final String EXPECTED_MAIN_SHA256 =
        "1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8";
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

        inspectStringPointerTable(0x71015520b8L, 10,
            "zukan_data indexed path table candidate");
        long[] functions = {
            0x71003775e0L, 0x7100377800L, 0x7100377810L,
            0x7100b09900L, 0x7100b0acd0L, 0x7100b0a150L,
            0x7100b0a200L, 0x7100b094e0L,
            0x7100b31300L, 0x7100b31400L,
            0x7100b315e0L, 0x7100b317c0L, 0x7100b318c0L,
            0x71003740d0L, 0x71001b3bb0L
        };
        String[] roles = {
            "zukan_data resource loader", "u16 accessor on loaded resource object",
            "loaded resource element count accessor", "zukan_data owner resource initializer",
            "query path that calls the u16 accessor", "monsname owner list scan",
            "monsname owner range scan", "monsname owner initialization",
            "item sort resource owner constructor", "item sort path request builder",
            "monsname sort owner initializer", "waza sort resource owner constructor",
            "waza sort path request builder", "localized sort path builder",
            "generic resource request helper"
        };
        for (int i = 0; i < functions.length; i++) {
            inspectFunction(functions[i], roles[i]);
        }
        inspectIncoming(0x7100b09900L, "zukan_data owner resource initializer");
        inspectIncoming(0x7100b0acd0L, "query path that calls the u16 accessor");
        inspectIncoming(0x7100377800L, "u16 accessor on loaded resource object");
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
        Function function = currentProgram.getFunctionManager().getFunctionAt(target);
        if (function == null) function = currentProgram.getFunctionManager().getFunctionContaining(target);
        boolean temporary = false;
        if (function == null) {
            if (currentProgram.getListing().getInstructionAt(target) == null) {
                disassemble(target);
            }
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
            + "\ttemporary=" + temporary);
        if (temporary) temporaryFunctions++;
        DecompInterface decompiler = new DecompInterface();
        decompiler.openProgram(currentProgram);
        DecompileResults result = decompiler.decompileFunction(function, 60, monitor);
        if (result != null && result.decompileCompleted() && result.getDecompiledFunction() != null) {
            String[] lines = result.getDecompiledFunction().getC().split("\n");
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

    private void inspectIncoming(long offset, String role) throws Exception {
        Address target = address(offset);
        ReferenceIterator refs = currentProgram.getReferenceManager().getReferencesTo(target);
        int count = 0;
        while (refs.hasNext()) {
            monitor.checkCancelled();
            Reference ref = refs.next();
            Function caller = currentProgram.getFunctionManager().getFunctionContaining(ref.getFromAddress());
            println("INCOMING\trole=" + role + "\tfrom=" + ref.getFromAddress()
                + "\ttype=" + ref.getReferenceType() + "\tcaller="
                + (caller == null ? "<no-function>" : caller.getEntryPoint())
                + "\tname=" + (caller == null ? "<no-function>" : caller.getName()));
            count++;
        }
        println("INCOMING_COUNT\trole=" + role + "\tcount=" + count);
    }

    private void inspectStringPointerTable(long offset, int count, String role) throws Exception {
        Address table = address(offset);
        println("STRING_TABLE_BEGIN\trole=" + role + "\taddress=" + table + "\tcount=" + count);
        for (int i = 0; i < count; i++) {
            Address slot = table.add(i * 8L);
            long value = currentProgram.getMemory().getLong(slot);
            Address target = currentProgram.getAddressFactory().getDefaultAddressSpace().getAddress(value);
            String text = "<unreadable>";
            if (currentProgram.getMemory().contains(target)) {
                StringBuilder builder = new StringBuilder();
                for (int j = 0; j < 160; j++) {
                    int b = currentProgram.getMemory().getByte(target.add(j)) & 0xff;
                    if (b == 0) break;
                    if (b < 0x20 || b > 0x7e) {
                        builder.append('?');
                    } else {
                        builder.append((char)b);
                    }
                }
                text = builder.toString();
            }
            println("STRING_TABLE_ENTRY\tindex=" + i + "\tslot=" + slot
                + "\tvalue=" + target + "\ttext=" + text);
        }
        println("STRING_TABLE_END\trole=" + role);
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
