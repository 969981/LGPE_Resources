import importlib
import importlib.util
from pathlib import Path
import sys
import types
import bpy

args = sys.argv[sys.argv.index('--') + 1:]
root, source, output, mode = Path(args[0]), Path(args[1]), Path(args[2]), args[3]
sys.path.insert(0, str(root / 'work' / 't08-python-site'))
package = types.ModuleType('lgpe_importer')
package.__path__ = [str(root / 'tools' / 'src' / 'Pokemon-Switch-Model-Importer-Blender')]
sys.modules[package.__name__] = package

source_path = root / 'tools' / 'src' / 'Pokemon-Switch-Model-Importer-Blender' / 'gfbmdl_import.py'
if mode in {'skip-custom-normals', 'skip-mesh27-normals'}:
    text = source_path.read_text(encoding='utf-8')
    old = 'if normal_array:\n        new_object.data.normals_split_custom_set_from_vertices(normal_array)'
    new = ('if normal_array and ' + ('ind != 27' if mode == 'skip-mesh27-normals' else 'False') + ':\n'
           '        new_object.data.normals_split_custom_set_from_vertices(normal_array)\n'
           '    elif normal_array:\n'
           '        print("LGPE_DIAG_SKIP_CUSTOM_NORMALS", ind, len(normal_array), flush=True)')
    if text.count(old) != 1:
        raise RuntimeError(f'expected one normal setter, found {text.count(old)}')
    module = types.ModuleType('lgpe_importer.gfbmdl_import')
    module.__package__ = 'lgpe_importer'
    sys.modules[module.__name__] = module
    exec(compile(text.replace(old, new), str(source_path), 'exec'), module.__dict__)
else:
    spec = importlib.util.spec_from_file_location('lgpe_importer.gfbmdl_import', source_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module.__name__] = module
    spec.loader.exec_module(module)

original = module.CreateMesh

def trace_create_mesh(name, mon, ind, *rest):
    print(f'LGPE_MESH_START\t{ind}\t{name}', flush=True)
    result = original(name, mon, ind, *rest)
    print(f'LGPE_MESH_DONE\t{ind}\t{name}', flush=True)
    return result

module.CreateMesh = trace_create_mesh
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
module.LoadModel(bytearray(source.read_bytes()), source.stem)
meshes = [x for x in bpy.data.objects if x.type == 'MESH']
if not meshes or not all(len(x.data.vertices) > 0 for x in meshes):
    raise ValueError('Importer produced no mesh')
if output.exists():
    raise FileExistsError(output)
output.parent.mkdir(parents=True, exist_ok=True)
result = bpy.ops.export_scene.gltf(filepath=str(output), export_format='GLB')
if result != {'FINISHED'}:
    raise RuntimeError(result)
print('LGPE_MODEL_COUNTS', [(x.name, len(x.data.vertices), len(x.data.polygons)) for x in meshes], flush=True)
