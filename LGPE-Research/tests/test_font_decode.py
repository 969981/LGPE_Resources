from __future__ import annotations

import struct
import unittest

from lgpe_research.fonts_decode import decode_bfotf, inspect_opentype


BFOTF_KEY = 1231165446


def small_opentype() -> bytes:
    header = b"OTTO" + struct.pack(">HHHH", 1, 0, 0, 0)
    directory = struct.pack(">4sIII", b"name", 0, len(header) + 16, 4)
    return header + directory + b"FONT"


def encrypt_bfotf(opentype: bytes, *, key: int = BFOTF_KEY) -> bytes:
    if len(opentype) % 4:
        raise ValueError("test fixture must be word aligned")
    magic = {2785117442: 0x1A879BD9, 1231165446: 0x1E1AF836, 2364726489: 0xC1DE68F3}[key]
    encoded = b"".join(
        (int.from_bytes(opentype[i:i + 4], "big") ^ key).to_bytes(4, "big")
        for i in range(0, len(opentype), 4)
    )
    return magic.to_bytes(4, "little") + (len(opentype) ^ key).to_bytes(4, "big") + encoded


class OpenTypeInspectionTests(unittest.TestCase):
    def test_reads_font_signature_and_bounded_table_directory(self):
        summary = inspect_opentype(small_opentype())
        self.assertEqual(summary["signature"], "OTTO")
        self.assertEqual(summary["table_count"], 1)
        self.assertEqual(summary["table_tags"], ["name"])

    def test_rejects_table_ranges_outside_file(self):
        data = bytearray(small_opentype())
        struct.pack_into(">I", data, 20, len(data) + 1)
        with self.assertRaisesRegex(ValueError, "outside"):
            inspect_opentype(bytes(data))


class BfotfDecodeTests(unittest.TestCase):
    def test_decrypts_wordwise_and_checks_decoded_size(self):
        expected = small_opentype()
        decoded, details = decode_bfotf(encrypt_bfotf(expected))
        self.assertEqual(decoded, expected)
        self.assertEqual(details["key"], BFOTF_KEY)
        self.assertEqual(details["output_bytes"], len(expected))
        self.assertEqual(details["font"]["table_tags"], ["name"])

    def test_rejects_unknown_magic(self):
        with self.assertRaisesRegex(ValueError, "magic"):
            decode_bfotf(b"NOPE" + b"\0" * 28)

    def test_rejects_non_word_aligned_encrypted_payload(self):
        with self.assertRaisesRegex(ValueError, "multiple of four"):
            decode_bfotf(b"\x36\xf8\x1a\x1e" + b"\0" * 9)

    def test_rejects_declared_size_mismatch(self):
        data = bytearray(encrypt_bfotf(small_opentype()))
        struct.pack_into(">I", data, 4, (len(data) ^ 1) ^ BFOTF_KEY)
        with self.assertRaisesRegex(ValueError, "declared output length"):
            decode_bfotf(bytes(data))

    def test_rejects_decoded_non_font_payload(self):
        with self.assertRaisesRegex(ValueError, "OpenType"):
            decode_bfotf(encrypt_bfotf(b"BAD!" + b"\0" * 28))


if __name__ == "__main__":
    unittest.main()
