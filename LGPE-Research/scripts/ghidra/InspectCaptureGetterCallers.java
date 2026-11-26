import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.framework.Application;
import ghidra.program.model.address.Address;
import ghidra.program.model.address.AddressSet;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;

import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.security.MessageDigest;
import java.util.HexFormat;
import java.util.Locale;

/** Read-only exact-build cross-reference of both capture-getter branches and their other callers. */
public class InspectCaptureGetterCallers extends GhidraScript {
    private static final long BASE = 0x7100000000L;
    private static final String EXPECTED_SHA256 =
        "1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8";
    private static final long[] TARGETS = {
        0x1a64c0L, 0x1aae40L, 0x28e7f0L, 0x28eb60L, 0x28ee10L, 0x305970L, 0x319f80L
    };
    private int decompiled;
    private int instructions;
    private int directCalls;
    private int failures;
    private int temporaryFunctions;

    private String offset(Address address) {
        return String.format("main+0x%x", address.getOffset() - BASE);
    }

    private String sha256(String path) throws Exception {
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        try (InputStream stream = Files.newInputStream(Paths.get(path))) {
            byte[] buffer = new byte[1024 * 1024];
            int count;
            while ((count = stream.read(buffer)) != -1) {
                if (count > 0) digest.update(buffer, 0, count);
            }
        }
        return HexFormat.of().formatHex(digest.digest());
    }

    private void incoming(Address target) {
        ReferenceIterator references = currentProgram.getReferenceManager().getReferencesTo(target);
        int count = 0;
        while (references.hasNext()) {
            Reference reference = references.next();
            Function owner = getFunctionContaining(reference.getFromAddress());
            Instruction instruction = getInstructionAt(reference.getFromAddress());
            println("INCOMING\ttarget=" + offset(target)
                + "\tfrom=" + offset(reference.getFromAddress())
                + "\ttype=" + reference.getReferenceType()
                + "\towner=" + (owner == null ? "NONE" : offset(owner.getEntryPoint()))
                + "\tinstruction=" + (instruction == null ? "NONE" : instruction));
            count++;
        }
        println("INCOMING_SUMMARY\ttarget=" + offset(target) + "\tcount=" + count);
    }

    private void inspect(long targetOffset, DecompInterface decompiler) throws Exception {
        Address entry = toAddr(BASE + targetOffset);
        incoming(entry);
        Function function = getFunctionAt(entry);
        if (function == null) {
            if (getFunctionContaining(entry) != null) {
                println("FUNCTION_NOT_ENTRY\t" + offset(entry)
                    + "\tcontaining=" + offset(getFunctionContaining(entry).getEntryPoint()));
                failures++;
                return;
            }
            if (getInstructionAt(entry) == null) disassemble(entry);
            function = createFunction(entry, null);
            if (function == null || !function.getEntryPoint().equals(entry)) {
                println("FUNCTION_CREATE_FAILED\t" + offset(entry));
                failures++;
                return;
            }
            temporaryFunctions++;
            println("TEMPORARY_FUNCTION_BOUNDARY\t" + offset(entry)
                + "\tread_only_database_changes_discarded=true");
        }
        println("FUNCTION_BEGIN\t" + offset(entry) + "\tbytes=" + function.getBody().getNumAddresses());
        InstructionIterator iterator = currentProgram.getListing().getInstructions(function.getBody(), true);
        int localInstructionCount = 0;
        while (iterator.hasNext()) {
            Instruction instruction = iterator.next();
            localInstructionCount++;
            instructions++;
            println("INS\t" + offset(instruction.getAddress()) + "\t"
                + HexFormat.of().formatHex(instruction.getBytes()) + "\t" + instruction);
            if (!instruction.getFlowType().isCall()) continue;
            Address[] flows = instruction.getFlows();
            if (flows == null || flows.length == 0) {
                println("INDIRECT_CALL\tfrom=" + offset(instruction.getAddress())
                    + "\tinstruction=" + instruction);
                continue;
            }
            for (Address flow : flows) {
                Function callee = getFunctionAt(flow);
                println("CALL\tfrom=" + offset(instruction.getAddress())
                    + "\ttarget=" + offset(flow)
                    + "\tcallee=" + (callee == null ? "NONE" : offset(callee.getEntryPoint()))
                    + "\tinstruction=" + instruction);
                directCalls++;
            }
        }
        DecompileResults result = decompiler.decompileFunction(function, 120, monitor);
        if (!result.decompileCompleted() || result.getDecompiledFunction() == null) {
            println("DECOMPILE_FAILED\t" + offset(entry) + "\t" + result.getErrorMessage());
            failures++;
            return;
        }
        println("DECOMPILED_BEGIN\t" + offset(entry) + "\tinstructions=" + localInstructionCount);
        println(result.getDecompiledFunction().getC());
        println("DECOMPILED_END\t" + offset(entry));
        decompiled++;
    }

