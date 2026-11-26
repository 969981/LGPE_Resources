import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;

import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.security.MessageDigest;
import java.util.Locale;

public class InspectSequenceOwnerVtables extends GhidraScript {
    private static final String EXPECTED_MAIN_SHA256 =
        "1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8";
    private static final long EXPECTED_BASE = 0x7100000000L;
    private static final String EXPECTED_NCA_ID = "2b7730a9e56498bbafac2002d4908c6b";
    private static final String[] TARGETS = {"7100a8acd0", "7100a8ce20"};

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

    private Address pointerAddress(long value) {
        return currentProgram.getAddressFactory().getDefaultAddressSpace().getAddress(value);
    }

    private boolean executablePointer(long value) {
        Address address;
        try {
            address = pointerAddress(value);
        } catch (Exception exception) {
            return false;
        }
        return currentProgram.getMemory().getBlock(address) != null
            && currentProgram.getMemory().getBlock(address).isExecute();
    }

    private String functionName(long value) {
        Function function = currentProgram.getFunctionManager().getFunctionContaining(pointerAddress(value));
        return function == null ? "<no-function>" : function.getEntryPoint().toString()
            + "/" + function.getName();
    }

    private String readAscii(long pointer, int maxLength) {
        try {
            Address address = pointerAddress(pointer);
            StringBuilder text = new StringBuilder();
            for (int index = 0; index < maxLength; index++) {
                byte value = currentProgram.getMemory().getByte(address.add(index));
                if (value == 0) break;
                if (value < 0x20 || value > 0x7e) return "<non-ascii>";
                text.append((char) value);
            }
            return text.toString();
        } catch (Exception exception) {
            return "<unreadable>";
        }
    }

    private void inspectTarget(String targetText) throws Exception {
        Address target = currentProgram.getAddressFactory().getAddress(targetText);
        ReferenceIterator references = currentProgram.getReferenceManager().getReferencesTo(target);
        int found = 0;
        while (references.hasNext()) {
            Reference reference = references.next();
            if (!reference.getReferenceType().isData()) continue;
            Address cell = reference.getFromAddress();
            long cellValue = currentProgram.getMemory().getLong(cell);
            if (cellValue != target.getOffset()) continue;
            found++;

            Address addressPoint = cell;
            int precedingCodeSlots = 0;
            for (int slot = 0; slot < 512; slot++) {
                Address previous = addressPoint.subtract(8);
                if (!executablePointer(currentProgram.getMemory().getLong(previous))) break;
                addressPoint = previous;
                precedingCodeSlots++;
            }

            Address rttiCell = addressPoint.subtract(8);
            Address offsetCell = addressPoint.subtract(16);
            long rttiPointer = currentProgram.getMemory().getLong(rttiCell);
            long offsetToTop = currentProgram.getMemory().getLong(offsetCell);
            String typeName = "<unresolved>";
            if (rttiPointer != 0 && !executablePointer(rttiPointer)) {
                long namePointer = currentProgram.getMemory().getLong(pointerAddress(rttiPointer).add(8));
                typeName = readAscii(namePointer, 256);
            }

            println("OWNER_METHOD_REF\ttarget=" + target + "\tcell=" + cell
                + "\taddress_point_candidate=" + addressPoint
                + "\tmethod_slot=" + (cell.subtract(addressPoint) / 8)
                + "\tpreceding_code_slots=" + precedingCodeSlots
                + "\trtti_cell=" + rttiCell
                + "\trtti_pointer=" + pointerAddress(rttiPointer)
                + "\ttypeinfo_name=" + typeName
                + "\toffset_to_top=0x" + Long.toHexString(offsetToTop));

            for (int slot = 0; slot < 12; slot++) {
                Address entry = addressPoint.add(slot * 8L);
                long value = currentProgram.getMemory().getLong(entry);
                println("OWNER_VTABLE_CANDIDATE\tindex=" + slot + "\tcell=" + entry
                    + "\tvalue=" + pointerAddress(value)
                    + "\texecutable=" + executablePointer(value)
                    + "\tfunction=" + functionName(value));
                if (!executablePointer(value)) break;
            }

            ReferenceIterator addressPointReferences = currentProgram.getReferenceManager()
                .getReferencesTo(addressPoint);
            while (addressPointReferences.hasNext()) {
                Reference addressPointReference = addressPointReferences.next();
                Function caller = currentProgram.getFunctionManager()
                    .getFunctionContaining(addressPointReference.getFromAddress());
                Instruction instruction = currentProgram.getListing()
                    .getInstructionAt(addressPointReference.getFromAddress());
                println("OWNER_VPTR_REF\taddress_point=" + addressPoint
                    + "\tfrom=" + addressPointReference.getFromAddress()
                    + "\ttype=" + addressPointReference.getReferenceType()
                    + "\tfunction=" + (caller == null ? "<none>" : caller.getEntryPoint())
                    + "\tinstruction=" + (instruction == null ? "<none>" : instruction));
            }
        }
        println("TARGET_SUMMARY\ttarget=" + target + "\tfunction_entry_data_refs=" + found);
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
        println("PROGRAM\timage_base=0x" + Long.toHexString(currentProgram.getImageBase().getOffset())
            + "\tmain_sha256=" + actualHash + "\tread_only=true");
        for (String target : TARGETS) inspectTarget(target);
        println("SUMMARY\ttargets=" + TARGETS.length + "\tmain_sha256=" + actualHash
            + "\tread_only=true");
    }
}
