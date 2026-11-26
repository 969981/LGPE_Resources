import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.mem.Memory;

import java.io.BufferedReader;
import java.io.File;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.security.MessageDigest;
import java.util.HashSet;
import java.util.Locale;
import java.util.Set;

public class VerifyPokeLdnRtti extends GhidraScript {
    private static final String EXPECTED_MAIN_SHA256 =
        "1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8";
    private static final long EXPECTED_BASE = 0x7100000000L;
    private static final String EXPECTED_NCA_ID = "2b7730a9e56498bbafac2002d4908c6b";

    private long classRows;
    private long vtableRows;
    private long checkedMethodSlots;
    private long checkedStrings;
    private long checkedVtableHeaders;
    private long bad;
    private long codeFunctions;
    private long codeInstructions;
    private final Set<Long> uniqueMethods = new HashSet<>();
    private final Set<String> classes = new HashSet<>();

    @Override
    public void run() throws Exception {
        String executable = currentProgram.getExecutablePath();
        String normalized = executable == null ? "" : executable.trim().replace('\\', '/');
        println("PROGRAM\t" + currentProgram.getName() + "\timageBase="
            + currentProgram.getImageBase() + "\texecutable=" + normalized);
        if (currentProgram.getImageBase().getOffset() != EXPECTED_BASE
            || !normalized.toLowerCase(Locale.ROOT).contains(EXPECTED_NCA_ID)
            || !normalized.toLowerCase(Locale.ROOT).endsWith("/0/main")) {
            throw new IllegalStateException("program identity/base is not the recorded LGPE 1.0.2 main");
        }
        try {
            String actualHash = sha256(Paths.get(executable.trim()));
            println("SOURCE_SHA256\t" + actualHash);
            if (!EXPECTED_MAIN_SHA256.equals(actualHash)) {
                throw new IllegalStateException("program source SHA-256 mismatch: " + actualHash);
            }
        } catch (IOException e) {
            println("SOURCE_SHA256_UNAVAILABLE\t" + e.getMessage());
        }

        String[] args = getScriptArgs();
        if (args.length != 1) {
            throw new IllegalArgumentException("usage: VerifyPokeLdnRtti.java <PokeLDN pointer TSV>");
        }
        Path tsv = Paths.get(args[0]);
        println("INVENTORY\t" + tsv.toAbsolutePath());
        try (BufferedReader reader = Files.newBufferedReader(tsv, StandardCharsets.UTF_8)) {
            String line;
            while ((line = reader.readLine()) != null) {
                if (line.isEmpty() || line.startsWith("#")) continue;
                String[] fields = line.split("\\t", -1);
                if ("CLASS".equals(fields[0])) {
                    verifyClass(fields);
                } else if ("VTABLE".equals(fields[0])) {
                    verifyVtable(fields);
                } else {
                    bad++;
                    println("BAD_ROW\t" + line);
                }
            }
        }
        println("SUMMARY\tclasses=" + classes.size() + "\tclass_rows=" + classRows
            + "\tstrings=" + checkedStrings + "\tvtables=" + vtableRows
            + "\tvtable_headers=" + checkedVtableHeaders + "\tmethod_slots=" + checkedMethodSlots
            + "\tunique_methods=" + uniqueMethods.size() + "\tfunctions=" + codeFunctions
            + "\tinstructions=" + codeInstructions + "\tbad=" + bad);
        if (classes.size() != 269 || checkedStrings != classRows || bad != 0) {
            throw new IllegalStateException("RTTI pointer cross-check failed");
        }
    }

    private void verifyClass(String[] f) throws Exception {
        if (f.length != 5) throw new IllegalArgumentException("CLASS row requires 5 fields");
        String name = f[1];
        long typeInfoOffset = parseOffset(f[2]);
        long nameOffset = parseOffset(f[3]);
        Address base = currentProgram.getImageBase();
        Address typeInfo = base.add(typeInfoOffset);
        Address namePointerSlot = typeInfo.add(8);
        long pointer = currentProgram.getMemory().getLong(namePointerSlot);
        Address expectedName = base.add(nameOffset);
        String actualMangledName = readCString(expectedName, 512);
        boolean good = pointer == expectedName.getOffset() && actualMangledName.equals(f[4]);
        classRows++;
        classes.add(name);
        if (good) {
            checkedStrings++;
        } else {
            bad++;
            println("BAD_CLASS\t" + name + "\tti=" + typeInfo + "\tnameptr="
                + String.format("0x%x", pointer) + "\texpected=" + expectedName
                + "\tactual=" + actualMangledName + "\twanted=" + f[4]);
        }
    }

    private void verifyVtable(String[] f) throws Exception {
        if (f.length != 5) throw new IllegalArgumentException("VTABLE row requires 5 fields");
        String name = f[1];
        long vtableOffset = parseOffset(f[2]);
        long typeInfoOffset = parseOffset(f[3]);
        Address base = currentProgram.getImageBase();
        Address vtable = base.add(vtableOffset);
        long typeInfoPointer = currentProgram.getMemory().getLong(vtable);
        long expectedTypeInfo = base.add(typeInfoOffset).getOffset();
        vtableRows++;
        if (typeInfoPointer == expectedTypeInfo) {
            checkedVtableHeaders++;
        } else {
            bad++;
            println("BAD_VTABLE\t" + name + "\tvtable=" + vtable + "\ttypeinfo="
                + String.format("0x%x", typeInfoPointer) + "\texpected="
                + String.format("0x%x", expectedTypeInfo));
        }
        if (!f[4].isEmpty()) {
            String[] methods = f[4].split(",");
            for (int i = 0; i < methods.length; i++) {
                long methodOffset = parseOffset(methods[i]);
                Address slot = vtable.add(8L + 8L * i);
                Address expectedFunction = base.add(methodOffset);
                long pointer = currentProgram.getMemory().getLong(slot);
                checkedMethodSlots++;
                uniqueMethods.add(methodOffset);
                if (pointer != expectedFunction.getOffset()) {
                    bad++;
                    println("BAD_METHOD\t" + name + "\tindex=" + i + "\tslot=" + slot
                        + "\tactual=" + String.format("0x%x", pointer)
                        + "\texpected=" + expectedFunction);
                    continue;
                }
                Function function = currentProgram.getFunctionManager().getFunctionAt(expectedFunction);
                Instruction instruction = currentProgram.getListing().getInstructionAt(expectedFunction);
                if (function != null) codeFunctions++;
                if (instruction != null) codeInstructions++;
                if (!currentProgram.getMemory().contains(expectedFunction)) {
                    bad++;
                    println("METHOD_UNMAPPED\t" + name + "\t" + expectedFunction);
                }
            }
        }
    }

    private long parseOffset(String value) {
        return Long.decode(value);
    }

    private String readCString(Address start, int max) throws Exception {
        Memory memory = currentProgram.getMemory();
        StringBuilder result = new StringBuilder();
        for (int i = 0; i < max; i++) {
            int value = memory.getByte(start.add(i)) & 0xff;
            if (value == 0) break;
            result.append((char) value);
        }
        return result.toString();
    }

    private String sha256(Path path) throws Exception {
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        try (java.io.InputStream in = Files.newInputStream(path)) {
            byte[] buffer = new byte[65536];
            int n;
            while ((n = in.read(buffer)) >= 0) digest.update(buffer, 0, n);
        }
        StringBuilder hex = new StringBuilder();
        for (byte b : digest.digest()) hex.append(String.format("%02x", b & 0xff));
        return hex.toString();
    }
}
