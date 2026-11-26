"""Convert four real LGPE 1.0.2 BNTX samples into disposable validated PNGs."""
from __future__ import annotations

import hashlib
import json
import struct
import sys
import tempfile
from pathlib import Path
import zlib

from lgpe_research import assets_decode


SAMPLES = {
    "bin/battle/waza/model/em000_ball_break01/fxmt_0_mask001_m.bntx": "R16_UNORM",
    "bin/battle/waza/model/check_cube/fxmt_cmn_sdw002_m_lta.bntx": "R8_UNORM",
    "bin/battle/waza/model/ew073_df_sprout01/fxmt_0_object203_a.bntx": "R8_G8_UNORM",
    "bin/chara/data/pd/pd0001_00_cap/mdl/pd0001_00_body_col_01.bntx": "BC7_SRGB",
    "bin/demo/res/ev0800_ghost/pm0105/model/pm0105_00_Body_amb.bntx": "BC7_UNORM",
}


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def png_rgba_pixels(path: Path) -> tuple[int, int, bytes]:
    data = path.read_bytes()
    width, height = struct.unpack_from(">II", data, 16)
    offset = 8
    compressed = bytearray()
    while offset < len(data):
        size = struct.unpack_from(">I", data, offset)[0]
        tag = data[offset + 4:offset + 8]
        if tag == b"IDAT":
            compressed.extend(data[offset + 8:offset + 8 + size])
        offset += size + 12
    raw = zlib.decompress(compressed)
    stride = width * 4
    pixels = bytearray()
    for y in range(height):
        row = raw[y * (stride + 1):(y + 1) * (stride + 1)]
        if row[0] != 0:
            raise ValueError("R16 smoke PNG uses an unexpected PNG row filter")
        pixels.extend(row[1:])
    return width, height, bytes(pixels)


def main() -> int:
    project = Path(__file__).resolve().parents[1]
    romfs = project.parent / "1.0.2" / "2b7730a9e56498bbafac2002d4908c6b_NCA" / "1"
    ffmpeg = Path(r"D:\Tool\ffmpeg-8.0.1-full_build\bin\ffmpeg.exe")
    results = []
    ffmpeg_version_command = []
    assets_decode.run_command([str(ffmpeg), "-version"], ffmpeg_version_command)
    ffmpeg_version = ffmpeg_version_command[0]["stdout"].splitlines()[0]
    sys.path.insert(0, str(project / "tools" / "src" / "BNTX-Extractor"))
    import bntx_extract

    with tempfile.TemporaryDirectory(prefix="bntx-smoke-", dir=project / "work") as tmp:
        scratch = Path(tmp)
        for rel, expected_format in SAMPLES.items():
            source = romfs / Path(rel)
            before = sha256(source)
            output = scratch / (Path(rel).stem + ".png")
            commands = []
            conversion = assets_decode.convert_bntx(source, output, project, ffmpeg, commands)
            validation = assets_decode.validate_output(output)
            after = sha256(source)
            if after != before:
                raise RuntimeError(f"source changed during conversion: {rel}")
            if conversion.get("pixel_format") != expected_format:
                raise RuntimeError(f"format mismatch for {rel}: {conversion}")
            cross_validation = None
            if expected_format == "R16_UNORM":
                texture = bntx_extract.readBNTX(source.read_bytes())[0]
                linear = bntx_extract.swizzle.deswizzle(
                    texture.width, texture.height, 1, 1, 2, texture.tileMode,
                    texture.alignment, texture.sizeRange, texture.data,
                )[:texture.width * texture.height * 2]
                raw_path = scratch / "r16-linear.raw"
                gray_path = scratch / "ffmpeg-gray8.raw"
                raw_path.write_bytes(linear)
                assets_decode.run_command([
                    str(ffmpeg), "-hide_banner", "-f", "rawvideo", "-pixel_format", "gray16le",
                    "-video_size", f"{texture.width}x{texture.height}", "-i", str(raw_path),
                    "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "gray", str(gray_path),
                ], commands, scratch)
                width, height, rgba = png_rgba_pixels(output)
                ffmpeg_gray = gray_path.read_bytes()
                if (width, height) != (texture.width, texture.height) or len(ffmpeg_gray) != width * height:
                    raise RuntimeError("FFmpeg R16 cross-check produced unexpected dimensions")
                max_difference = max(abs(rgba[i * 4] - ffmpeg_gray[i]) for i in range(width * height))
                if any(rgba[i * 4:i * 4 + 4] != bytes((rgba[i * 4],) * 3 + (255,)) for i in range(width * height)):
                    raise RuntimeError("R16 PNG channel expansion is not grayscale with opaque alpha")
                if max_difference > 1:
                    raise RuntimeError(f"R16 grayscale differs from FFmpeg by {max_difference} levels")
                cross_validation = {
                    "decoder": "FFmpeg rawvideo gray16le->gray8",
                    "sample_count": width * height,
                    "max_gray_difference": max_difference,
                    "within_one_8bit_level": True,
                }
            results.append({
                "source": rel,
                "source_sha256": before,
                "source_unchanged": True,
                "expected_format": expected_format,
                "conversion": conversion,
                "output_sha256": sha256(output),
                "output_bytes": output.stat().st_size,
                "validation": validation,
                "cross_validation": cross_validation,
                "commands": commands,
            })
    evidence = {
        "source_version": "Pokemon Let's Go Pikachu 1.0.2",
        "bntx_extractor_commit": "2c08e8e55fcc666ba6568a102f36dabd6c584e25",
        "texture2ddecoder_version": "1.0.6",
        "ffmpeg": {"version": ffmpeg_version, "executable_sha256": sha256(ffmpeg)},
        "ffmpeg_version_command": ffmpeg_version_command,
        "smoke_samples": len(results),
        "results": results,
    }
    log = project / "logs" / "bntx-smoke.json"
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(evidence, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
