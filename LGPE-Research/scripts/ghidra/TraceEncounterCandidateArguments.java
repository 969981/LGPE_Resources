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
import java.nio.file.Paths;
import java.security.MessageDigest;
import java.util.Locale;

public class TraceEncounterCandidateArguments extends GhidraScript {
    private static final String EXPECTED_MAIN_SHA256 =
        "1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8";
    private static final long EXPECTED_BASE = 0x7100000000L;
    private static final String EXPECTED_NCA_ID = "2b7730a9e56498bbafac2002d4908c6b";
    private static final long CALLER_OFFSET = 0x2f8a50L;
    private static final long PARSER_OFFSET = 0x2fdf90L;
    private static final long CALLSITE_OFFSET = 0x2f8e2cL;
    private static final long APPENDER_OFFSET = 0x307010L;
    private static final long MODE_HELPER_OFFSET = 0x1c4840L;

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

        Address callerEntry = currentProgram.getImageBase().add(CALLER_OFFSET);
        Function caller = currentProgram.getFunctionManager().getFunctionAt(callerEntry);
        if (caller == null) throw new IllegalStateException("caller function not found");
        printFunction("CALLER", caller);

        Address parserEntry = currentProgram.getImageBase().add(PARSER_OFFSET);
        Function parser = currentProgram.getFunctionManager().getFunctionAt(parserEntry);
        if (parser == null) throw new IllegalStateException("parser candidate not found");
        printFunction("PARSER", parser);

        Address appenderEntry = currentProgram.getImageBase().add(APPENDER_OFFSET);
        Function appender = currentProgram.getFunctionManager().getFunctionAt(appenderEntry);
        if (appender == null) throw new IllegalStateException("candidate appender not found");
        printFunction("APPENDER", appender);

        Address modeHelperEntry = currentProgram.getImageBase().add(MODE_HELPER_OFFSET);
        Function modeHelper = currentProgram.getFunctionManager().getFunctionAt(modeHelperEntry);
        if (modeHelper == null) throw new IllegalStateException("mode helper not found");
        printFunction("MODE_HELPER", modeHelper);

        Address callsite = currentProgram.getImageBase().add(CALLSITE_OFFSET);
        Instruction instruction = currentProgram.getListing().getInstructionAt(callsite);
        println("CALLSITE\t" + callsite + "\t" + (instruction == null ? "<no instruction>" : instruction.toString()));
        if (instruction != null) {
            Instruction cursor = instruction;
            for (int i = 0; i < 10 && cursor != null; i++) {
                cursor = currentProgram.getListing().getInstructionBefore(cursor.getAddress());
            }
            for (int i = 0; i < 18 && cursor != null; i++) {
                println("CALLSITE_CONTEXT\t" + cursor.getAddress() + "\t" + cursor);
                if (cursor.getAddress().compareTo(callsite) >= 0) break;
                cursor = currentProgram.getListing().getInstructionAfter(cursor.getAddress());
            }
        }
        println("SUMMARY\tcaller=" + callerEntry + "\tparser=" + parserEntry
            + "\tcallsite=" + callsite + "\timage=" + normalized);
    }

    private void printFunction(String label, Function function) throws Exception {
        println("FUNCTION\t" + label + "\tentry=" + function.getEntryPoint()
            + "\tname=" + function.getName() + "\tbytes=" + function.getBody().getNumAddresses());
        ReferenceIterator incoming = currentProgram.getReferenceManager()
            .getReferencesTo(function.getEntryPoint());
        int incomingCount = 0;
        while (incoming.hasNext()) {
            Reference reference = incoming.next();
            incomingCount++;
            Function from = currentProgram.getFunctionManager()
                .getFunctionContaining(reference.getFromAddress());
            println("INCOMING\t" + label + "\tfrom=" + reference.getFromAddress()
                + "\ttype=" + reference.getReferenceType() + "\tcaller="
                + (from == null ? "<no-function>" : from.getEntryPoint()));
        }
        println("INCOMING_SUMMARY\t" + label + "\tcount=" + incomingCount);

        DecompInterface decompiler = new DecompInterface();
        decompiler.openProgram(currentProgram);
        DecompileResults result = decompiler.decompileFunction(function, 180, monitor);
        if (!result.decompileCompleted() || result.getDecompiledFunction() == null) {
            println("DECOMPILE_FAILED\t" + label + "\t" + result.getErrorMessage());
            decompiler.dispose();
            return;
        }
        String[] lines = result.getDecompiledFunction().getC().split("\\R", -1);
        println("DECOMPILED_BEGIN\t" + label + "\tlines=" + lines.length);
        for (int i = 0; i < lines.length; i++) {
            String line = lines[i].replace("\\", "\\\\").replace("\t", "\\t");
            boolean candidateMatchWindow = label.equals("PARSER")
                && ((i >= 210 && i <= 240) || (i >= 240 && i <= 380)
                    || (i >= 1070 && i <= 1550)
                    || (i >= 2100 && i <= 2140));
            if (label.equals("CALLER") || label.equals("APPENDER")
                || label.equals("MODE_HELPER") || candidateMatchWindow || line.contains("param_2")
                || line.contains("lVar41") || line.contains("iVar19")
                || line.contains("FUN_71002fdf90")) {
                println("CODE\t" + label + "\t" + i + "\t" + line);
            }
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
