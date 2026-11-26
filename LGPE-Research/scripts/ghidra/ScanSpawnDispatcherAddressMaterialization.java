import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import ghidra.program.model.mem.MemoryBlock;

import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.security.MessageDigest;
import java.util.Locale;

/** Bounded code scan for PC-relative materialization of one orphaned dispatcher. */
public class ScanSpawnDispatcherAddressMaterialization extends GhidraScript {
    private static final String EXPECTED_SHA256 =
        "1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8";
    private static final long EXPECTED_BASE = 0x7100000000L;
    private static final long TARGET = 0x71002f8a50L;
    private static final String NCA_ID = "2b7730a9e56498bbafac2002d4908c6b";

    private String sha256(String path) throws Exception {
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        try (InputStream in = Files.newInputStream(Paths.get(path))) {
            byte[] buffer = new byte[1024 * 1024];
            int count;
            while ((count = in.read(buffer)) != -1) digest.update(buffer, 0, count);
        }
        StringBuilder result = new StringBuilder();
        for (byte b : digest.digest()) result.append(String.format("%02x", b & 0xff));
        return result.toString();
    }

    @Override
    public void run() throws Exception {
        String executable = currentProgram.getExecutablePath();
        String normalized = executable == null ? "" : executable.trim().replace('\\', '/');
        String lower = normalized.toLowerCase(Locale.ROOT);
        if (currentProgram.getImageBase().getOffset() != EXPECTED_BASE
            || !lower.contains(NCA_ID) || !lower.endsWith("/0/main")) {
            throw new IllegalStateException("not the recorded local LGPE Pikachu 1.0.2 main");
        }
        String actualSha = sha256(normalized);
        println("PROGRAM\t" + normalized + "\tbase=" + currentProgram.getImageBase()
            + "\tsha256=" + actualSha);
        if (!EXPECTED_SHA256.equals(actualSha)) {
            throw new IllegalStateException("main SHA-256 mismatch: " + actualSha);
        }

        Address target = currentProgram.getAddressFactory().getDefaultAddressSpace()
            .getAddress(TARGET);
        Address targetPage = currentProgram.getAddressFactory().getDefaultAddressSpace()
            .getAddress(TARGET & ~0xfffL);
        int executableBlocks = 0;
        long instructionCount = 0;
        int pcRelativeCount = 0;
        int pageCandidates = 0;
        int exactTargetCandidates = 0;
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
                pcRelativeCount++;
                String operands = instruction.toString().toLowerCase(Locale.ROOT);
                if (!operands.contains("2f8")) continue;
                pageCandidates++;
                boolean exact = operands.contains(target.toString().toLowerCase(Locale.ROOT));
                if (exact) exactTargetCandidates++;
                println("PCREL_CANDIDATE\t" + instruction.getAddress()
                    + "\t" + instruction + "\tpage=" + targetPage
                    + "\texact_target_text=" + exact);
                Address next = instruction.getAddress().add(instruction.getLength());
                for (int i = 0; i < 4; i++) {
                    Instruction following = currentProgram.getListing().getInstructionAt(next);
                    if (following == null || following.getAddress().getOffset()
                        >= instruction.getAddress().getOffset() + 0x20) break;
                    println("PCREL_CONTEXT\t" + following.getAddress() + "\t" + following);
                    next = next.add(following.getLength());
                }
            }
        }
        println("SUMMARY\tsha256=" + actualSha + "\tbase=0x"
            + Long.toHexString(currentProgram.getImageBase().getOffset())
            + "\ttarget=" + target + "\ttarget_page=" + targetPage
            + "\texecutable_blocks=" + executableBlocks
            + "\tinstructions=" + instructionCount + "\tadr_adrp=" + pcRelativeCount
            + "\t2f8_candidates=" + pageCandidates
            + "\texact_target_candidates=" + exactTargetCandidates
            + "\tread_only=true");
    }
}
