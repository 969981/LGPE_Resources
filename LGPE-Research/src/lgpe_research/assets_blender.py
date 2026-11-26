"""Blender worker for the pinned local model importer (license not present in source checkout)."""
import importlib
import hashlib
from pathlib import Path
import sys
import types
import bpy

root, source, output = map(Path,sys.argv[sys.argv.index('--')+1:])
sys.path.insert(0,str(root/'.venv/Lib/site-packages'))
sys.path.insert(0,str(root/'src'))
from lgpe_research.blender_compat import patch_model_importer
package=types.ModuleType('lgpe_importer')
package.__path__=[str(root/'tools/src/Pokemon-Switch-Model-Importer-Blender')]
sys.modules[package.__name__]=package

with source.open('rb') as stream:
    source_hash=hashlib.file_digest(stream,'sha256').hexdigest()
importer_path=root/'tools/src/Pokemon-Switch-Model-Importer-Blender/gfbmdl_import.py'
importer_source=importer_path.read_text(encoding='utf-8')
importer_source, patched=patch_model_importer(source_hash,importer_source)
if patched:
    module=types.ModuleType('lgpe_importer.gfbmdl_import')
    module.__package__='lgpe_importer'
    sys.modules[module.__name__]=module
    exec(compile(importer_source,str(importer_path),'exec'),module.__dict__)
    print('LGPE_COMPAT_PATCH',source_hash,'mesh=27','name=plant17','skip=custom_normals',flush=True)
else:
    module=importlib.import_module('lgpe_importer.gfbmdl_import')
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
module.LoadModel(bytearray(source.read_bytes()),source.stem)
meshes=[x for x in bpy.data.objects if x.type=='MESH']
if not meshes or not all(len(x.data.vertices)>0 for x in meshes):
    raise ValueError('Importer produced no mesh')
if output.exists():raise FileExistsError(output)
result=bpy.ops.export_scene.gltf(filepath=str(output),export_format='GLB')
if result!={'FINISHED'}:raise RuntimeError(result)
print('LGPE_MODEL_COUNTS',[(x.name,len(x.data.vertices),len(x.data.polygons)) for x in meshes])
