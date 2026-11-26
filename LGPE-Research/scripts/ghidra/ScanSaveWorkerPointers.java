import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import ghidra.program.model.listing.Function;
import ghidra.program.model.mem.MemoryBlock;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;

import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.security.MessageDigest;
import java.util.Locale;

/** Bounded raw pointer-value census for save worker functions in exact LGPE 1.0.2 main. */
public class ScanSaveWorkerPointers extends GhidraScript {
    private static final String EXPECTED_MAIN_SHA256 =
        "1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8";
    private static final long EXPECTED_BASE = 0x7100000000L;
    private static final String EXPECTED_NCA_ID = "2b7730a9e56498bbafac2002d4908c6b";
    private static final long[] TARGETS = {
        0x7100024d70L, 0x7100027200L, 0x7100027440L, 0x71000275f0L
    };
    private static final String[] LABELS = {
        "SAVE_WORKER", "SAVE_ID_HELPER", "QUEUE_HELPER", "STATUS_HELPER"
    };
    private static final int CHUNK_SIZE = 1024 * 1024;
    private static final int MAX_CANDIDATE_LINES = 100;
    private static final int MAX_ADDRESS_CANDIDATE_LINES = 200;

    @Override
    public void run() throws Exception {
        String executable = currentProgram.getExecutablePath();
        String normalized = executable == null ? "" : executable.trim().replace('\\', '/');
        if (currentProgram.getImageBase().getOffset() != EXPECTED_BASE
            || !normalized.toLowerCase(Locale.ROOT).contains(EXPECTED_NCA_ID)
            || !normalized.toLowerCase(Locale.ROOT).endsWith("/0/main")) {
            throw new IllegalStateException("not the recorded LGPE 1.0.2 main program");
        }

        String sourceHashBefore = sha256(executable.trim());
        if (!EXPECTED_MAIN_SHA256.equals(sourceHashBefore)) {
            throw new IllegalStateException("source main SHA-256 mismatch: " + sourceHashBefore);
        }

        for (int i = 0; i < TARGETS.length; i++) {
            Address target = toAddr(TARGETS[i]);
            Function function = currentProgram.getFunctionManager().getFunctionAt(target);
            println("TARGET\t" + target + "\t" + LABELS[i] + "\tfunction="
                + (function == null ? "<none>" : function.getName()) + "\timage_offset=0x"
                + Long.toHexString(TARGETS[i] - EXPECTED_BASE));
            ReferenceIterator incoming = currentProgram.getReferenceManager().getReferencesTo(target);
            int incomingCount = 0;
            while (incoming.hasNext()) {
                Reference reference = incoming.next();
                println("TARGET_XREF\t" + LABELS[i] + "\tfrom=" + reference.getFromAddress()
                    + "\ttype=" + reference.getReferenceType());
                incomingCount++;
            }
            println("TARGET_XREF_SUMMARY\t" + LABELS[i] + "\tcount=" + incomingCount);
        }

        long[] qwordMatches = new long[TARGETS.length];
        long[] imageOffsetMatches = new long[TARGETS.length];
        long bytesScanned = 0;
        int initializedBlocks = 0;
        int candidateLines = 0;
        boolean candidateOutputTruncated = false;

        for (MemoryBlock block : currentProgram.getMemory().getBlocks()) {
            if (!block.isInitialized() || !block.isRead() || block.getSize() < 4) continue;
            initializedBlocks++;
            long offset = 0;
            while (offset < block.getSize()) {
                monitor.checkCancelled();
                int requested = (int)Math.min(CHUNK_SIZE, block.getSize() - offset);
                byte[] buffer = new byte[requested];
                int read = currentProgram.getMemory().getBytes(block.getStart().add(offset), buffer);
                if (read <= 0) break;
                bytesScanned += Math.max(0, read - (offset == 0 ? 0 : 7));
                Address chunkStart = block.getStart().add(offset);

                for (int i = 0; i < read; i++) {
                    if (i <= read - 8) {
                        long value = littleEndianLong(buffer, i);
                        for (int targetIndex = 0; targetIndex < TARGETS.length; targetIndex++) {
                            if (value != TARGETS[targetIndex]) continue;
                            qwordMatches[targetIndex]++;
                            Address slot = chunkStart.add(i);
                            if (candidateLines < MAX_CANDIDATE_LINES) {
                                printCandidate("ABSOLUTE_QWORD", block, slot,
                                    LABELS[targetIndex], toAddr(TARGETS[targetIndex]));
                                candidateLines++;
                            } else {
                                candidateOutputTruncated = true;
                            }
                        }
                    }

                    if (!block.isExecute() && (offset == 0 || i >= 4) && i <= read - 4) {
                        int value = littleEndianInt(buffer, i);
                        for (int targetIndex = 0; targetIndex < TARGETS.length; targetIndex++) {
                            if (value != (int)(TARGETS[targetIndex] - EXPECTED_BASE)) continue;
                            imageOffsetMatches[targetIndex]++;
                            if (candidateLines < MAX_CANDIDATE_LINES) {
                                Address slot = chunkStart.add(i);
                                printCandidate("IMAGE_OFFSET_DWORD", block, slot,
                                    LABELS[targetIndex], toAddr(TARGETS[targetIndex]));
                                candidateLines++;
                            } else {
                                candidateOutputTruncated = true;
                            }
                        }
                    }
                }

                if (offset + read >= block.getSize()) break;
                offset += read - 7;
            }
        }

        Address worker = toAddr(TARGETS[0]);
        Address workerPage = toAddr(TARGETS[0] & ~0xfffL);
        String workerText = worker.toString().toLowerCase(Locale.ROOT);
        String workerPageText = workerPage.toString().toLowerCase(Locale.ROOT);
        String workerPageRegister = "";
        long executableBlocks = 0;
        long instructionCount = 0;
        long adrAdrpCount = 0;
        long addressPageCandidates = 0;
        long pagePlusOffsetCandidates = 0;
        long exactWorkerCandidates = 0;
        long addressCandidateLines = 0;
        boolean addressCandidateOutputTruncated = false;
        for (MemoryBlock block : currentProgram.getMemory().getBlocks()) {
            if (!block.isInitialized() || !block.isExecute()) continue;
            executableBlocks++;
            InstructionIterator instructions = currentProgram.getListing()
                .getInstructions(block.getStart(), true);
            while (instructions.hasNext()) {
                monitor.checkCancelled();
                Instruction instruction = instructions.next();
                instructionCount++;
                String mnemonic = instruction.getMnemonicString().toUpperCase(Locale.ROOT);
                if (!mnemonic.equals("ADR") && !mnemonic.equals("ADRP")) continue;
                adrAdrpCount++;
                String rendered = instruction.toString();
                String lowerRendered = rendered.toLowerCase(Locale.ROOT);
                if (!lowerRendered.contains(workerPageText)
                    && !lowerRendered.contains(workerText)) continue;

                addressPageCandidates++;
                String[] addressParts = rendered.replace(',', ' ').trim().split("\\s+");
                workerPageRegister = addressParts.length > 1
                    ? addressParts[1].toLowerCase(Locale.ROOT) : "";
                if (lowerRendered.contains(workerText)) exactWorkerCandidates++;
                if (addressCandidateLines < MAX_ADDRESS_CANDIDATE_LINES) {
                    println("ADDRESS_PAGE_CANDIDATE\t" + instruction.getAddress() + "\t"
                        + rendered + "\tregister=" + workerPageRegister);
                    addressCandidateLines++;
                } else {
                    addressCandidateOutputTruncated = true;
                }

                Address next = instruction.getAddress().add(instruction.getLength());
                for (int followingIndex = 0; followingIndex < 8; followingIndex++) {
                    Instruction following = currentProgram.getListing().getInstructionAt(next);
                    if (following == null || next.getOffset()
                        >= instruction.getAddress().getOffset() + 0x20) break;
                    String followingText = following.toString();
                    if (isPageOffsetAdd(followingText, workerPageRegister,
                        TARGETS[0] & 0xfffL)) {
                        pagePlusOffsetCandidates++;
                        if (addressCandidateLines < MAX_ADDRESS_CANDIDATE_LINES) {
                            println("PAGE_PLUS_OFFSET_CANDIDATE\t" + instruction.getAddress()
                                + "\t" + following.getAddress() + "\tregister="
                                + workerPageRegister + "\t" + followingText);
                            addressCandidateLines++;
                        } else {
                            addressCandidateOutputTruncated = true;
                        }
                    }
                    if (addressCandidateLines < MAX_ADDRESS_CANDIDATE_LINES) {
                        println("ADDRESS_PAGE_CONTEXT\t" + following.getAddress()
                            + "\t" + followingText);
                        addressCandidateLines++;
                    } else {
                        addressCandidateOutputTruncated = true;
                    }
                    next = next.add(following.getLength());
                }
            }
        }

        long qwordTotal = 0;
        long imageOffsetTotal = 0;
        for (int i = 0; i < TARGETS.length; i++) {
            qwordTotal += qwordMatches[i];
            imageOffsetTotal += imageOffsetMatches[i];
            println("TARGET_SCAN_SUMMARY\t" + LABELS[i] + "\tabsolute_qword="
                + qwordMatches[i] + "\timage_offset_dword=" + imageOffsetMatches[i]);
        }

        String sourceHashAfter = sha256(executable.trim());
        if (!sourceHashBefore.equals(sourceHashAfter)) {
            throw new IllegalStateException("source main changed during read-only inspection");
        }
        println("QWORD_SCAN_SUMMARY\tmatches=" + qwordTotal);
        println("IMAGE_OFFSET_SCAN_SUMMARY\tmatches=" + imageOffsetTotal);
        println("ADDRESS_MATERIALIZATION_SUMMARY\texecutable_blocks=" + executableBlocks
            + "\tinstruction_count=" + instructionCount + "\tadr_adrp=" + adrAdrpCount
            + "\tpage_candidates=" + addressPageCandidates
            + "\tpage_plus_offset_candidates=" + pagePlusOffsetCandidates
            + "\texact_worker_candidates=" + exactWorkerCandidates
            + "\tcandidate_lines=" + addressCandidateLines
            + "\tcandidate_output_truncated=" + addressCandidateOutputTruncated);
        println("SUMMARY\tmain_sha256=" + sourceHashAfter + "\timage_base=0x"
            + Long.toHexString(currentProgram.getImageBase().getOffset())
            + "\tinitialized_blocks=" + initializedBlocks + "\tbytes_scanned=" + bytesScanned
            + "\tcandidate_lines=" + candidateLines + "\tcandidate_output_truncated="
            + candidateOutputTruncated + "\tsourceHashUnchanged=true\treadOnly=true");
    }

