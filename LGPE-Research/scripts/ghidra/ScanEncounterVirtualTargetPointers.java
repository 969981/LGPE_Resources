import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.mem.MemoryBlock;

import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.security.MessageDigest;
import java.util.Locale;

public class ScanEncounterVirtualTargetPointers extends GhidraScript {
    private static final String EXPECTED_MAIN_SHA256 =
        "1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8";
    private static final long EXPECTED_BASE = 0x7100000000L;
    private static final String EXPECTED_NCA_ID = "2b7730a9e56498bbafac2002d4908c6b";
    private static final long[] TARGETS = {
        0x7100005bd0L, 0x71002f8a50L, 0x71002fdf90L, 0x7100315260L, 0x71003154a0L
    };
    private static final int CHUNK_SIZE = 1024 * 1024;

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

        Address knownVtableReference = toAddr(0x7101527458L);
        println("KNOWN_REF_BYTES\t" + knownVtableReference + "\t0x"
            + Long.toHexString(currentProgram.getMemory().getLong(knownVtableReference)));

        // Raw integer matches are candidates; surrounding data must be classified manually.
        long matches = 0;
        long relativeMatches = 0;
        for (MemoryBlock block : currentProgram.getMemory().getBlocks()) {
            if (!block.isInitialized() || block.getSize() < 8) continue;
            long offset = 0;
            while (offset < block.getSize()) {
                int requested = (int)Math.min(CHUNK_SIZE, block.getSize() - offset);
                byte[] buffer = new byte[requested];
                int read = currentProgram.getMemory().getBytes(block.getStart().add(offset), buffer);
                if (read <= 0) break;
                for (int i = 0; i < read; i++) {
                    if (i <= read - 8) {
                        long value = littleEndianLong(buffer, i);
                        for (long target : TARGETS) {
                            if (value == target) {
                                println("POINTER\t" + block.getName() + "\t"
                                    + block.getStart().add(offset + i) + "\t->\t"
                                    + currentProgram.getAddressFactory().getDefaultAddressSpace()
                                        .getAddress(target));
                                matches++;
                            }
                        }
                    }
                    if (!block.isExecute() && i <= read - 4) {
                        int displacement = littleEndianInt(buffer, i);
                        long slot = block.getStart().add(offset + i).getOffset();
                        for (long target : TARGETS) {
                            if (displacement == (int)(target - EXPECTED_BASE)) {
                                println("RELATIVE_DWORD_CANDIDATE\timage-offset\t" + block.getName()
                                    + "\t" + currentProgram.getAddressFactory()
                                        .getDefaultAddressSpace().getAddress(slot)
                                    + "\t->\t" + currentProgram.getAddressFactory()
                                        .getDefaultAddressSpace().getAddress(target));
                                relativeMatches++;
                            }
                            if (slot + (long)displacement == target) {
                                println("RELATIVE_DWORD_CANDIDATE\tfrom-slot\t" + block.getName()
                                    + "\t" + currentProgram.getAddressFactory()
                                        .getDefaultAddressSpace().getAddress(slot)
                                    + "\t->\t" + currentProgram.getAddressFactory()
                                        .getDefaultAddressSpace().getAddress(target));
                                relativeMatches++;
                            }
                            if (slot + 4L + displacement == target) {
                                println("RELATIVE_DWORD_CANDIDATE\tfrom-next\t" + block.getName()
                                    + "\t" + currentProgram.getAddressFactory()
                                        .getDefaultAddressSpace().getAddress(slot)
                                    + "\t->\t" + currentProgram.getAddressFactory()
                                        .getDefaultAddressSpace().getAddress(target));
                                relativeMatches++;
                            }
                            if (slot + (long)displacement == target) {
                                printNeighbors(block, block.getStart().add(offset + i));
                            }
                        }
                    }
                }
                if (offset + read >= block.getSize()) break;
                offset += read - 7;
            }
        }
        println("SUMMARY\tabsolute_qword_matches=" + matches + "\trelative_dword_matches="
            + relativeMatches + "\timage=" + normalized);
    }

    private void printNeighbors(MemoryBlock block, Address slot) throws Exception {
        for (int index = -8; index <= 8; index++) {
            Address entry = slot.add(index * 4L);
            if (!block.contains(entry) || !block.contains(entry.add(3))) continue;
            int displacement = currentProgram.getMemory().getInt(entry);
            long resolved = entry.getOffset() + (long)displacement;
            String target = "<outside-text>";
            if (resolved >= EXPECTED_BASE && resolved < EXPECTED_BASE + 0xd2fa78L) {
                Address targetAddress = currentProgram.getAddressFactory()
                    .getDefaultAddressSpace().getAddress(resolved);
                ghidra.program.model.listing.Function function = currentProgram
                    .getFunctionManager().getFunctionContaining(targetAddress);
                target = targetAddress.toString() + ":"
                    + (function == null ? "<no-function>" : function.getName());
            }
            println("REL_NEIGHBOR\t" + block.getName() + "\t" + entry + "\tindex="
                + index + "\traw=0x" + Integer.toHexString(displacement)
                + "\ttarget=" + target);
            for (ghidra.program.model.symbol.Reference ref
                : currentProgram.getReferenceManager().getReferencesTo(entry)) {
                ghidra.program.model.listing.Function caller = currentProgram
                    .getFunctionManager().getFunctionContaining(ref.getFromAddress());
                println("REL_XREF\t" + entry + "\t" + ref.getReferenceType()
                    + "\tfrom=" + ref.getFromAddress() + "\tcaller="
                    + (caller == null ? "<no-function>" : caller.getEntryPoint()));
            }
        }
    }

    private int littleEndianInt(byte[] bytes, int offset) {
        return (bytes[offset] & 0xff) | ((bytes[offset + 1] & 0xff) << 8)
            | ((bytes[offset + 2] & 0xff) << 16) | (bytes[offset + 3] << 24);
    }

    private long littleEndianLong(byte[] bytes, int offset) {
        long value = 0;
        for (int i = 7; i >= 0; i--) value = (value << 8) | (bytes[offset + i] & 0xffL);
        return value;
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
