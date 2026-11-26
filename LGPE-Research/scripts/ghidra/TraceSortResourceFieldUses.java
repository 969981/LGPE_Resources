import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import ghidra.program.model.mem.MemoryBlock;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.util.Locale;
import java.util.Map;
import java.util.TreeMap;
import java.util.regex.Pattern;

public class TraceSortResourceFieldUses extends GhidraScript {
    private static final long EXPECTED_BASE = 0x7100000000L;
    private static final String EXPECTED_NCA_ID = "2b7730a9e56498bbafac2002d4908c6b";
    private static final String EXPECTED_MAIN_SHA256 =
        "1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8";
    private static final int[] RESOURCE_OBJECT_OFFSETS = {
        0x340, 0x348, 0x350, 0x358, 0x360, 0x368
    };
    private static final Pattern OFFSET = Pattern.compile(
        "(?i)(?<![0-9a-f])#?0x(?:340|348|350|358|360|368)(?![0-9a-f])");

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
        println("SCOPE\tbounded executable-instruction scan for offsets exposed by"
            + " FUN_7100374530; matches are candidates and do not prove object identity");

        Map<String, Integer> counts = new TreeMap<>();
        for (int offset : RESOURCE_OBJECT_OFFSETS) counts.put(hex(offset), 0);
        int scanned = 0;
        int candidates = 0;
        for (MemoryBlock block : currentProgram.getMemory().getBlocks()) {
            if (!block.isExecute()) continue;
            InstructionIterator instructions = currentProgram.getListing()
                .getInstructions(block.getStart(), true);
            while (instructions.hasNext()) {
                monitor.checkCancelled();
                Instruction instruction = instructions.next();
                scanned++;
                String text = instruction.toString();
                java.util.regex.Matcher matcher = OFFSET.matcher(text);
                if (!matcher.find()) continue;
                matcher.reset();
                while (matcher.find()) {
                    String value = matcher.group().replace("#", "").toLowerCase(Locale.ROOT);
                    counts.put(value, counts.get(value) + 1);
                }
                Function function = currentProgram.getFunctionManager()
                    .getFunctionContaining(instruction.getAddress());
                println("OFFSET_INSN\taddress=" + instruction.getAddress()
                    + "\tfunction=" + (function == null ? "<no-function>" : function.getEntryPoint())
                    + "\tname=" + (function == null ? "<no-function>" : function.getName())
                    + "\tinstruction=" + text);
                candidates++;
            }
        }
        for (Map.Entry<String, Integer> entry : counts.entrySet()) {
            println("OFFSET_COUNT\toffset=" + entry.getKey() + "\tcount=" + entry.getValue());
        }
        println("SUMMARY\texecutable_instructions_scanned=" + scanned
            + "\tcandidate_instructions=" + candidates
            + "\tprogram=" + currentProgram.getName());
        if (!EXPECTED_MAIN_SHA256.equals(sha256(Path.of(executable.trim())))) {
            throw new IllegalStateException("source main hash changed during inspection");
        }
    }

    private static String hex(int value) {
        return "0x" + Integer.toHexString(value);
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
