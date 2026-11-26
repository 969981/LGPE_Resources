import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.address.AddressSetView;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import ghidra.program.model.mem.MemoryBlock;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;
import ghidra.program.model.symbol.ReferenceManager;

import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.util.HashSet;
import java.util.Locale;
import java.util.Set;

/** Exact-build, read-only audit for incoming direct control flow and static pointers. */
public class ScanSpawnDispatcherIncomingEdges extends GhidraScript {
    private static final String EXPECTED_SHA256 =
        "1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8";
    private static final String NCA_ID = "2b7730a9e56498bbafac2002d4908c6b";
    private static final long EXPECTED_BASE = 0x7100000000L;
    private static final long DISPATCHER_OFFSET = 0x2f8a50L;
    private static final int CHUNK_SIZE = 1024 * 1024;

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

    private long littleEndianLong(byte[] bytes, int offset) {
        long value = 0;
        for (int i = 7; i >= 0; i--) value = (value << 8) | (bytes[offset + i] & 0xffL);
        return value;
    }

    private int littleEndianInt(byte[] bytes, int offset) {
        return (bytes[offset] & 0xff) | ((bytes[offset + 1] & 0xff) << 8)
            | ((bytes[offset + 2] & 0xff) << 16) | (bytes[offset + 3] << 24);
    }

    private boolean contains(AddressSetView body, long offset) {
        try {
            return body.contains(currentProgram.getAddressFactory()
                .getDefaultAddressSpace().getAddress(offset));
        } catch (Exception ignored) {
            return false;
        }
    }

    private void printRelativeContext(MemoryBlock block, Address slot) throws Exception {
        Address start = slot.subtract(16);
        if (start.compareTo(block.getStart()) < 0) start = block.getStart();
        Address end = slot.add(31);
        if (end.compareTo(block.getEnd()) > 0) end = block.getEnd();
        int count = (int)(end.subtract(start) + 1);
        byte[] bytes = new byte[count];
        currentProgram.getMemory().getBytes(start, bytes);
        StringBuilder hex = new StringBuilder();
        for (byte value : bytes) hex.append(String.format("%02x", value & 0xff));
        println("RELATIVE_CONTEXT\tblock=" + block.getName() + "\tstart=" + start
            + "\tslot=" + slot + "\talignment=" + (slot.getOffset() & 3)
            + "\tbytes=" + hex);
        ReferenceIterator references = currentProgram.getReferenceManager().getReferencesTo(slot);
        int countReferences = 0;
        while (references.hasNext()) {
            Reference reference = references.next();
            countReferences++;
            Function owner = currentProgram.getFunctionManager()
                .getFunctionContaining(reference.getFromAddress());
            println("RELATIVE_SLOT_XREF\tslot=" + slot + "\tfrom="
                + reference.getFromAddress() + "\ttype=" + reference.getReferenceType()
                + "\towner=" + (owner == null ? "<none>" : owner.getEntryPoint()));
        }
        println("RELATIVE_SLOT_XREF_COUNT\tslot=" + slot + "\tcount=" + countReferences);
    }

    private void printWindowReferences(MemoryBlock block, Address center,
        Set<String> queriedTargets, Set<String> emittedReferences) throws Exception {
        Address start = center.subtract(0x40);
        if (start.compareTo(block.getStart()) < 0) start = block.getStart();
        Address end = center.add(0x40);
        if (end.compareTo(block.getEnd()) > 0) end = block.getEnd();
        int count = 0;
        for (Address target = start; target.compareTo(end) <= 0; target = target.add(1)) {
            if (!queriedTargets.add(target.toString())) continue;
            ReferenceIterator references = currentProgram.getReferenceManager()
                .getReferencesTo(target);
            while (references.hasNext()) {
                Reference reference = references.next();
                String key = target + ":" + reference.getFromAddress() + ":"
                    + reference.getReferenceType();
                if (!emittedReferences.add(key)) continue;
                Function owner = currentProgram.getFunctionManager()
                    .getFunctionContaining(reference.getFromAddress());
                println("RELATIVE_WINDOW_XREF\twindow_center=" + center + "\ttarget="
                    + target + "\tfrom=" + reference.getFromAddress() + "\ttype="
                    + reference.getReferenceType() + "\towner="
                    + (owner == null ? "<none>" : owner.getEntryPoint()));
                count++;
            }
        }
        println("RELATIVE_WINDOW_XREF_COUNT\tcenter=" + center + "\tstart=" + start
            + "\tend=" + end + "\tnew_references=" + count);
    }

