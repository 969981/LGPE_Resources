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

public class InspectPokeLdnMethodTargets extends GhidraScript {
    private static final String EXPECTED_MAIN_SHA256 =
        "1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8";
    private static final long EXPECTED_BASE = 0x7100000000L;
    private static final String EXPECTED_NCA_ID = "2b7730a9e56498bbafac2002d4908c6b";

    private static final Target[] TARGETS = {
        new Target("nn::pia::clone::CloneProtocol::vfunc2", 0x51c100L),
        new Target("nn::pia::clone::CloneProtocol::vfunc3", 0x51f370L),
        new Target("nn::nex::JobProcessProtocolMessage::vfunc0", 0x50e280L),
        new Target("nn::nex::JobProcessProtocolMessage::vfunc1", 0x50e370L),
        new Target("nn::nex::JobProcessProtocolMessage::vfunc3", 0x50e470L),
        new Target("nn::nex::MethodCallJob::vfunc1", 0x4fa590L),
        new Target("nn::nex::MethodCallJob::vfunc3", 0x4fa5b0L),
        new Target("nn::nex::MatchMakingClient::vfunc0", 0xb40100L),
        new Target("nn::nex::MatchMakingClient::vfunc1", 0xb402a0L),
        new Target("nn::nex::MatchMakingClient::vfunc8", 0xb402f0L),
        new Target("caller of MatchMakingClient::vfunc8", 0xb36610L)
    };

    @Override
    public void run() throws Exception {
        String executable = currentProgram.getExecutablePath();
        String normalized = executable == null ? "" : executable.trim().replace('\\', '/');
        println("PROGRAM\t" + currentProgram.getName() + "\tbase="
            + currentProgram.getImageBase() + "\texecutable=" + normalized);
        if (currentProgram.getImageBase().getOffset() != EXPECTED_BASE
            || !normalized.toLowerCase(Locale.ROOT).contains(EXPECTED_NCA_ID)
            || !normalized.toLowerCase(Locale.ROOT).endsWith("/0/main")) {
            throw new IllegalStateException("not the recorded LGPE 1.0.2 main program");
        }
        String actualHash = sha256(executable.trim());
        println("SOURCE_SHA256\t" + actualHash);
        if (!EXPECTED_MAIN_SHA256.equals(actualHash)) {
            throw new IllegalStateException("source main SHA-256 mismatch: " + actualHash);
        }

        for (Target target : TARGETS) inspect(target);
    }

    private void inspect(Target target) throws Exception {
        Address address = currentProgram.getImageBase().add(target.offset);
        Function function = currentProgram.getFunctionManager().getFunctionAt(address);
        Function containing = function != null ? function
            : currentProgram.getFunctionManager().getFunctionContaining(address);
        Instruction instruction = currentProgram.getListing().getInstructionAt(address);
        println("TARGET\t" + target.label + "\tmain+0x" + Long.toHexString(target.offset)
            + "\taddress=" + address + "\tmemory=" + currentProgram.getMemory().contains(address)
            + "\tfunctionAt=" + (function == null ? "<none>" : function.getEntryPoint())
            + "\tfunctionContaining=" + (containing == null ? "<none>" : containing.getEntryPoint())
            + "\tinstruction=" + (instruction == null ? "<none>" : instruction.toString()));

        ReferenceIterator incoming = currentProgram.getReferenceManager().getReferencesTo(address);
        while (incoming.hasNext()) {
            Reference reference = incoming.next();
            Function caller = currentProgram.getFunctionManager()
                .getFunctionContaining(reference.getFromAddress());
            println("INCOMING\t" + address + "\t" + reference.getFromAddress()
                + "\t" + reference.getReferenceType()
                + "\tcaller=" + (caller == null ? "<no-function>" : caller.getEntryPoint()));
        }

        if (function == null) return;
        InstructionIterator instructions = currentProgram.getListing()
            .getInstructions(function.getBody(), true);
        int emitted = 0;
        while (instructions.hasNext() && emitted < 48) {
            Instruction next = instructions.next();
            if (next.getAddress().compareTo(address) < 0) continue;
            println("INSN\t" + next.getAddress() + "\t" + next);
            emitted++;
        }
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

    private static final class Target {
        final String label;
        final long offset;

        Target(String label, long offset) {
            this.label = label;
            this.offset = offset;
        }
    }
}
