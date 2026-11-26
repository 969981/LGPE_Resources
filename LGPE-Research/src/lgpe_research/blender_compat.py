"""Hash-gated source compatibility patches for the pinned Blender model importer."""

MODEL_SOURCE_SHA256 = "8077968c4a0a0d59071df2c26bdcdecef53dd537cae814988b3d570bd45d24ff"
_NORMAL_SETTER = (
    "if normal_array:\n"
    "        new_object.data.normals_split_custom_set_from_vertices(normal_array)"
)
_NORMAL_SETTER_COMPAT = (
    'if normal_array and not (ind == 27 and name == "plant17"):\n'
    "        new_object.data.normals_split_custom_set_from_vertices(normal_array)\n"
    "    elif normal_array:\n"
    '        print("LGPE_COMPAT_SKIP_CUSTOM_NORMALS", ind, name, len(normal_array), flush=True)'
)


def patch_model_importer(source_sha256: str, importer_source: str) -> tuple[str, bool]:
    """Skip one crashing custom-normal call for the exact known model only."""
    if source_sha256 != MODEL_SOURCE_SHA256:
        return importer_source, False
    occurrences = importer_source.count(_NORMAL_SETTER)
    if occurrences != 1:
        raise RuntimeError(
            f"pinned importer normal setter changed; expected one occurrence, got {occurrences}"
        )
    return importer_source.replace(_NORMAL_SETTER, _NORMAL_SETTER_COMPAT), True
