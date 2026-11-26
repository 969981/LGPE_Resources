import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.util.HashSet;
import java.util.Set;

public class InspectSpawnRngContext extends GhidraScript {
    private static final String EXPECTED_SHA256 =
        "1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8";
    private static final long EXPECTED_BASE = 0x7100000000L;
    private static final long TARGET_OFFSET = 0x2fdfc0L;
    private static final long CALLER_OFFSET = 0x2f8a50L;
    private static final long HELPER_OFFSET = 0x3154a0L;
    private static final long ENTITY_VALUE_OFFSET = 0x218470L;

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

    private int countReferences(Address target, boolean print) throws Exception {
        int count = 0;
        ReferenceIterator refs = currentProgram.getReferenceManager().getReferencesTo(target);
        while (refs.hasNext()) {
            monitor.checkCancelled();
            Reference ref = refs.next();
            count++;
            Function owner = currentProgram.getFunctionManager()
                .getFunctionContaining(ref.getFromAddress());
            println("REFERENCE\t" + target + "\tfrom=" + ref.getFromAddress()
                + "\ttype=" + ref.getReferenceType() + "\towner="
                + (owner == null ? "<none>" : owner.getEntryPoint()));
        }
        if (print) println("REFERENCE_COUNT\t" + target + "\t" + count);
        return count;
    }

    private void printInstructionWindow(Address target) throws Exception {
        Address first = target.subtract(0x20);
        Address last = target.add(0x20);
        InstructionIterator instructions = currentProgram.getListing().getInstructions(first, true);
        while (instructions.hasNext()) {
            Instruction instruction = instructions.next();
            if (instruction.getAddress().compareTo(last) > 0) break;
            println("INSTRUCTION\t" + instruction.getAddress() + "\t" + instruction);
        }
    }

    private void printExcerpt(String label, String[] lines, int match, int before, int after,
        Set<Integer> printed) {
        int start = Math.max(0, match - before);
        int end = Math.min(lines.length - 1, match + after);
        for (int i = start; i <= end; i++) {
            if (printed.add(i)) println("EXCERPT\t" + label + "\tL" + (i + 1) + "\t" + lines[i]);
        }
    }

    private int printMatches(String label, String code, String needle, int before, int after) {
        String[] lines = code.split("\\R", -1);
        Set<Integer> printed = new HashSet<>();
        int count = 0;
        for (int i = 0; i < lines.length; i++) {
            if (!lines[i].contains(needle)) continue;
            count++;
            if (count <= 3) printExcerpt(label, lines, i, before, after, printed);
        }
        println("MATCH_COUNT\t" + label + "\t" + count);
        return count;
    }

    @Override
    public void run() throws Exception {
        String executable = currentProgram.getExecutablePath();
        if (currentProgram.getImageBase().getOffset() != EXPECTED_BASE) {
            throw new IllegalStateException("unexpected LGPE main image base");
        }
        String actualSha = sha256(Path.of(executable));
        println("PROGRAM\t" + executable + "\tbase=" + currentProgram.getImageBase()
            + "\tsha256=" + actualSha);
        if (!EXPECTED_SHA256.equals(actualSha)
            || !executable.replace('\\', '/').toLowerCase().endsWith("/0/main")) {
            throw new IllegalStateException("not the recorded local Let's Go Pikachu 1.0.2 main");
        }

        Address target = currentProgram.getImageBase().add(TARGET_OFFSET);
        Address callerAddress = currentProgram.getImageBase().add(CALLER_OFFSET);
        Address helperAddress = currentProgram.getImageBase().add(HELPER_OFFSET);
        Function targetExact = currentProgram.getFunctionManager().getFunctionAt(target);
        Function targetFunction = currentProgram.getFunctionManager().getFunctionContaining(target);
        Function caller = currentProgram.getFunctionManager().getFunctionAt(callerAddress);
        Function helper = currentProgram.getFunctionManager().getFunctionAt(helperAddress);
        Function entityValue = currentProgram.getFunctionManager().getFunctionAt(
            currentProgram.getImageBase().add(ENTITY_VALUE_OFFSET));
        println("TARGET\t" + target + "\texact_start=" + (targetExact != null)
            + "\tcontaining_function=" + (targetFunction == null ? "<none>"
                : targetFunction.getEntryPoint()) + "\tname="
            + (targetFunction == null ? "<none>" : targetFunction.getName()));
        if (targetFunction == null || caller == null || helper == null || entityValue == null) {
            throw new IllegalStateException("required exact-build functions are absent");
        }
        printInstructionWindow(target);
        int candidateCalls = countReferences(targetFunction.getEntryPoint(), true);
        int callerIncoming = countReferences(caller.getEntryPoint(), true);
        int helperCalls = countReferences(helper.getEntryPoint(), true);

        DecompInterface decompiler = new DecompInterface();
        decompiler.openProgram(currentProgram);
        DecompileResults result = decompiler.decompileFunction(targetFunction, 120, monitor);
        if (!result.decompileCompleted() || result.getDecompiledFunction() == null) {
            throw new IllegalStateException("decompile failed: " + result.getErrorMessage());
        }
        String code = result.getDecompiledFunction().getC();
        int stateA = printMatches("STATE_A_STEP", code,
            "uVar25 = iVar38 + iVar21 & 0x7f", 12, 7);
        int rateUse = printMatches("RATE_HELPER", code, "FUN_71003154a0(", 9, 7);
        int stateB = printMatches("STATE_B_STEP", code,
            "uVar52 = *(ulong *)(param_1 + 0x90)", 3, 14);
        int specialGate = printMatches("MODE_GATE", code,
            "(int)plVar61[0x7a] != 3", 5, 3);
        int threshold = printMatches("STATE_B_THRESHOLD", code,
            "if (4 < (uint)((int)uVar33 + (int)(uVar33 / 10000) * -10000))", 5, 5);
        int speciesChoice = printMatches("NUMERIC_CHOICES", code,
            "uVar25 = (uint)((uVar53 + uVar52) / 3)", 3, 13);
        DecompileResults entityResult = decompiler.decompileFunction(entityValue, 120, monitor);
        if (!entityResult.decompileCompleted() || entityResult.getDecompiledFunction() == null) {
            throw new IllegalStateException("entity-value helper decompile failed: "
                + entityResult.getErrorMessage());
        }
        String entityCode = entityResult.getDecompiledFunction().getC();
        println("ENTITY_VALUE_HELPER_BEGIN\t" + entityValue.getEntryPoint()
            + "\tchars=" + entityCode.length());
        println(entityCode);
        println("ENTITY_VALUE_HELPER_END\t" + entityValue.getEntryPoint());
        decompiler.dispose();

        if (candidateCalls == 0 || stateA == 0 || rateUse == 0 || stateB == 0
            || specialGate == 0 || threshold == 0 || speciesChoice == 0) {
            throw new IllegalStateException("expected local code patterns were not recovered");
        }
        println("SUMMARY\tsha256=" + actualSha + "\tbase=0x"
            + Long.toHexString(currentProgram.getImageBase().getOffset())
            + "\ttarget_exact_start=" + (targetExact != null)
            + "\tcandidate_calls=" + candidateCalls + "\tcaller_incoming=" + callerIncoming
            + "\thelper_calls=" + helperCalls + "\tstateA=" + stateA + "\tstateB=" + stateB
            + "\trate_use=" + rateUse + "\tmode_gate=" + specialGate
            + "\tstateB_threshold=" + threshold + "\tnumeric_choices=" + speciesChoice
            + "\tentity_value_helper=" + entityValue.getEntryPoint()
            + "\tread_only=true");
    }
}
