import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.Data;
import ghidra.program.model.listing.DataIterator;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;

import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.Locale;
import java.util.Map;

public class InspectWwiseSequenceSymbols extends GhidraScript {
    private static final String EXPECTED_MAIN_SHA256 =
        "1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8";
    private static final long EXPECTED_BASE = 0x7100000000L;
    private static final String EXPECTED_NCA_ID = "2b7730a9e56498bbafac2002d4908c6b";
    private static final String[] TOKENS = {
        "BelugaSoundPlaySe", "BelugaSoundPlaySeVersion", "BelugaSoundAddEvent",
        "BelugaSoundLoadBank", "BelugaSoundPlayVoice", "SoundPlaySe",
        "SoundLoadBank", "SoundPostEvent", "Sound3DPostEvent", "PostEvent",
        "AkBankHeader", "AK::SoundEngine", "Wwise", "wwise", "BSEQ", "SESD"
    };

    private String escape(String value) {
        return value.replace("\\", "\\\\").replace("\r", "\\r")
            .replace("\n", "\\n").replace("\t", "\\t");
    }

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

    private String matchingToken(String text) {
        String lower = text.toLowerCase(Locale.ROOT);
        for (String token : TOKENS) {
            if (lower.contains(token.toLowerCase(Locale.ROOT))) return token;
        }
        return null;
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

        int definedStrings = 0;
        int candidateStrings = 0;
        int xrefs = 0;
        int noFunctionXrefs = 0;
        Map<String, Function> candidateFunctions = new LinkedHashMap<>();
        DataIterator iterator = currentProgram.getListing().getDefinedData(true);
        while (iterator.hasNext()) {
            Data data = iterator.next();
            Object value = data.getValue();
            if (!(value instanceof String)) continue;
            definedStrings++;
            String text = (String) value;
            String token = matchingToken(text);
            if (token == null) continue;
            candidateStrings++;
            println("STRING\t" + data.getAddress() + "\ttoken=" + token
                + "\tvalue=" + escape(text));
            ReferenceIterator references = currentProgram.getReferenceManager()
                .getReferencesTo(data.getAddress());
            while (references.hasNext()) {
                Reference reference = references.next();
                Function function = currentProgram.getFunctionManager()
                    .getFunctionContaining(reference.getFromAddress());
                Instruction instruction = currentProgram.getListing()
                    .getInstructionAt(reference.getFromAddress());
                println("XREF\t" + data.getAddress() + "\t" + reference.getFromAddress()
                    + "\t" + reference.getReferenceType()
                    + "\tfunction=" + (function == null ? "<none>" : function.getEntryPoint())
                    + "\tname=" + (function == null ? "<none>" : function.getName())
                    + "\tinstruction=" + (instruction == null ? "<none>" : escape(instruction.toString())));
                xrefs++;
                if (function == null) noFunctionXrefs++;
                else candidateFunctions.put(function.getEntryPoint().toString(), function);
            }
        }

        DecompInterface decompiler = new DecompInterface();
        decompiler.openProgram(currentProgram);
        int decompiled = 0;
        int failures = 0;
        for (Function function : candidateFunctions.values()) {
            println("FUNCTION\t" + function.getEntryPoint() + "\t" + function.getName()
                + "\tbytes=" + function.getBody().getNumAddresses());
            DecompileResults result = decompiler.decompileFunction(function, 120, monitor);
            if (!result.decompileCompleted() || result.getDecompiledFunction() == null) {
                failures++;
                println("DECOMPILE_FAILED\t" + function.getEntryPoint() + "\t"
                    + escape(result.getErrorMessage()));
                continue;
            }
            String code = result.getDecompiledFunction().getC();
            decompiled++;
            println("DECOMPILED_BEGIN\t" + function.getEntryPoint() + "\tchars=" + code.length());
            println(code);
            println("DECOMPILED_END\t" + function.getEntryPoint());
        }
        decompiler.dispose();
        println("SUMMARY\tmain_sha256=" + actualHash
            + "\timage_base=0x" + Long.toHexString(currentProgram.getImageBase().getOffset())
            + "\tdefined_strings=" + definedStrings
            + "\tcandidate_strings=" + candidateStrings
            + "\txrefs=" + xrefs
            + "\tunique_functions=" + candidateFunctions.size()
            + "\tdecompiled=" + decompiled
            + "\tdecompile_failures=" + failures
            + "\txrefs_without_function=" + noFunctionXrefs
            + "\tsemantics=UNKNOWN\tread_only=true");
    }
}
