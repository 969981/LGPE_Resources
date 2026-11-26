import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionIterator;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;

import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/** Finds object-base store sites covering both 128-bit RNG state pairs. */
public class ScanSpawnRngStateStores extends GhidraScript {
    private static final String EXPECTED_SHA256 =
        "1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8";
    private static final long EXPECTED_BASE = 0x7100000000L;
    private static final long POSITIVE_CONTROL = 0x71002fdf90L;
    private static final String NCA_ID = "2b7730a9e56498bbafac2002d4908c6b";
    private static final Pattern MEMORY_OPERAND = Pattern.compile(
        "\\[(x[0-9]+|sp),\\s*#0x(80|88|90|98)\\]");

    private static final class StoreSet {
        final Function function;
        final String base;
        final Set<Integer> offsets = new HashSet<>();
        final ArrayList<String> instructions = new ArrayList<>();
        StoreSet(Function function, String base) {
            this.function = function;
            this.base = base;
        }
    }

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

    private int incomingCalls(Address entry) {
        int count = 0;
        ReferenceIterator references = currentProgram.getReferenceManager().getReferencesTo(entry);
        while (references.hasNext()) {
            Reference reference = references.next();
            if (reference.getReferenceType().isCall()) count++;
        }
        return count;
    }

    private void collect(Function function, Instruction instruction,
        Map<String, StoreSet> byBase, long[] matchingStores) {
        String mnemonic = instruction.getMnemonicString().toUpperCase(Locale.ROOT);
        if (!mnemonic.startsWith("STR") && !mnemonic.equals("STP")) return;
        String text = instruction.toString().toLowerCase(Locale.ROOT);
        Matcher matcher = MEMORY_OPERAND.matcher(text);
        if (!matcher.find()) return;
        String base = matcher.group(1);
        int offset = Integer.parseInt(matcher.group(2), 16);
        if (base.equals("sp")) return;
        boolean qwordStore = text.matches(".*\\bstr\\s+x(?:[0-9]+|zr)\\s*,.*")
            || (mnemonic.equals("STP")
                && text.matches(".*\\bstp\\s+x(?:[0-9]+|zr)\\s*,\\s*x(?:[0-9]+|zr)\\s*,.*"));
        if (!qwordStore) return;

        StoreSet stores = byBase.computeIfAbsent(base, key -> new StoreSet(function, key));
        stores.instructions.add(instruction.getAddress() + "\t" + instruction);
        stores.offsets.add(offset);
        if (mnemonic.equals("STP") && offset == 0x80) stores.offsets.add(0x88);
        if (mnemonic.equals("STP") && offset == 0x90) stores.offsets.add(0x98);
        matchingStores[0]++;
    }

    @Override
    public void run() throws Exception {
        String executable = currentProgram.getExecutablePath();
        String normalized = executable == null ? "" : executable.trim().replace('\\', '/');
        String lowerPath = normalized.toLowerCase(Locale.ROOT);
        if (currentProgram.getImageBase().getOffset() != EXPECTED_BASE
            || !lowerPath.contains(NCA_ID) || !lowerPath.endsWith("/0/main")) {
            throw new IllegalStateException("not the recorded local LGPE Pikachu 1.0.2 main");
        }
        String actualSha = sha256(normalized);
        println("PROGRAM\t" + normalized + "\tbase=" + currentProgram.getImageBase()
            + "\tsha256=" + actualSha);
        if (!EXPECTED_SHA256.equals(actualSha)) {
            throw new IllegalStateException("main SHA-256 mismatch: " + actualSha);
        }

        long functionCount = 0;
        long instructionCount = 0;
        long[] matchingStores = {0};
        int pair80Count = 0;
        int pair90Count = 0;
        int fourFieldCount = 0;
        boolean controlSeen = false;
        ArrayList<StoreSet> controlStores = new ArrayList<>();
        FunctionIterator functions = currentProgram.getFunctionManager().getFunctions(true);
        while (functions.hasNext()) {
            monitor.checkCancelled();
            Function function = functions.next();
            functionCount++;
            Map<String, StoreSet> byBase = new HashMap<>();
            InstructionIterator instructions = currentProgram.getListing()
                .getInstructions(function.getBody(), true);
            while (instructions.hasNext()) {
                instructionCount++;
                collect(function, instructions.next(), byBase, matchingStores);
            }
            for (StoreSet stores : byBase.values()) {
                boolean pair80 = stores.offsets.contains(0x80) && stores.offsets.contains(0x88);
                boolean pair90 = stores.offsets.contains(0x90) && stores.offsets.contains(0x98);
                if (pair80) pair80Count++;
                if (pair90) pair90Count++;
                if (!pair80 || !pair90) continue;
                fourFieldCount++;
                boolean positive = function.getEntryPoint().getOffset() == POSITIVE_CONTROL;
                if (positive) {
                    controlSeen = true;
                    controlStores.add(stores);
                }
            }
        }
        if (!controlSeen) {
            throw new IllegalStateException("candidate's four state fields not recovered; scan control failed");
        }
        for (StoreSet stores : controlStores) {
            Function function = stores.function;
            println("POSITIVE_CONTROL_WRITER\t" + function.getEntryPoint()
                + "\t" + function.getName() + "\tbase=" + stores.base
                + "\tbytes=" + function.getBody().getNumAddresses()
                + "\tincoming_calls=" + incomingCalls(function.getEntryPoint()));
            for (String line : stores.instructions) println("CONTROL_STORE\t" + line);
        }
        println("SUMMARY\tsha256=" + actualSha + "\tbase=0x"
            + Long.toHexString(currentProgram.getImageBase().getOffset())
            + "\tfunctions=" + functionCount + "\tinstructions=" + instructionCount
            + "\tmatching_qword_store_instructions=" + matchingStores[0]
            + "\tbase_registers_writing_0x80_0x88=" + pair80Count
            + "\tbase_registers_writing_0x90_0x98=" + pair90Count
            + "\tfour_field_writers=" + fourFieldCount
            + "\tpositive_control=true\tread_only=true");
    }
}
