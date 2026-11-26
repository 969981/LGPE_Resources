import unittest
import struct
from scripts.audit_image_resources import linearize, rgba

class ImageResourceTests(unittest.TestCase):
    def test_rgb5a1_gob_and_alpha(self):
        data=bytearray(512)
        struct.pack_into("<HHHH",data,0,0x801f,0x83e0,0xfc00,0)
        row=dict(depth=1,array_count=1,tile_mode=1,mip_count=1,
                 component_selectors=[2,3,4,5],width=4,height=1,
                 format_code=0x0501,block_height_log2=0)
        self.assertEqual(rgba(row,bytes(data)),bytes([255,0,0,255,0,255,0,255,0,0,255,255,0,0,0,0]))
    def test_truncated_gob(self):
        with self.assertRaises(ValueError): linearize(b"",1,1,2,0)
    def test_unsupported_selectors(self):
        with self.assertRaises(NotImplementedError):
            rgba(dict(depth=1,array_count=1,tile_mode=1,mip_count=1,component_selectors=[0,3,4,5]),b"")