    private void inspectUnownedCallsite(long callsiteOffset, int radius) throws Exception {
        Address callsite = toAddr(BASE + callsiteOffset);
        Function owner = getFunctionContaining(callsite);
        Instruction instruction = getInstructionAt(callsite);
        if (instruction == null) throw new IllegalStateException("missing instruction at " + offset(callsite));
        println("UNOWNED_CALLSITE\taddress=" + offset(callsite)
            + "\towner=" + (owner == null ? "NONE" : offset(owner.getEntryPoint()))
            + "\tinstruction=" + instruction);
        Address start = callsite.subtract(radius);
        Address end = callsite.add(radius);
        InstructionIterator iterator = currentProgram.getListing()
            .getInstructions(new AddressSet(start, end), true);
        while (iterator.hasNext()) {
            Instruction current = iterator.next();
            Function currentOwner = getFunctionContaining(current.getAddress());
            println("UNOWNED_WINDOW\taddress=" + offset(current.getAddress())
                + "\towner=" + (currentOwner == null ? "NONE" : offset(currentOwner.getEntryPoint()))
                + "\tbytes=" + HexFormat.of().formatHex(current.getBytes())
                + "\tinstruction=" + current);
        }
    }

    @Override
    public void run() throws Exception {
        if (!"12.2".equals(Application.getApplicationVersion())) {
            throw new IllegalStateException("Ghidra 12.2 required: " + Application.getApplicationVersion());
        }
        String executable = currentProgram.getExecutablePath().trim();
        String normalized = executable.replace('\\', '/').toLowerCase(Locale.ROOT);
        if (currentProgram.getImageBase().getOffset() != BASE
            || !normalized.contains("2b7730a9e56498bbafac2002d4908c6b")
            || !normalized.endsWith("/0/main")) {
            throw new IllegalStateException("not the pinned Pikachu 1.0.2 main");
        }
        String before = sha256(executable);
        if (!EXPECTED_SHA256.equals(before)) throw new IllegalStateException("main SHA-256 mismatch: " + before);
        println("BUILD\tgame=Pokemon-Lets-Go-Pikachu\tversion=1.0.2\tnca_id=2b7730a9e56498bbafac2002d4908c6b"
            + "\timage_base=0x7100000000\tmain_sha256=" + before);
        println("SCOPE\tDirect getter-handler callers and one caller layer; no capture-result semantics inferred.");

        DecompInterface decompiler = new DecompInterface();
        if (!decompiler.openProgram(currentProgram)) throw new IllegalStateException("decompiler could not open main");
        try {
            for (long target : TARGETS) inspect(target, decompiler);
            inspectUnownedCallsite(0x8549fcL, 0x20);
        } finally {
            decompiler.dispose();
        }
        String after = sha256(executable);
        if (!EXPECTED_SHA256.equals(after) || !before.equals(after)) {
            throw new IllegalStateException("main changed during analysis: " + after);
        }
        println("SUMMARY\tmain_sha256=" + after + "\tdecompiled=" + decompiled
            + "\tinstructions=" + instructions + "\tdirectCalls=" + directCalls
            + "\ttemporaryFunctions=" + temporaryFunctions + "\tfailures=" + failures
            + "\treadOnlySource=true\treadOnlyProject=true");
        if (failures != 0) throw new IllegalStateException("one or more expected function boundaries/decompilations failed");
    }
}
