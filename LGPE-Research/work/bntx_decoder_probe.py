import os
import sys
import tempfile
from pathlib import Path

project = Path(r"X:\ROMS\Nintendo Switch\Pokemon\Pokemon Lets Go Pikachu\LGPE-Research")
romfs = project.parent / "1.0.2" / "2b7730a9e56498bbafac2002d4908c6b_NCA" / "1"
sys.path.insert(0, str(project / "tools" / "src" / "BNTX-Extractor"))
import bntx_extract
import texture2ddecoder

samples = [
    ("bin/battle/waza/model/check_cube/fxmt_cmn_sdw002_m_lta.bntx", "R8_UNORM"),
    ("bin/battle/waza/model/ew073_df_sprout01/fxmt_0_object203_a.bntx", "R8_G8_UNORM"),
    ("bin/chara/data/pd/pd0001_00_cap/mdl/pd0001_00_body_col_01.bntx", "BC7_SRGB"),
    ("bin/demo/res/ev0800_ghost/pm0105/model/pm0105_00_Body_amb.bntx", "BC7_UNORM"),
]
for relative, expected_format in samples:
    source = romfs / relative
    with tempfile.TemporaryDirectory(prefix="bntx-probe-", dir=project / "work") as temp:
        previous = Path.cwd()
        os.chdir(temp)
        try:
            textures = bntx_extract.readBNTX(source.read_bytes())
            if len(textures) != 1:
                raise ValueError(f"expected one texture, got {len(textures)}")
            texture = textures[0]
            actual_format = bntx_extract.formats.get(texture.format, str(texture.format))
            if actual_format != expected_format:
                raise ValueError(f"expected {expected_format}, got {actual_format}")
            bntx_extract.saveTextures(textures)
            dds = Path(texture.name + ".dds").read_bytes()
            if actual_format.startswith("BC7"):
                header_size = 148
                width_in_blocks = (texture.width + 3) // 4
                height_in_blocks = (texture.height + 3) // 4
                expected_bytes = width_in_blocks * height_in_blocks * 16
                payload = dds[header_size:]
                decoded = texture2ddecoder.decode_bc7(payload, texture.width, texture.height)
                if len(payload) != expected_bytes or len(decoded) != texture.width * texture.height * 4:
                    raise ValueError("BC7 payload or decoded BGRA byte count mismatch")
                print(expected_format, relative, "DDS", len(dds), "payload", len(payload), "BGRA", len(decoded))
            else:
                header_size = 128
                channels = 1 if actual_format == "R8_UNORM" else 2
                payload = dds[header_size:]
                expected_bytes = texture.width * texture.height * channels
                if len(payload) != expected_bytes:
                    raise ValueError(f"raw channel payload length {len(payload)} != {expected_bytes}")
                print(expected_format, relative, "DDS", len(dds), "payload", len(payload), "channels", channels)
        finally:
            os.chdir(previous)
