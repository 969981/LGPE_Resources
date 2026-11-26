import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;

import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.security.MessageDigest;
import java.util.Locale;

public class InspectSequenceCallbacks extends GhidraScript {
    private static final String EXPECTED_MAIN_SHA256 =
        "1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8";
    private static final long EXPECTED_BASE = 0x7100000000L;
    private static final String EXPECTED_NCA_ID = "2b7730a9e56498bbafac2002d4908c6b";
    private static final String[] TARGETS = {
        "7100aa2310", "7100aa2370", "7100aa0eb0",
        "7100ada060", "7100ade320", "7100aeb5e0", "7100aeb6b0", "7100aeb700"
    };

    private String sha256(String path) throws Exception {
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        try (InputStream stream = Files.newInputStream(Paths.get(path))) {
            byte[] buffer = new byte[1024 * 1024];
            int count;
            while ((count = stream.read(buffer)) >= 0) {
                if (count > 0) digest.update(buffer, 0, count);
            }
        }
        StringBuilder output = new StringBuilder();
        for (byte value : digest.digest()) output.append(String.format("%02x", value));
        return output.toString();
    }

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
        if (!EXPECTED_MAIN_SHA256.equals(actualHash)) {
            throw new IllegalStateException("source main SHA-256 mismatch: " + actualHash);
        }

        DecompInterface decompiler = new DecompInterface();
        decompiler.openProgram(currentProgram);
        int created = 0;
        int decompiled = 0;
        int failures = 0;
        for (String target : TARGETS) {
            Address entry = toAddr(target);
            Function function = currentProgram.getFunctionManager().getFunctionAt(entry);
            if (function == null) {
                disassemble(entry);
                function = createFunction(entry, null);
                if (function != null) created++;
            }
            if (function == null || !function.getEntryPoint().equals(entry)) {
                println("FUNCTION_CREATE_FAILED\t" + entry);
                failures++;
                continue;
            }
            println("FUNCTION_BEGIN\t" + function.getEntryPoint() + "\t" + function.getName()
                + "\tbytes=" + function.getBody().getNumAddresses());
            InstructionIterator instructions =
                currentProgram.getListing().getInstructions(function.getBody(), true);
            int instructionCount = 0;
            while (instructions.hasNext()) {
                Instruction instruction = instructions.next();
                println("INSN\t" + instruction.getAddress() + "\t" + instruction);
                instructionCount++;
            }
            DecompileResults result = decompiler.decompileFunction(function, 120, monitor);
            if (!result.decompileCompleted() || result.getDecompiledFunction() == null) {
                println("DECOMPILE_FAILED\t" + entry + "\t" + result.getErrorMessage());
                failures++;
            } else {
                println("DECOMPILED_BEGIN\t" + entry + "\tchars="
                    + result.getDecompiledFunction().getC().length());
                println(result.getDecompiledFunction().getC());
                println("DECOMPILED_END\t" + entry);
                decompiled++;
            }
            println("FUNCTION_END\t" + entry + "\tinstructions=" + instructionCount);
        }
        decompiler.dispose();
        String finalHash = sha256(executable.trim());
        if (!EXPECTED_MAIN_SHA256.equals(finalHash)) {
            throw new IllegalStateException("source main changed during analysis: " + finalHash);
        }
        println("SUMMARY\tmain_sha256=" + finalHash + "\timage_base=0x"
            + Long.toHexString(currentProgram.getImageBase().getOffset())
            + "\ttargets=" + TARGETS.length + "\tcreated_functions=" + created
            + "\tdecompiled=" + decompiled + "\tfailures=" + failures
            + "\tread_only_source=true\tproject_database_modified=true");
    }
}
