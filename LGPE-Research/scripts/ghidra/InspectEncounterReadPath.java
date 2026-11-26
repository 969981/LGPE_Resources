import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Data;
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

public class InspectEncounterReadPath extends GhidraScript {
    private static final String EXPECTED_MAIN_SHA256 =
        "1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8";
    private static final long EXPECTED_BASE = 0x7100000000L;
    private static final String EXPECTED_NCA_ID = "2b7730a9e56498bbafac2002d4908c6b";
    private static final long[] OFFSETS = {
        0x12a730L, 0x12cee0L, 0x135960L, 0x13b650L, 0x13bfa0L, 0x13d020L,
        0x00238e0L, 0x0023970L, 0x0023990L, 0x0026070L, 0x0026610L,
        0x00276e0L, 0x0023e10L, 0x0023680L, 0x00237c0L, 0x00a63a0L,
        0x00adc70L, 0x000093b0L, 0x000093d0L, 0x001d3c0L, 0x001d430L
    };
    private static final long[] DECOMPILE_OFFSETS = {
        0x12a730L, 0x12cee0L, 0x13d020L, 0x13bfa0L, 0x0023970L, 0x0026070L,
        0x0026610L, 0x00276e0L, 0x0023e10L, 0x0023680L,
        0x00a63a0L, 0x00adc70L, 0x000093b0L, 0x000093d0L,
        0x001d3c0L, 0x001d430L
    };
    private static final long[] CREATE_OFFSETS = {
        0x000093b0L, 0x000093d0L
    };

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
        inspectVtable(0x71015fafe8L, "encounter resource callback subobject", 0x18);
        inspectVtable(0x71015fcb38L, "encounter data object primary vtable", 0x58);
        for (long offset : OFFSETS) inspect(offset, decompiler);
        decompiler.dispose();
        println("SUMMARY\timage=" + normalized);
    }

    private void inspectVtable(long globalAddress, String label, int length) throws Exception {
        Address global = toAddr(globalAddress);
        long vtableBase = currentProgram.getMemory().getLong(global);
        Address vptr = toAddr(vtableBase + 0x10);
        println("VTABLE\t" + label + "\tglobal=" + global + "\tbase="
            + toAddr(vtableBase) + "\tvptr=" + vptr);
        for (int offset = 0; offset < length; offset += 8) {
            Address slot = vptr.add(offset);
            long raw = currentProgram.getMemory().getLong(slot);
            Address target = toAddr(raw);
            Function function = currentProgram.getFunctionManager().getFunctionContaining(target);
            println("VTABLE_SLOT\t" + label + "\t+0x" + Integer.toHexString(offset)
                + "\t" + slot + "\t" + target + "\t"
                + (function == null ? "<no-function>" : function.getEntryPoint()));
        }
    }

    private void inspect(long offset, DecompInterface decompiler) throws Exception {
        Address address = currentProgram.getImageBase().add(offset);
        Function exact = currentProgram.getFunctionManager().getFunctionAt(address);
        Function function = exact != null ? exact
            : currentProgram.getFunctionManager().getFunctionContaining(address);
        if (function == null && shouldCreate(offset)) {
            disassemble(address);
            function = createFunction(address, null);
        }
        println("TARGET\tmain+0x" + Long.toHexString(offset) + "\t" + address
            + "\tfunctionAt=" + (exact == null ? "<none>" : exact.getEntryPoint())
            + "\tfunctionContaining=" + (function == null ? "<none>" : function.getEntryPoint())
            + "\tname=" + (function == null ? "<none>" : function.getName()));
        if (function == null) {
            continueTarget(offset);
            return;
        }

        ReferenceIterator incoming = currentProgram.getReferenceManager().getReferencesTo(address);
        while (incoming.hasNext()) {
            Reference reference = incoming.next();
            Function caller = currentProgram.getFunctionManager()
                .getFunctionContaining(reference.getFromAddress());
            println("INCOMING\t" + reference.getFromAddress() + "\t"
                + reference.getReferenceType() + "\tcaller="
                + (caller == null ? "<no-function>" : caller.getEntryPoint()));
        }

        InstructionIterator instructions = currentProgram.getListing()
            .getInstructions(function.getBody(), true);
        while (instructions.hasNext()) {
            Instruction instruction = instructions.next();
            for (Reference reference : instruction.getReferencesFrom()) {
                if (reference.getReferenceType().isCall()) {
                    Function callee = currentProgram.getFunctionManager()
                        .getFunctionContaining(reference.getToAddress());
                    println("CALL\t" + instruction.getAddress() + "\t" + reference.getToAddress()
                        + "\tcallee=" + (callee == null ? "<no-function>" : callee.getEntryPoint()));
                }
                Data data = currentProgram.getListing().getDataAt(reference.getToAddress());
                if (data != null && data.getValue() instanceof String) {
                    println("STRING_REF\t" + instruction.getAddress() + "\t"
                        + reference.getToAddress() + "\t" + clean((String) data.getValue()));
                }
            }
        }

        if (shouldDecompile(offset)) {
            DecompileResults result = decompiler.decompileFunction(function, 120, monitor);
            if (!result.decompileCompleted() || result.getDecompiledFunction() == null) {
                println("DECOMPILE_FAILED\t" + function.getEntryPoint() + "\t"
                    + result.getErrorMessage());
            } else {
                String code = result.getDecompiledFunction().getC();
                println("DECOMPILED_BEGIN\t" + function.getEntryPoint() + "\tchars=" + code.length());
                if (offset == 0x12a730L) {
                    printContext(code, new String[] {
                        "param_1[0x3e] = 0;", "param_1[0x4e] = 0;",
                        "encount_data_p.bin", "FUN_71000adc70(param_1 + 0x3c"
                    }, 3, 6);
                } else if (offset == 0x12cee0L) {
                    printContext(code, new String[] {
                        "uVar11 < 0x93", "FUN_71000adc70((long *)&local_f40",
                        "bin/field/param/placement/"
                    }, 2, 5);
                } else {
                    println(code);
                }
                println("DECOMPILED_END\t" + function.getEntryPoint());
            }
        }
    }

    private void continueTarget(long offset) {
        println("FUNCTION_NOT_FOUND\tmain+0x" + Long.toHexString(offset));
    }

    private boolean shouldDecompile(long offset) {
        for (long candidate : DECOMPILE_OFFSETS) if (candidate == offset) return true;
        return false;
    }

    private boolean shouldCreate(long offset) {
        for (long candidate : CREATE_OFFSETS) if (candidate == offset) return true;
        return false;
    }

    private String clean(String value) {
        return value.replace("\\", "\\\\").replace("\r", "\\r")
            .replace("\n", "\\n").replace("\t", "\\t");
    }

    private void printContext(String code, String[] needles, int before, int after) {
        String[] lines = code.split("\\R", -1);
        boolean[] selected = new boolean[lines.length];
        for (String needle : needles) {
            for (int i = 0; i < lines.length; i++) {
                if (!lines[i].contains(needle)) continue;
                for (int j = Math.max(0, i - before); j <= Math.min(lines.length - 1, i + after); j++) {
                    selected[j] = true;
                }
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
