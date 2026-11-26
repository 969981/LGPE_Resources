import json
from pathlib import Path
import subprocess
import struct
import tempfile
import unittest
import wave
from unittest.mock import patch
from lgpe_research.assets_decode import decode_bntx_dds, decode_bntx_r16, ptcl_sections, run_command, safe_name, validate_output, write_png_rgba

class AssetValidationTests(unittest.TestCase):
    def test_reject_texture_traversal_and_windows_devices(self):
        for name in ['../escape','a/b','a\\b','C:escape','NUL','COM1.dds','space ','.','']:
            with self.subTest(name=name),self.assertRaises(ValueError):safe_name(name)
        self.assertEqual(safe_name('fxmt_3_white202_a'),'fxmt_3_white202_a')

    def particle(self,next_offset=0xffffffff,binary=32):
        data=bytearray(64)
        data[:4]=b'VFXB';data[12:14]=b'\xff\xfe'
        struct.pack_into('<H',data,22,32);struct.pack_into('<I',data,28,len(data))
        struct.pack_into('<4s7I',data,32,b'ESTA',0,0xffffffff,next_offset,0xffffffff,binary,0,0)
        return data

    def test_particle_traversal(self):
        obj=ptcl_sections(self.particle())
        self.assertEqual([s['signature'] for s in obj['sections']],['ESTA'])
        self.assertIn('UNSUPPORTED',obj['render_status'])

    def test_particle_rejects_bad_size_and_links(self):
        cases=[self.particle(next_offset=0),self.particle(next_offset=64),self.particle(binary=64)]
        cases[-1][36:40]=struct.pack('<I',1)
        broken=self.particle();struct.pack_into('<I',broken,28,100);cases.append(broken)
        cycle=self.particle();struct.pack_into('<I',cycle,40,0);cases.append(cycle)
        for data in cases:
            with self.subTest(data=data.hex()),self.assertRaises(ValueError):ptcl_sections(data)

    def test_glb_requires_actual_mesh(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'empty.glb';chunk=json.dumps({'asset':{'version':'2.0'}}).encode()
            p.write_bytes(struct.pack('<4sII',b'glTF',2,20+len(chunk))+struct.pack('<I4s',len(chunk),b'JSON')+chunk)
            with self.assertRaises(ValueError):validate_output(p)

    def test_wav_rejects_truncated_samples(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'sound.wav'
            with wave.open(str(p),'wb') as w:
                w.setparams((2,2,48000,0,'NONE','NONE'));w.writeframes(b'\0'*40)
            self.assertEqual(validate_output(p)['frames'],10)
            p.write_bytes(p.read_bytes()[:-4])
            with self.assertRaises(ValueError):validate_output(p)

    def test_bntx_r8_and_rg8_channel_mappings(self):
        r8=bytearray(130);r8[:4]=b'DDS ';struct.pack_into('<II',r8,12,1,2)
        struct.pack_into('<I',r8,80,0x00020000);r8[128:]=b'\x12\xfe'
        width,height,rgba,meta=decode_bntx_dds(bytes(r8),'R8_UNORM')
        self.assertEqual((width,height,rgba),(2,1,b'\x12\x12\x12\xff\xfe\xfe\xfe\xff'))
        self.assertIn('opaque',meta['channel_mapping'])

        rg8=bytearray(132);rg8[:4]=b'DDS ';struct.pack_into('<II',rg8,12,1,2)
        struct.pack_into('<I',rg8,80,0x00020001);rg8[128:]=b'\x12\x34\xfe\xdc'
        width,height,rgba,meta=decode_bntx_dds(bytes(rg8),'R8_G8_UNORM')
        self.assertEqual((width,height,rgba),(2,1,b'\x12\x34\x00\xff\xfe\xdc\x00\xff'))

    def test_bntx_r16_unorm_expands_to_grayscale_rgba(self):
        source=struct.pack('<4H',0,1,32768,65535)
        rgba=decode_bntx_r16(source,4,1)
        self.assertEqual(rgba,b'\x00\x00\x00\xff\x00\x00\x00\xff\x80\x80\x80\xff\xff\xff\xff\xff')
        for bad_data,bad_width,bad_height in [(source[:-2],4,1),(source,0,1),(source,3,1)]:
            with self.subTest(length=len(bad_data),width=bad_width,height=bad_height),self.assertRaises(ValueError):
                decode_bntx_r16(bad_data,bad_width,bad_height)

    def test_bntx_bc7_rejects_wrong_payload_size(self):
        dds=bytearray(163);dds[:4]=b'DDS ';struct.pack_into('<II',dds,12,4,4)
        dds[84:88]=b'DX10';struct.pack_into('<I',dds,128,98)
        with self.assertRaisesRegex(ValueError,'payload size mismatch'):
            decode_bntx_dds(bytes(dds),'BC7_UNORM')

    def test_rgba_png_writer_and_crc_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'sample.png';write_png_rgba(p,1,1,b'\x01\x02\x03\xff',srgb=True)
            self.assertEqual(validate_output(p)['color_type'],6)
            data=bytearray(p.read_bytes());data[41]^=1;p.write_bytes(data)
            with self.assertRaisesRegex(ValueError,'CRC'):
                validate_output(p)

    def test_timeout_is_reproducibly_logged(self):
        log=[]
        with patch('lgpe_research.assets_decode.subprocess.run',side_effect=subprocess.TimeoutExpired(['fake-tool'],1,output=b'partial',stderr=b'waiting')):
            with self.assertRaises(subprocess.TimeoutExpired):run_command(['fake-tool'],log,timeout=1)
        self.assertEqual(log[0]['timeout_seconds'],1)
        self.assertTrue(log[0]['timed_out'])
        self.assertEqual((log[0]['stdout'],log[0]['stderr']),('partial','waiting'))

if __name__=='__main__':unittest.main()
