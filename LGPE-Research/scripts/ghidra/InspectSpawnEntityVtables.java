import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;
import ghidra.program.model.symbol.Symbol;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;

public class InspectSpawnEntityVtables extends GhidraScript {
    private static final String EXPECTED_SHA256 =
        "1bf36681a230f8f5d69c1484e5d4af9027a2cdaee6ed7bf517420b65ff03f1b8";
    private static final long EXPECTED_BASE = 0x7100000000L;
    private static final long[] GLOBALS = {0x15fe9d8L, 0x15fe9e0L};
    private static final long[] VTABLE_OFFSETS = {0x10L, 0x138L, 0x170L};
    private static final long[] SAMPLE_OFFSETS = {
        0L, 8L, 0x10L, 0x18L, 0x130L, 0x138L, 0x140L,
        0x160L, 0x168L, 0x170L, 0x178L
    };

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

    private String readAscii(long pointer) throws Exception {
        StringBuilder value = new StringBuilder();
        Address address = toAddr(pointer);
        for (int i = 0; i < 256; i++) {
            byte b = currentProgram.getMemory().getByte(address.add(i));
            if (b == 0) break;
            if (b < 0x20 || b > 0x7e) return "<non-ascii-at-" + address + ">";
            value.append((char) b);
        }
        return value.toString();
    }

    private String symbolAt(Address address) {
        Symbol symbol = currentProgram.getSymbolTable().getPrimarySymbol(address);
        return symbol == null ? "<none>" : symbol.getName(true);
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

        for (long globalOffset : GLOBALS) {
            Address global = currentProgram.getImageBase().add(globalOffset);
            long pointer = currentProgram.getMemory().getLong(global);
            println("GLOBAL\t" + global + "\tvalue=0x" + Long.toHexString(pointer)
                + "\tsymbol=" + symbolAt(global));
            for (long delta : SAMPLE_OFFSETS) {
                Address slot = toAddr(pointer + delta);
                if (!currentProgram.getMemory().contains(slot)) continue;
                println("VTABLE_WORD\t" + slot + "\tvalue=0x"
                    + Long.toHexString(currentProgram.getMemory().getLong(slot)));
            }
            for (long vtableOffset : VTABLE_OFFSETS) {
                Address vtable = toAddr(pointer + vtableOffset);
                long offsetToTop = currentProgram.getMemory().getLong(vtable.subtract(0x10));
                long typeInfoPointer = currentProgram.getMemory().getLong(vtable.subtract(8));
                if (typeInfoPointer == 0 || !currentProgram.getMemory()
                    .contains(toAddr(typeInfoPointer + 8))) {
                    println("VTABLE\tglobal=" + global + "\taddress_point=" + vtable
                        + "\toffset_to_top=" + offsetToTop + "\ttypeinfo=0x"
                        + Long.toHexString(typeInfoPointer) + "\ttypename=<unavailable>");
                    continue;
                }
                Address typeInfo = toAddr(typeInfoPointer);
                long typeNamePointer = currentProgram.getMemory().getLong(typeInfo.add(8));
                String typeName = readAscii(typeNamePointer);
                println("VTABLE\tglobal=" + global + "\taddress_point=" + vtable
                    + "\toffset_to_top=" + offsetToTop + "\ttypeinfo=0x"
                    + Long.toHexString(typeInfoPointer) + "\ttypeinfo_symbol="
                    + symbolAt(typeInfo) + "\ttypename=" + typeName);
                ReferenceIterator refs = currentProgram.getReferenceManager()
                    .getReferencesTo(vtable);
                int count = 0;
                while (refs.hasNext()) {
                    monitor.checkCancelled();
                    Reference ref = refs.next();
                    count++;
                    Function owner = currentProgram.getFunctionManager()
                        .getFunctionContaining(ref.getFromAddress());
                    println("VTABLE_REFERENCE\t" + vtable + "\tfrom="
                        + ref.getFromAddress() + "\towner="
                        + (owner == null ? "<none>" : owner.getEntryPoint()));
                }
                println("VTABLE_REFERENCE_COUNT\t" + vtable + "\t" + count);
            }
        }
        println("SUMMARY\tsha256=" + actualSha + "\tbase=0x"
            + Long.toHexString(currentProgram.getImageBase().getOffset())
            + "\tread_only=true");
    }
}