    @Override
    public void run() throws Exception {
        String executable = currentProgram.getExecutablePath();
        String normalized = executable == null ? "" : executable.trim().replace('\\', '/');
        String lower = normalized.toLowerCase(Locale.ROOT);
        if (currentProgram.getImageBase().getOffset() != EXPECTED_BASE
            || !lower.contains(NCA_ID) || !lower.endsWith("/0/main")) {
            throw new IllegalStateException("not the local LGPE Pikachu 1.0.2 main");
        }
        String actualSha = sha256(Path.of(executable.trim()));
        println("PROGRAM\t" + normalized + "\tbase=" + currentProgram.getImageBase()
            + "\tsha256=" + actualSha);
        if (!EXPECTED_SHA256.equals(actualSha)) {
            throw new IllegalStateException("main SHA-256 mismatch: " + actualSha);
        }

        Address entry = currentProgram.getImageBase().add(DISPATCHER_OFFSET);
        Function dispatcher = currentProgram.getFunctionManager().getFunctionAt(entry);
        if (dispatcher == null) throw new IllegalStateException("dispatcher entry is undefined");
        AddressSetView body = dispatcher.getBody();
        println("DISPATCHER\t" + entry + "\tname=" + dispatcher.getName()
            + "\tbytes=" + body.getNumAddresses() + "\tranges=" + body.getNumAddressRanges()
            + "\tmin=" + body.getMinAddress() + "\tmax=" + body.getMaxAddress());

        long executableBlocks = 0;
        long scannedInstructions = 0;
        long directBranchTargets = 0;
        long computedBranchInstructions = 0;
        for (MemoryBlock block : currentProgram.getMemory().getBlocks()) {
            if (!block.isInitialized() || !block.isExecute()) continue;
            executableBlocks++;
            InstructionIterator iterator = currentProgram.getListing()
                .getInstructions(block.getStart(), true);
            while (iterator.hasNext()) {
                monitor.checkCancelled();
                Instruction instruction = iterator.next();
                scannedInstructions++;
                if (!instruction.getFlowType().isCall() && !instruction.getFlowType().isJump()) {
                    continue;
                }
                if (instruction.getFlowType().isComputed()) {
                    computedBranchInstructions++;
                    continue;
                }
                Address[] flows = instruction.getFlows();
                if (flows == null) continue;
                for (Address target : flows) {
                    if (!body.contains(target) || body.contains(instruction.getAddress())) continue;
                    Function owner = currentProgram.getFunctionManager()
                        .getFunctionContaining(instruction.getAddress());
                    println("DIRECT_FLOW_INTO_BODY\tfrom=" + instruction.getAddress()
                        + "\ttarget=" + target + "\ttype=" + instruction.getFlowType()
                        + "\towner=" + (owner == null ? "<none>" : owner.getEntryPoint())
                        + "\tinstruction=" + instruction);
                    directBranchTargets++;
                }
            }
        }

        long referenceCount = 0;
        ReferenceManager referenceManager = currentProgram.getReferenceManager();
        InstructionIterator bodyInstructions = currentProgram.getListing()
            .getInstructions(body, true);
        while (bodyInstructions.hasNext()) {
            monitor.checkCancelled();
            Instruction targetInstruction = bodyInstructions.next();
            ReferenceIterator references = referenceManager
                .getReferencesTo(targetInstruction.getAddress());
            while (references.hasNext()) {
                Reference reference = references.next();
                if (body.contains(reference.getFromAddress())) continue;
                Function owner = currentProgram.getFunctionManager()
                    .getFunctionContaining(reference.getFromAddress());
                println("DATABASE_XREF_INTO_BODY\ttarget=" + targetInstruction.getAddress()
                    + "\tfrom=" + reference.getFromAddress() + "\ttype="
                    + reference.getReferenceType() + "\towner="
                    + (owner == null ? "<none>" : owner.getEntryPoint()));
                referenceCount++;
            }
        }

        long absolutePointerCandidates = 0;
        long relativePointerCandidates = 0;
        long readableDataBlocks = 0;
        long readableDataBytes = 0;
        Set<String> relativeContextSlots = new HashSet<>();
        Set<String> queriedWindowTargets = new HashSet<>();
        Set<String> emittedWindowReferences = new HashSet<>();
        for (MemoryBlock block : currentProgram.getMemory().getBlocks()) {
            if (!block.isInitialized() || block.isExecute() || !block.isRead()) continue;
            readableDataBlocks++;
            readableDataBytes += block.getSize();
            long offset = 0;
            while (offset < block.getSize()) {
                monitor.checkCancelled();
                int requested = (int)Math.min(CHUNK_SIZE, block.getSize() - offset);
                byte[] buffer = new byte[requested];
                int read = currentProgram.getMemory().getBytes(block.getStart().add(offset), buffer);
                if (read <= 0) break;
                for (int i = 0; i < read; i++) {
                    Address slot = block.getStart().add(offset + i);
                    if (i <= read - 8 && body.contains(toAddr(littleEndianLong(buffer, i)))) {
                        println("ABSOLUTE_POINTER_CANDIDATE\tblock=" + block.getName()
                            + "\tslot=" + slot + "\tvalue=0x"
                            + Long.toHexString(littleEndianLong(buffer, i)));
                        absolutePointerCandidates++;
                    }
                    if (i <= read - 4) {
                        int displacement = littleEndianInt(buffer, i);
                        long[] resolved = {
                            displacement,
                            slot.getOffset() + (long)displacement,
                            slot.getOffset() + 4L + displacement
                        };
                        String[] bases = {"image-offset", "from-slot", "from-next"};
                        for (int form = 0; form < resolved.length; form++) {
                            if (!contains(body, resolved[form])) continue;
                            println("RELATIVE_POINTER_CANDIDATE\tblock=" + block.getName()
                                + "\tslot=" + slot + "\tform=" + bases[form]
                                + "\traw=0x" + Integer.toHexString(displacement)
                                + "\ttarget=" + toAddr(resolved[form]));
                            relativePointerCandidates++;
                            String slotKey = block.getName() + ":" + slot;
                            if (relativeContextSlots.add(slotKey)) {
                                printRelativeContext(block, slot);
                            }
                            if ((slot.getOffset() & 3) == 0) {
                                printWindowReferences(block, slot, queriedWindowTargets,
                                    emittedWindowReferences);
                            }
                        }
                    }
                }
                if (offset + read >= block.getSize()) break;
                offset += read - 7;
            }
        }

        println("SUMMARY\tsha256=" + actualSha + "\tbase=0x"
            + Long.toHexString(currentProgram.getImageBase().getOffset())
            + "\tdispatcher=" + entry + "\tbody_bytes=" + body.getNumAddresses()
            + "\texecutable_blocks=" + executableBlocks + "\tinstructions="
            + scannedInstructions + "\tdirect_flows_into_body=" + directBranchTargets
            + "\tcomputed_branch_instructions=" + computedBranchInstructions
            + "\tdatabase_xrefs_into_body=" + referenceCount + "\treadable_data_blocks="
            + readableDataBlocks + "\treadable_data_bytes=" + readableDataBytes
            + "\tabsolute_pointer_candidates=" + absolutePointerCandidates
            + "\trelative_pointer_candidates=" + relativePointerCandidates
            + "\tread_only=true");
    }
}
