import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Data;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionIterator;
import ghidra.program.model.listing.FunctionManager;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;

import java.io.InputStream;
import java.util.ArrayList;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.security.MessageDigest;
import java.util.HashSet;
import java.util.Locale;
import java.util.Set;

public class InspectEncounterModeHelper extends GhidraScript {
    private static final String EXPECTED_MAIN_SHA256 =
        "1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8";
    private static final long EXPECTED_BASE = 0x7100000000L;
    private static final String EXPECTED_NCA_ID = "2b7730a9e56498bbafac2002d4908c6b";
    private static final long HELPER_OFFSET = 0x1c4840L;
    private static final long FIELD_STORE_OFFSET = 0x1c4824L;
    private static final int CONTEXT_BEFORE = 8;
    private static final int CONTEXT_AFTER = 2;

    @Override
    public void run() throws Exception {
        String executable = currentProgram.getExecutablePath();
        String normalized = executable == null ? "" : executable.trim().replace('\\', '/');
        if (currentProgram.getImageBase().getOffset() != EXPECTED_BASE
            || !normalized.toLowerCase(Locale.ROOT).contains(EXPECTED_NCA_ID)
            || !normalized.toLowerCase(Locale.ROOT).endsWith("/0/main")) {
            throw new IllegalStateException("not the recorded LGPE 1.0.2 main program");
        }
        String hash = sha256(executable.trim());
        println("PROGRAM\tbase=" + currentProgram.getImageBase() + "\tsha256=" + hash);
        if (!EXPECTED_MAIN_SHA256.equals(hash)) {
            throw new IllegalStateException("source main SHA-256 mismatch: " + hash);
        }

        Address helperAddress = currentProgram.getImageBase().add(HELPER_OFFSET);
        Function helper = currentProgram.getFunctionManager().getFunctionAt(helperAddress);
        if (helper == null) throw new IllegalStateException("mode helper not found");
        println("HELPER\tentry=" + helper.getEntryPoint() + "\tname=" + helper.getName()
            + "\tbytes=" + helper.getBody().getNumAddresses());
        decompile("HELPER", helper);

        Set<Long> decompiledEntries = new HashSet<>();
        ReferenceIterator incoming = currentProgram.getReferenceManager()
            .getReferencesTo(helperAddress);
        int refCount = 0;
        while (incoming.hasNext()) {
            monitor.checkCancelled();
            Reference reference = incoming.next();
            refCount++;
            Address callAddress = reference.getFromAddress();
            Function caller = currentProgram.getFunctionManager().getFunctionContaining(callAddress);
            println("CALL_REFERENCE\tfrom=" + callAddress + "\ttype=" + reference.getReferenceType()
                + "\tcaller=" + (caller == null ? "<no-function>" : caller.getEntryPoint()));
            printInstructionContext(callAddress);
            if (caller != null && caller.getEntryPoint().equals(callAddress)) {
                println("WARNING\treference address is caller entry rather than a call instruction\t" + callAddress);
            }
            if (caller != null && decompiledEntries.add(caller.getEntryPoint().getOffset())) {
                decompile("CALLER_" + caller.getEntryPoint(), caller);
            }
        }
        println("CALL_REFERENCE_COUNT\t" + refCount);

        inspectFieldWriter();
        inspectWriterCallsiteParent();

        int offsetMatches = 0;
        int offsetPrinted = 0;
        InstructionIterator instructions = currentProgram.getListing().getInstructions(true);
        while (instructions.hasNext()) {
            monitor.checkCancelled();
            Instruction instruction = instructions.next();
            String text = instruction.toString().toLowerCase(Locale.ROOT);
            if (text.contains("0x11f8") || text.contains("0x11fa")) {
                offsetMatches++;
                if (offsetPrinted < 200) {
                    println("OFFSET_LITERAL\t" + instruction.getAddress() + "\t" + instruction);
                    offsetPrinted++;
                }
            }
        }
        println("OFFSET_LITERAL_SUMMARY\tmatches=" + offsetMatches + "\tprinted=" + offsetPrinted);
        println("SUMMARY\tprogram=" + normalized + "\thelper=" + helperAddress);
    }

