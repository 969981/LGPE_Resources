import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Data;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;

public class InspectCaptureApiFunctions extends GhidraScript {
    private static final String TABLE_START = "0x710153c800";
    private static final int TABLE_BYTES = 0x100;
    private static final String[] TARGETS = {
        "0x71001a61e0", "0x71001a64c0", "0x710028fa10",
        "0x710028fd60", "0x710028fed0", "0x710028f910", "0x710028fc10",
        "0x7100292640", "0x7100292570", "0x710013a5e0", "0x710013a6b0",
        "0x71001aae40", "0x7100672cc0", "0x710019c6a0", "0x710014cc90",
        "0x710001c9a0", "0x7100210e20", "0x710024a4a0", "0x7100001b80"
    };

    private String clean(String value) {
        return value.replace("\\", "\\\\").replace("\r", "\\r")
            .replace("\n", "\\n").replace("\t", "\\t");
    }

    @Override
    public void run() throws Exception {
        println("PROGRAM\t" + currentProgram.getName() + "\tbase="
            + currentProgram.getImageBase() + "\t" + currentProgram.getExecutablePath());
        Address table = toAddr(TABLE_START);
        for (int offset = 0; offset < TABLE_BYTES; offset += 0x10) {
            Address functionSlot = table.add(offset);
            long functionPointer = currentProgram.getMemory().getLong(functionSlot);
            long namePointer = currentProgram.getMemory().getLong(functionSlot.add(8));
            Address functionAddress = toAddr(String.format("0x%x", functionPointer));
            Address nameAddress = toAddr(String.format("0x%x", namePointer));
            Data nameData = currentProgram.getListing().getDataAt(nameAddress);
            String name = nameData == null ? "<no-defined-data>" : String.valueOf(nameData.getValue());
            Function function = currentProgram.getFunctionManager().getFunctionAt(functionAddress);
            println("PAIR\t" + functionSlot + "\tfunction=" + functionAddress + "\t"
                + (function == null ? "<no-function>" : function.getName())
                + "\tname=" + clean(name) + "\tname_address=" + nameAddress);
        }

        DecompInterface decompiler = new DecompInterface();
        decompiler.openProgram(currentProgram);
        for (String target : TARGETS) {
            Address address = toAddr(target);
            Function function = currentProgram.getFunctionManager().getFunctionAt(address);
            if (function == null) {
                disassemble(address);
                function = createFunction(address, null);
            }
            if (function == null) {
                println("FUNCTION_NOT_FOUND\t" + target);
                continue;
            }
            println("FUNCTION\t" + address + "\tentry=" + function.getEntryPoint()
                + "\t" + function.getName() + "\tbytes=" + function.getBody().getNumAddresses());
            ReferenceIterator incoming = currentProgram.getReferenceManager()
                .getReferencesTo(function.getEntryPoint());
            while (incoming.hasNext()) {
                Reference ref = incoming.next();
                Function caller = currentProgram.getFunctionManager()
                    .getFunctionContaining(ref.getFromAddress());
                println("INCOMING\t" + ref.getFromAddress() + "\t"
                    + (caller == null ? "<no-function>" : caller.getEntryPoint()) + "\t"
                    + (caller == null ? "<no-function>" : caller.getName()));
            }
            InstructionIterator instructions = currentProgram.getListing()
                .getInstructions(function.getBody(), true);
            while (instructions.hasNext()) {
                Instruction instruction = instructions.next();
                for (Reference ref : instruction.getReferencesFrom()) {
                    if (ref.getReferenceType().isCall()) {
                        Function callee = currentProgram.getFunctionManager()
                            .getFunctionContaining(ref.getToAddress());
                        println("CALL\t" + instruction.getAddress() + "\t"
                            + ref.getToAddress() + "\t"
                            + (callee == null ? "<no-function>" : callee.getEntryPoint())
                            + "\t" + (callee == null ? "<no-function>" : callee.getName()));
                    }
                }
            }
            DecompileResults result = decompiler.decompileFunction(function, 120, monitor);
            if (!result.decompileCompleted() || result.getDecompiledFunction() == null) {
                println("DECOMPILE_FAILED\t" + function.getEntryPoint() + "\t"
                    + result.getErrorMessage());
            } else {
                String code = result.getDecompiledFunction().getC();
                println("DECOMPILED_BEGIN\t" + function.getEntryPoint() + "\tchars="
                    + code.length());
                println(code);
                println("DECOMPILED_END\t" + function.getEntryPoint());
            }
        }
        decompiler.dispose();
        println("SUMMARY\timage=" + currentProgram.getExecutablePath());
    }
}
