import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.lang.Register;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionIterator;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import ghidra.program.model.scalar.Scalar;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.util.HashSet;
import java.util.Set;

public class ScanSpawnEntityDescriptorWrites extends GhidraScript {
    private static final String EXPECTED_SHA256 =
        "1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8";
    private static final long EXPECTED_BASE = 0x7100000000L;
    private static final long[] OFFSETS = {0x3e8L, 0x3f0L, 0x3f8L, 0x400L};

    private String sha256(Path path) throws Exception {
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        try (InputStream input = Files.newInputStream(path)) {
            byte[] buffer = new byte[1024 * 1024];
            int count;
            while ((count = input.read(buffer)) != -1) digest.update(buffer, 0, count);
        }
        StringBuilder value = new StringBuilder();
        for (byte b : digest.digest()) value.append(String.format("%02x", b & 0xff));
        return value.toString();
    }

    private boolean isStore(String mnemonic) {
        return mnemonic.startsWith("STR") || mnemonic.startsWith("STP")
            || mnemonic.startsWith("STUR") || mnemonic.startsWith("STNP")
            || mnemonic.startsWith("STXR") || mnemonic.startsWith("STL");
    }

    private boolean hasAddressOffset(Instruction instruction, long expected) {
        for (int operand = 0; operand < instruction.getNumOperands(); operand++) {
            boolean hasBaseRegister = false;
            boolean hasMatchingScalar = false;
            for (Object object : instruction.getOpObjects(operand)) {
                if (object instanceof Register) hasBaseRegister = true;
                if (object instanceof Scalar
                    && ((Scalar) object).getUnsignedValue() == expected) {
                    hasMatchingScalar = true;
                }
            }
            if (hasBaseRegister && hasMatchingScalar) return true;
        }
        return false;
    }

    @Override
    public void run() throws Exception {
        String executable = currentProgram.getExecutablePath();
        String actualSha = sha256(Path.of(executable));
        println("PROGRAM\t" + executable + "\tbase=" + currentProgram.getImageBase()
            + "\tsha256=" + actualSha);
        if (currentProgram.getImageBase().getOffset() != EXPECTED_BASE
            || !EXPECTED_SHA256.equals(actualSha)
            || !executable.replace('\\', '/').toLowerCase().endsWith("/0/main")) {
            throw new IllegalStateException("not the exact local Let's Go Pikachu 1.0.2 main");
        }

        long functions = 0;
        long instructions = 0;
        long writes = 0;
        Set<String> seen = new HashSet<>();
        FunctionIterator functionIterator = currentProgram.getFunctionManager().getFunctions(true);
        while (functionIterator.hasNext()) {
            monitor.checkCancelled();
            Function function = functionIterator.next();
            functions++;
            InstructionIterator iterator = currentProgram.getListing()
                .getInstructions(function.getBody(), true);
            while (iterator.hasNext()) {
                monitor.checkCancelled();
                Instruction instruction = iterator.next();
                instructions++;
                String mnemonic = instruction.getMnemonicString().toUpperCase();
                if (!isStore(mnemonic)) continue;
                for (long offset : OFFSETS) {
                    if (!hasAddressOffset(instruction, offset)) continue;
                    String key = instruction.getAddress().toString();
                    if (seen.add(key)) {
                        writes++;
                        println("WRITE\t" + instruction.getAddress() + "\towner="
                            + function.getEntryPoint() + "\toffset=0x"
                            + Long.toHexString(offset) + "\t" + instruction);
                    }
                }
            }
        }
        println("SUMMARY\tsha256=" + actualSha + "\tbase=0x"
            + Long.toHexString(currentProgram.getImageBase().getOffset())
            + "\tfunctions=" + functions + "\tinstructions=" + instructions
            + "\tmatching_stores=" + writes + "\tread_only=true");
    }
}