    private void inspectFieldWriter() throws Exception {
        Address storeAddress = currentProgram.getImageBase().add(FIELD_STORE_OFFSET);
        Function writer = currentProgram.getFunctionManager().getFunctionContaining(storeAddress);
        if (writer == null) {
            println("FIELD_WRITER_NOT_FOUND\tstore=" + storeAddress);
            return;
        }
        println("FIELD_WRITER\tstore=" + storeAddress + "\tentry=" + writer.getEntryPoint()
            + "\tname=" + writer.getName() + "\tbytes=" + writer.getBody().getNumAddresses());
        printInstructionContext(storeAddress);
        printInstructionContext(currentProgram.getImageBase().add(FIELD_STORE_OFFSET + 4));
        decompile("FIELD_WRITER", writer);

        ReferenceIterator incoming = currentProgram.getReferenceManager()
            .getReferencesTo(writer.getEntryPoint());
        int count = 0;
        while (incoming.hasNext()) {
            monitor.checkCancelled();
            Reference reference = incoming.next();
            count++;
            Address from = reference.getFromAddress();
            Function caller = currentProgram.getFunctionManager().getFunctionContaining(from);
            println("FIELD_WRITER_REFERENCE\tfrom=" + from + "\ttype=" + reference.getReferenceType()
                + "\tcaller=" + (caller == null ? "<no-function>" : caller.getEntryPoint()));
            printInstructionContext(from);
        }
        println("FIELD_WRITER_REFERENCE_COUNT\t" + count);
    }

    private void inspectWriterCallsiteParent() throws Exception {
        Address callAddress = currentProgram.getImageBase().add(0x1957fcL);
        Address prologueAddress = currentProgram.getImageBase().add(0x1957a0L);
        FunctionManager manager = currentProgram.getFunctionManager();
        Function containing = manager.getFunctionContaining(callAddress);
        Function beforeFunction = null;
        Function afterFunction = null;
        FunctionIterator functions = manager.getFunctions(true);
        while (functions.hasNext()) {
            Function candidate = functions.next();
            if (candidate.getEntryPoint().compareTo(callAddress) < 0) {
                beforeFunction = candidate;
            } else if (candidate.getEntryPoint().compareTo(callAddress) > 0) {
                afterFunction = candidate;
                break;
            }
        }
        println("WRITER_CALLSITE\taddress=" + callAddress
            + "\tcontaining=" + (containing == null ? "<no-function>" : containing.getEntryPoint())
            + "\tfunction_before=" + (beforeFunction == null ? "<none>" : beforeFunction.getEntryPoint())
            + "\tfunction_after=" + (afterFunction == null ? "<none>" : afterFunction.getEntryPoint()));

        ReferenceIterator incoming = currentProgram.getReferenceManager().getReferencesTo(callAddress);
        int incomingCount = 0;
        while (incoming.hasNext()) {
            monitor.checkCancelled();
            Reference reference = incoming.next();
            incomingCount++;
            Function source = manager.getFunctionContaining(reference.getFromAddress());
            println("WRITER_CALLSITE_INCOMING\tfrom=" + reference.getFromAddress()
                + "\ttype=" + reference.getReferenceType()
                + "\tcaller=" + (source == null ? "<no-function>" : source.getEntryPoint()));
        }
        println("WRITER_CALLSITE_INCOMING_COUNT\t" + incomingCount);

        Function prologueFunction = manager.getFunctionAt(prologueAddress);
        println("WRITER_PROLOGUE_CANDIDATE\taddress=" + prologueAddress
            + "\tfunction=" + (prologueFunction == null ? "<unassigned>" : prologueFunction.getEntryPoint()));
        ReferenceIterator prologueReferences = currentProgram.getReferenceManager()
            .getReferencesTo(prologueAddress);
        int prologueReferenceCount = 0;
        while (prologueReferences.hasNext()) {
            monitor.checkCancelled();
            Reference reference = prologueReferences.next();
            prologueReferenceCount++;
            Function source = manager.getFunctionContaining(reference.getFromAddress());
            println("WRITER_PROLOGUE_REFERENCE\tfrom=" + reference.getFromAddress()
                + "\ttype=" + reference.getReferenceType()
                + "\tcaller=" + (source == null ? "<no-function>" : source.getEntryPoint()));
            dumpPointerWords(reference.getFromAddress());
        }
        println("WRITER_PROLOGUE_REFERENCE_COUNT\t" + prologueReferenceCount);

        dumpCodeWindow("REMAINING_ENCOUNT_STEP_COUNT_METHOD",
            currentProgram.getImageBase().add(0x195840L), 64);
        inspectReferencesToHelper(0x1c4890L);
        inspectReferencesToHelper(0x1c48a0L);
        inspectReferencesToHelper(0x1c48b0L);
        inspectReferencesToHelper(0x1c48d0L);
        inspectReferencesToHelper(0x1c95f0L);
        inspectReferencesToHelper(0x17abb0L);
        inspectReferencesToHelper(0x17a750L);
        inspectReferencesToHelper(0x17b940L);
        inspectReferencesToHelper(0x19b220L);
        inspectReferencesToHelper(0x19b3c0L);
        inspectReferencesToHelper(0x2fdf90L);
        inspectReferencesToHelper(0x2f8a50L);
        printInstructionContext(currentProgram.getImageBase().add(0x2fe270L));
        printInstructionContext(currentProgram.getImageBase().add(0x2f8e2cL));
        inspectReferencesToHelper(0x71d1b0L);
        dumpCodeWindow("AUX_ITEM_ID_ACCESSOR", currentProgram.getImageBase().add(0x1c4890L), 16);
        dumpCodeWindow("AUX_STEP_COUNT_ACCESSOR", currentProgram.getImageBase().add(0x1c48a0L), 16);
        dumpCodeWindow("AUX_STEP_COUNT_UPDATE", currentProgram.getImageBase().add(0x1c48b0L), 32);
        dumpCodeWindow("AUX_EXPIRED_STATE_CLEAR", currentProgram.getImageBase().add(0x1c48d0L), 16);

        Instruction cursor = currentProgram.getListing().getInstructionAt(callAddress);
        ArrayList<Instruction> prior = new ArrayList<>();
        for (int i = 0; i < 96 && cursor != null; i++) {
            prior.add(cursor);
            cursor = currentProgram.getListing().getInstructionBefore(cursor.getAddress());
        }
        for (int i = prior.size() - 1; i >= 0; i--) {
            printWindowInstruction(prior.get(i));
        }
        cursor = currentProgram.getListing().getInstructionAfter(callAddress);
        for (int i = 0; i < 24 && cursor != null; i++) {
            printWindowInstruction(cursor);
            cursor = currentProgram.getListing().getInstructionAfter(cursor.getAddress());
        }
    }

