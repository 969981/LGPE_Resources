import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.mem.MemoryBlock;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;

import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.security.MessageDigest;
import java.util.Locale;

public class InspectBseqDispatchBoundary extends GhidraScript {
    private static final String EXPECTED_MAIN_SHA256 =
        "1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8";
    private static final long EXPECTED_BASE = 0x7100000000L;
    private static final String EXPECTED_NCA_ID = "2b7730a9e56498bbafac2002d4908c6b";
    private static final long TABLE_CELL = 0x7101608df8L;
    private static final long EXPECTED_TABLE = 0x71015d4c70L;
    private static final long DUMMY_LABEL_TARGET = 0x7100ada060L;
    private static final int MAX_EXTRA_SLOTS = 4096;
    private static final int NON_EXECUTABLE_STOP_RUN = 8;

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

    private String bytesAt(Address address, int length) throws Exception {
        byte[] bytes = new byte[length];
        int count = currentProgram.getMemory().getBytes(address, bytes);
        if (count != length) throw new IllegalStateException("short memory read at " + address);
        StringBuilder output = new StringBuilder();
        for (byte value : bytes) {
            if (output.length() > 0) output.append(' ');
            output.append(String.format("%02x", value & 0xff));
        }
        return output.toString();
    }

    private void inspectDummyLabelTarget() throws Exception {
        Address target = toAddr(DUMMY_LABEL_TARGET);
        MemoryBlock block = currentProgram.getMemory().getBlock(target);
        if (block == null || !block.isInitialized() || !block.isExecute()) {
            throw new IllegalStateException("DummyLabel target is not initialized executable memory");
        }
        Instruction instruction = currentProgram.getListing().getInstructionAt(target);
        if (instruction == null || !instruction.getAddress().equals(target)) {
            throw new IllegalStateException("no instruction starts at the observed DummyLabel target");
        }
        String bytes = bytesAt(target, instruction.getLength());
        println("TARGET_INSTRUCTION\taddress=" + target
            + "\tmnemonic=" + instruction.getMnemonicString()
            + "\tlength=" + instruction.getLength()
            + "\tbytes_le=" + bytes
            + "\ttext=" + instruction);
        if (!"ret".equalsIgnoreCase(instruction.getMnemonicString())
            || instruction.getLength() != 4 || !"c0 03 5f d6".equals(bytes)) {
            throw new IllegalStateException("exact-build DummyLabel instruction differs from the recorded RET encoding");
        }

        ReferenceIterator references = currentProgram.getReferenceManager().getReferencesTo(target);
        int count = 0;
        while (references.hasNext()) {
            Reference reference = references.next();
            println("TARGET_INCOMING_REF\tfrom=" + reference.getFromAddress()
                + "\ttype=" + reference.getReferenceType()
                + "\toperand=" + reference.getOperandIndex());
            count++;
        }
        println("TARGET_INCOMING_SUMMARY\taddress=" + target + "\tcount=" + count);
    }

    private void inspectAdditionalTableSlots() throws Exception {
        Address cell = toAddr(TABLE_CELL);
        long table = currentProgram.getMemory().getLong(cell);
        if (table != EXPECTED_TABLE) {
            throw new IllegalStateException("dispatch table cell does not match the recorded exact-build address");
        }
        Address tableAddress = toAddr(table);
        int inspected = 0;
        int executable = 0;
        int trailingNonExecutable = 0;
        String stopReason = "configured_limit";
        for (int extra = 0; extra < MAX_EXTRA_SLOTS; extra++) {
            int index = 256 + extra;
            Address slotAddress = tableAddress.add(index * 8L);
            MemoryBlock slotBlock = currentProgram.getMemory().getBlock(slotAddress);
            if (slotBlock == null || !slotBlock.isInitialized()) {
                stopReason = "unmapped_or_uninitialized_slot";
                break;
            }
            long targetValue;
            try {
                targetValue = currentProgram.getMemory().getLong(slotAddress);
            } catch (Exception exception) {
                stopReason = "unreadable_slot";
                break;
            }
            Address targetAddress = currentProgram.getAddressFactory().getDefaultAddressSpace()
                .getAddress(targetValue);
            MemoryBlock targetBlock = currentProgram.getMemory().getBlock(targetAddress);
            boolean isExecutable = targetBlock != null && targetBlock.isExecute();
            println("EXTRA_DISPATCH_SLOT\tindex=" + index
                + "\taddress=" + slotAddress
                + "\ttarget=" + targetAddress
                + "\texecutable=" + isExecutable);
            inspected++;
            if (isExecutable) {
                executable++;
                trailingNonExecutable = 0;
            } else {
                trailingNonExecutable++;
                if (trailingNonExecutable >= NON_EXECUTABLE_STOP_RUN) {
                    stopReason = "configured_nonexec_run_observed";
                    break;
                }
            }
        }
        println("EXTRA_DISPATCH_SUMMARY\tcell=" + cell
            + "\ttable=" + tableAddress
            + "\tfirst_index=256"
            + "\tinspected=" + inspected
            + "\texecutable_targets=" + executable
            + "\ttrailing_nonexec=" + trailingNonExecutable
            + "\tmax_extra_slots=" + MAX_EXTRA_SLOTS
            + "\tstop_reason=" + stopReason
            + "\tfull_table_length_proven=false");
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
        String beforeHash = sha256(executable.trim());
        if (!EXPECTED_MAIN_SHA256.equals(beforeHash)) {
            throw new IllegalStateException("source main SHA-256 mismatch: " + beforeHash);
        }
        println("BUILD\tmain_sha256=" + beforeHash
            + "\timage_base=0x" + Long.toHexString(currentProgram.getImageBase().getOffset())
            + "\tgame=Pokemon-Lets-Go-Pikachu\tversion=1.0.2\tnca_id=" + EXPECTED_NCA_ID);
        inspectDummyLabelTarget();
        inspectAdditionalTableSlots();
        String afterHash = sha256(executable.trim());
        if (!EXPECTED_MAIN_SHA256.equals(afterHash) || !beforeHash.equals(afterHash)) {
            throw new IllegalStateException("source main changed during read-only analysis");
        }
        println("SUMMARY\tmain_sha256=" + afterHash
            + "\tread_only_source=true\tread_only_project=true");
    }
}
