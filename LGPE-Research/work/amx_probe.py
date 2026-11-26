import json
from collections import Counter
from pathlib import Path

ROWS = [json.loads(line) for line in Path("manifests/amx_headers.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
ROMFS = Path("../1.0.2/2b7730a9e56498bbafac2002d4908c6b_NCA/1")
DECODED = Path("decoded/1.0.2/romfs")


def decode_compact(blob: bytes, width: int) -> list[int]:
    mask = (1 << (width * 8)) - 1
    cells = []
    cursor = 0
    while cursor < len(blob):
        first = blob[cursor]
        cursor += 1
        negative = bool(first & 0x40)
        value = first & 0x7f
        groups = 1
        while first & 0x80:
            if cursor >= len(blob):
                raise ValueError("truncated compact cell")
            first = blob[cursor]
            cursor += 1
            value = (value << 7) | (first & 0x7f)
            groups += 1
            if groups > (width * 8 + 6) // 7:
                raise ValueError("compact cell exceeds cell width")
        if negative:
            value |= -1 << (groups * 7)
        cells.append(value & mask)
    return cells


def decode_little(blob: bytes, width: int) -> list[int]:
    mask = (1 << (width * 8)) - 1
    cells = []
    cursor = 0
    while cursor < len(blob):
        start = cursor
        shift = 0
        value = 0
        last = 0
        while True:
            if cursor >= len(blob):
                raise ValueError("truncated compact cell")
            last = blob[cursor]
            cursor += 1
            value |= (last & 0x7f) << shift
            shift += 7
            if not last & 0x80:
                break
            if shift > width * 8 + 7:
                raise ValueError("compact cell exceeds cell width")
        if last & 0x40:
            value |= -1 << shift
        if cursor <= start:
            raise AssertionError
        cells.append(value & mask)
    return cells


def signed(value: int) -> int:
    return value - (1 << 64) if value & (1 << 63) else value


def validate_game_code(cells: list[int], code_count: int, fields: dict) -> tuple[str, int, list[int]]:
    global_data_ops = {1, 2, 5, 6, 0x0f, 0x10, 0x13, 0x14, 0x6d, 0x72}
    stack_ops = {3, 4, 7, 8, 0x11, 0x12, 0x15, 0x16, 0x6e, 0x73}
    branch_ops = {0x31, 0x33, *range(0x35, 0x41), 0x81}
    invalid_ops = {0x32, *range(0x7c, 0x81), 0x88}
    data_size = fields["hea"] - fields["dat"]
    stack_size = fields["stp"] - fields["hea"]
    code_bytes = fields["dat"] - fields["cod"]
    pc = 0
    opcodes = []
    while pc < code_count:
        op = cells[pc] & 0xffffffff
        opcodes.append(op)
        if not 1 <= op <= 0xd4:
            return f"invalid opcode {op:#x} at cell {pc}", pc, opcodes
        if op in invalid_ops:
            return f"unsupported opcode {op:#x} at cell {pc}", pc, opcodes
        next_pc = pc + 1
        if op in global_data_ops:
            if pc + 1 >= code_count:
                return f"truncated global operand at cell {pc}", pc, opcodes
            operand = signed(cells[pc + 1])
            if not 0 <= operand < data_size:
                return f"global operand {operand} out of range at cell {pc}", pc, opcodes
            next_pc = pc + 2
        elif op in stack_ops:
            if pc + 1 >= code_count:
                return f"truncated stack operand at cell {pc}", pc, opcodes
            operand = signed(cells[pc + 1])
            if not -stack_size <= operand <= stack_size:
                return f"stack operand {operand} out of range at cell {pc}", pc, opcodes
            next_pc = pc + 2
        elif op in branch_ops:
            if pc + 1 >= code_count:
                return f"truncated branch operand at cell {pc}", pc, opcodes
            target = pc * 8 + signed(cells[pc + 1])
            if not 0 <= target <= code_bytes:
                return f"branch target {target} out of range at cell {pc}", pc, opcodes
            next_pc = pc + 2
        elif op in {0x9a, 0x9b}:
            if pc + 2 >= code_count:
                return f"truncated paired operands at cell {pc}", pc, opcodes
            lower, upper = (0, data_size) if op == 0x9a else (-stack_size, stack_size)
            for operand_cell in (pc + 1, pc + 2):
                operand = signed(cells[operand_cell])
                if not lower <= operand < upper:
                    return f"paired operand {operand} out of range at cell {pc}", pc, opcodes
            next_pc = pc + 3
        elif op == 0x82:
            if pc + 1 >= code_count:
                return f"truncated switch count at cell {pc}", pc, opcodes
            count = signed(cells[pc + 1])
            if count < 0 or count > code_count:
                return f"invalid switch count {count} at cell {pc}", pc, opcodes
            for index in range(count + 1):
                target_cell = pc + 2 + 2 * index
                if target_cell >= code_count:
                    return f"truncated switch table at cell {pc}", pc, opcodes
                target = target_cell * 8 + signed(cells[target_cell]) - 8
                if not 0 <= target <= code_bytes:
                    return f"switch target {target} out of range at cell {pc}", pc, opcodes
            next_pc = pc + 3 + 2 * count
        elif op == 0xa0:
            if pc + 1 >= code_count:
                return f"truncated branch operand at cell {pc}", pc, opcodes
            target = pc * 8 + signed(cells[pc + 1])
            if not 0 <= target <= code_bytes:
                return f"branch target {target} out of range at cell {pc}", pc, opcodes
            next_pc = pc + 2
        elif op == 0xa1:
            if pc + 1 >= code_count:
                return f"truncated variable operand at cell {pc}", pc, opcodes
            count = signed(cells[pc + 1])
            if count < 0 or count > code_count:
                return f"invalid variable operand count {count} at cell {pc}", pc, opcodes
            return "unsupported callback-dependent opcode 0xa1", pc, opcodes
        elif op == 0x7b:
            next_pc = pc + 2
        elif op == 0x87:
            next_pc = pc + 3
        elif 0x8a <= op <= 0x8d or op in (0x9c, 0x9d):
            next_pc = pc + 3
        elif 0x8e <= op <= 0x91:
            next_pc = pc + 4
        elif 0x92 <= op <= 0x95:
            next_pc = pc + 5
        elif 0x96 <= op <= 0x99:
            next_pc = pc + 6
        elif op == 0x9e:
            next_pc = pc + 2
        elif op == 0xa1:
            raise AssertionError("handled above")
        if next_pc > code_count:
            return f"instruction overruns code at cell {pc}", pc, opcodes
        pc = next_pc
    return "ok", pc, opcodes


results = []
code_results = []
for row in ROWS:
    root = ROMFS if row.get("source_kind") == "romfs_file" else DECODED
    data = (root / row["source"]).read_bytes()
    fields = row["fields"]
    width = {0xf1e1: 8, 0xf1e0: 4, 0xf1e2: 2}[fields["magic"]]
    if not fields["flags"] & 0x04:
        results.append((row["source"], "no_compact_flag", None, None))
        continue
    try:
        cells = decode_compact(data[fields["cod"]:], width)
    except Exception as exc:
        results.append((row["source"], type(exc).__name__ + ": " + str(exc), None, None))
        continue
    expected = (fields["hea"] - fields["cod"]) // width
    code_cells = (fields["dat"] - fields["cod"]) // width
    results.append((row["source"], "ok" if len(cells) == expected else "cell_count_mismatch", len(cells), expected, code_cells, cells[:12]))
    code_status, code_pc, opcodes = validate_game_code(cells, code_cells, fields)
    code_results.append((row["source"], code_status, code_pc, code_cells, opcodes[:12]))
    if len(code_results) <= 10:
        little_cells = decode_little(data[fields["cod"]:], width)
        little_status = validate_game_code(little_cells, code_cells, fields)[0]
        print("candidate", row["source"], len(little_cells), little_status,
              [hex(v) for v in little_cells[:18]])

print("entries", len(ROWS), "results", dict(Counter(row[1] for row in results)))
print("first mismatches", json.dumps([row[:4] for row in results if row[1] != "ok"][:12]))
print("code_validation", dict(Counter("ok" if row[1] == "ok" else row[1].split()[0] for row in code_results)))
print("first_code_failures", json.dumps([row[:4] for row in code_results if row[1] != "ok"][:12]))
print("first_code_passes", json.dumps([row[:4] for row in code_results if row[1] == "ok"][:8]))
print("fail_cell_histogram", Counter(row[2] for row in code_results if row[1] != "ok").most_common(20))
first_failure = next(row for row in ROWS if row["source"] == next(item[0] for item in code_results if item[1] != "ok"))
fail_root = ROMFS if first_failure.get("source_kind") == "romfs_file" else DECODED
fail_data = (fail_root / first_failure["source"]).read_bytes()
fail_fields = first_failure["fields"]
fail_cells = decode_compact(fail_data[fail_fields["cod"]:], 8)
print("first_failure_cells", [(i, hex(value), hex(value & 0xffffffff)) for i, value in enumerate(fail_cells[:24])])
for flag in sorted({row["fields"]["flags"] for row in ROWS}):
    selected = [item for item in code_results if next(r for r in ROWS if r["source"] == item[0])["fields"]["flags"] == flag]
    print("flag_group", hex(flag), len(selected), Counter("ok" if item[1] == "ok" else item[1].split()[0] for item in selected))
for kind in sorted({row.get("source_kind") for row in ROWS}):
    selected_sources = {row["source"] for row in ROWS if row.get("source_kind") == kind}
    selected = [item for item in code_results if item[0] in selected_sources]
    print("kind_group", kind, len(selected), Counter("ok" if item[1] == "ok" else item[1].split()[0] for item in selected))
for row in results[:8]:
    print(json.dumps({"source": row[0], "decoded_cells": row[2], "expected_cells": row[3], "code_cells": row[4], "first_cells": [hex(value) for value in row[5]], "game_code_validation": next(value[1] for value in code_results if value[0] == row[0])}))
for source_row in ROWS:
    if source_row.get("source_kind") == "romfs_file":
        data = (ROMFS / source_row["source"]).read_bytes()
        cells = decode_compact(data[source_row["fields"]["cod"]:], 8)
        print("loose_probe", source_row["source"], source_row["fields"], [hex(x) for x in cells[:20]], next(x[1] for x in code_results if x[0] == source_row["source"]))