    private void printCandidate(String kind, MemoryBlock block, Address slot, String label,
                                Address target) {
        println("POINTER_CANDIDATE\t" + kind + "\t" + block.getName() + "\t" + slot
            + "\t" + label + "\t->\t" + target);
        ReferenceIterator references = currentProgram.getReferenceManager().getReferencesTo(slot);
        while (references.hasNext()) {
            Reference reference = references.next();
            Function caller = currentProgram.getFunctionManager()
                .getFunctionContaining(reference.getFromAddress());
            println("POINTER_SLOT_XREF\t" + slot + "\t" + reference.getReferenceType()
                + "\tfrom=" + reference.getFromAddress() + "\tcaller="
                + (caller == null ? "<no-function>" : caller.getEntryPoint()));
        }
    }

    private int littleEndianInt(byte[] bytes, int offset) {
        return (bytes[offset] & 0xff) | ((bytes[offset + 1] & 0xff) << 8)
            | ((bytes[offset + 2] & 0xff) << 16) | (bytes[offset + 3] << 24);
    }

    private boolean isPageOffsetAdd(String instruction, String pageRegister, long offset) {
        if (pageRegister == null || pageRegister.isEmpty()) return false;
        String[] parts = instruction.toLowerCase(Locale.ROOT)
            .replace(',', ' ').trim().split("\\s+");
        if (parts.length < 4 || !parts[0].equals("add") || !parts[2].equals(pageRegister)) {
            return false;
        }
        for (int i = 3; i < parts.length; i++) {
            String value = parts[i].replace("#", "");
            if (value.startsWith("0x")) value = value.substring(2);
            try {
                if (Long.parseLong(value, 16) == offset) return true;
            } catch (NumberFormatException ignored) {
                // Other operands, including register extensions, are not offsets.
            }
        }
        return false;
    }

    private long littleEndianLong(byte[] bytes, int offset) {
        long value = 0;
        for (int i = 7; i >= 0; i--) value = (value << 8) | (bytes[offset + i] & 0xffL);
        return value;
    }

    private String sha256(String path) throws Exception {
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        try (InputStream input = Files.newInputStream(Paths.get(path))) {
            byte[] buffer = new byte[1024 * 1024];
            int count;
            while ((count = input.read(buffer)) >= 0) digest.update(buffer, 0, count);
        }
        StringBuilder result = new StringBuilder();
        for (byte value : digest.digest()) result.append(String.format("%02x", value & 0xff));
        return result.toString();
    }
}
