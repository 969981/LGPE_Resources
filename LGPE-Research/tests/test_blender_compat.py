import unittest

from lgpe_research.blender_compat import MODEL_SOURCE_SHA256, patch_model_importer


NORMAL_SETTER = (
    "if normal_array:\n"
    "        new_object.data.normals_split_custom_set_from_vertices(normal_array)"
)


class BlenderCompatibilityTests(unittest.TestCase):
    def test_unmatched_model_hash_keeps_pinned_importer_unchanged(self):
        source = f"before\n{NORMAL_SETTER}\nafter\n"
        self.assertEqual(patch_model_importer("0" * 64, source), (source, False))

    def test_exact_model_hash_only_skips_the_verified_mesh_normals(self):
        source = f"before\n{NORMAL_SETTER}\nafter\n"
        patched, applied = patch_model_importer(MODEL_SOURCE_SHA256, source)
        self.assertTrue(applied)
        self.assertIn('if normal_array and not (ind == 27 and name == "plant17"):', patched)
        self.assertIn("new_object.data.normals_split_custom_set_from_vertices(normal_array)", patched)
        self.assertEqual(patched.count("LGPE_COMPAT_SKIP_CUSTOM_NORMALS"), 1)
        self.assertEqual(patched.count("before"), 1)
        self.assertEqual(patched.count("after"), 1)

    def test_exact_model_hash_refuses_unknown_importer_layout(self):
        with self.assertRaisesRegex(RuntimeError, "normal setter changed"):
            patch_model_importer(MODEL_SOURCE_SHA256, "different importer source")


if __name__ == "__main__":
    unittest.main()