    private void dumpCodeWindow(String label, Address start, int instructionLimit) throws Exception {
        println("CODE_WINDOW_BEGIN\t" + label + "\tstart=" + start);
        Instruction cursor = currentProgram.getListing().getInstructionAt(start);
        for (int i = 0; i < instructionLimit && cursor != null; i++) {
            monitor.checkCancelled();
            printWindowInstruction(cursor);
            if (cursor.getFlowType().isTerminal()) break;
            cursor = currentProgram.getListing().getInstructionAfter(cursor.getAddress());
        }
        println("CODE_WINDOW_END\t" + label);
    }

    private void inspectReferencesToHelper(long offset) throws Exception {
        Address target = currentProgram.getImageBase().add(offset);
        Function function = currentProgram.getFunctionManager().getFunctionContaining(target);
        println("RELATED_HELPER\taddress=" + target
            + "\tfunction=" + (function == null ? "<unassigned>" : function.getName())
            + "\tentry=" + (function == null ? "<none>" : function.getEntryPoint()));
        if (function != null && function.getEntryPoint().equals(target)) {
            decompile("RELATED_HELPER_" + target, function);
        }
        Address referenceTarget = function == null ? target : function.getEntryPoint();
        ReferenceIterator references = currentProgram.getReferenceManager().getReferencesTo(referenceTarget);
        int count = 0;
        Set<Long> analyzedCallerEntries = new HashSet<>();
        Set<Long> analyzedParentEntries = new HashSet<>();
        Set<Long> analyzedAncestorEntries = new HashSet<>();
        Set<Long> analyzedHigherEntries = new HashSet<>();
        while (references.hasNext()) {
            monitor.checkCancelled();
            Reference reference = references.next();
            count++;
            Function caller = currentProgram.getFunctionManager()
                .getFunctionContaining(reference.getFromAddress());
            println("RELATED_HELPER_REFERENCE\ttarget=" + target + "\tfrom=" + reference.getFromAddress()
                + "\ttype=" + reference.getReferenceType()
                + "\tcaller=" + (caller == null ? "<no-function>" : caller.getEntryPoint()));
            if (offset == 0x1c48b0L && caller != null
                && analyzedCallerEntries.add(caller.getEntryPoint().getOffset())) {
                decompile("AUX_STEP_UPDATE_CALLER", caller);
                ReferenceIterator callerReferences = currentProgram.getReferenceManager()
                    .getReferencesTo(caller.getEntryPoint());
                int callerReferenceCount = 0;
                while (callerReferences.hasNext()) {
                    monitor.checkCancelled();
                    Reference callerReference = callerReferences.next();
                    callerReferenceCount++;
                    Function parent = currentProgram.getFunctionManager()
                        .getFunctionContaining(callerReference.getFromAddress());
                    println("AUX_STEP_UPDATE_CALLER_REFERENCE\tfrom="
                        + callerReference.getFromAddress()
                        + "\ttype=" + callerReference.getReferenceType()
                        + "\tparent=" + (parent == null ? "<no-function>" : parent.getEntryPoint()));
                    printInstructionContext(callerReference.getFromAddress());
                    if (parent != null && analyzedParentEntries.add(parent.getEntryPoint().getOffset())) {
                        decompile("AUX_STEP_UPDATE_PARENT", parent);
                        ReferenceIterator parentReferences = currentProgram.getReferenceManager()
                            .getReferencesTo(parent.getEntryPoint());
                        int parentReferenceCount = 0;
                        while (parentReferences.hasNext()) {
                            monitor.checkCancelled();
                            Reference parentReference = parentReferences.next();
                            parentReferenceCount++;
                            Function ancestor = currentProgram.getFunctionManager()
                                .getFunctionContaining(parentReference.getFromAddress());
                            println("AUX_STEP_UPDATE_PARENT_REFERENCE\tfrom="
                                + parentReference.getFromAddress()
                                + "\ttype=" + parentReference.getReferenceType()
                                + "\tancestor=" + (ancestor == null ? "<no-function>" : ancestor.getEntryPoint()));
                            printInstructionContext(parentReference.getFromAddress());
                            if (ancestor != null
                                && analyzedAncestorEntries.add(ancestor.getEntryPoint().getOffset())) {
                                decompile("AUX_STEP_UPDATE_ANCESTOR", ancestor);
                                ReferenceIterator ancestorReferences = currentProgram.getReferenceManager()
                                    .getReferencesTo(ancestor.getEntryPoint());
                                int ancestorReferenceCount = 0;
                                while (ancestorReferences.hasNext()) {
                                    monitor.checkCancelled();
                                    Reference ancestorReference = ancestorReferences.next();
                                    ancestorReferenceCount++;
                                    Function higher = currentProgram.getFunctionManager()
                                        .getFunctionContaining(ancestorReference.getFromAddress());
                                    println("AUX_STEP_UPDATE_ANCESTOR_REFERENCE\tfrom="
                                        + ancestorReference.getFromAddress()
                                        + "\ttype=" + ancestorReference.getReferenceType()
                                        + "\thigher=" + (higher == null ? "<no-function>" : higher.getEntryPoint()));
                                    printInstructionContext(ancestorReference.getFromAddress());
                                    if (higher != null
                                        && analyzedHigherEntries.add(higher.getEntryPoint().getOffset())) {
                                        ReferenceIterator higherReferences = currentProgram.getReferenceManager()
                                            .getReferencesTo(higher.getEntryPoint());
                                        int higherReferenceCount = 0;
                                        while (higherReferences.hasNext()) {
                                            monitor.checkCancelled();
                                            Reference higherReference = higherReferences.next();
                                            higherReferenceCount++;
                                            Function callerOfHigher = currentProgram.getFunctionManager()
                                                .getFunctionContaining(higherReference.getFromAddress());
                                            println("AUX_STEP_UPDATE_HIGHER_REFERENCE\tfrom="
                                                + higherReference.getFromAddress()
                                                + "\ttype=" + higherReference.getReferenceType()
                                                + "\tcaller=" + (callerOfHigher == null
                                                    ? "<no-function>" : callerOfHigher.getEntryPoint()));
                                        }
                                        println("AUX_STEP_UPDATE_HIGHER_REFERENCE_COUNT\t" + higherReferenceCount);
                                    }
                                }
                                println("AUX_STEP_UPDATE_ANCESTOR_REFERENCE_COUNT\t" + ancestorReferenceCount);
                            }
                        }
                        println("AUX_STEP_UPDATE_PARENT_REFERENCE_COUNT\t" + parentReferenceCount);
                    }
                }
                println("AUX_STEP_UPDATE_CALLER_REFERENCE_COUNT\t" + callerReferenceCount);
            }
        }
        println("RELATED_HELPER_REFERENCE_COUNT\t" + target + "\t" + count);
    }

    private void dumpPointerWords(Address center) {
        for (int offset = -0x30; offset <= 0x30; offset += 8) {
            Address slot = center.add(offset);
            try {
                long value = currentProgram.getMemory().getLong(slot);
                println("WRITER_PROLOGUE_QWORD\t" + slot + "\t"
                    + String.format(Locale.ROOT, "0x%016x", value));
                if (value >= EXPECTED_BASE) {
                    Data targetData = currentProgram.getListing().getDataAt(toAddr(value));
                    if (targetData != null && targetData.getValue() instanceof String) {
                        println("WRITER_PROLOGUE_STRING\t" + slot + "\t"
                            + String.format(Locale.ROOT, "0x%016x", value) + "\t"
                            + targetData.getValue());
                    }
                }
            } catch (Exception e) {
                println("WRITER_PROLOGUE_QWORD_UNREADABLE\t" + slot + "\t" + e.getClass().getSimpleName());
            }
        }
    }

    private void printWindowInstruction(Instruction instruction) {
        Function owner = currentProgram.getFunctionManager()
            .getFunctionAt(instruction.getAddress());
        println("WRITER_WINDOW\t" + instruction.getAddress()
            + "\tentry=" + (owner == null ? "" : owner.getName()) + "\t" + instruction);
    }

    private void printInstructionContext(Address callAddress) {
        Instruction call = currentProgram.getListing().getInstructionAt(callAddress);
        if (call == null) {
            println("CALL_CONTEXT_MISSING\t" + callAddress);
            return;
        }
        Instruction cursor = call;
        for (int i = 0; i < CONTEXT_BEFORE && cursor != null; i++) {
            cursor = currentProgram.getListing().getInstructionBefore(cursor.getAddress());
        }
        while (cursor != null && cursor.getAddress().compareTo(callAddress) <= 0) {
            println("CALL_CONTEXT\t" + cursor.getAddress() + "\t" + cursor);
            if (cursor.getAddress().equals(callAddress)) break;
            cursor = currentProgram.getListing().getInstructionAfter(cursor.getAddress());
        }
        cursor = currentProgram.getListing().getInstructionAfter(callAddress);
        for (int i = 0; i < CONTEXT_AFTER && cursor != null; i++) {
            println("CALL_CONTEXT\t" + cursor.getAddress() + "\t" + cursor);
            cursor = currentProgram.getListing().getInstructionAfter(cursor.getAddress());
        }
    }

    private void decompile(String label, Function function) throws Exception {
        DecompInterface decompiler = new DecompInterface();
        decompiler.openProgram(currentProgram);
        DecompileResults result = decompiler.decompileFunction(function, 180, monitor);
        if (!result.decompileCompleted() || result.getDecompiledFunction() == null) {
            println("DECOMPILE_FAILED\t" + label + "\t" + result.getErrorMessage());
            decompiler.dispose();
            return;
        }
        String[] lines = result.getDecompiledFunction().getC().split("\\R", -1);
        println("DECOMPILED_BEGIN\t" + label + "\tentry=" + function.getEntryPoint()
            + "\tlines=" + lines.length);
        for (int i = 0; i < lines.length; i++) {
            String line = lines[i].replace("\\", "\\\\").replace("\t", "\\t");
            println("CODE\t" + label + "\t" + i + "\t" + line);
        }
        println("DECOMPILED_END\t" + label);
        decompiler.dispose();
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
