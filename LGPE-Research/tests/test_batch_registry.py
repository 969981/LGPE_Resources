import json
import hashlib
import tempfile
import unittest
from pathlib import Path, PurePosixPath, PureWindowsPath
from unittest.mock import patch

from lgpe_research.batch import (
    _ContainedPathResolver, _map_foreign_posix_path, merge_failures,
    read_source_list, verify_outputs, write_jsonl_selected,
)
from lgpe_research.core import NCA, VERSION, add_receipts, remove_receipts


class BatchRegistryTests(unittest.TestCase):
    def test_contained_path_resolver_reuses_parent_and_rejects_symlink_escape(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            root = project / "decoded"
            folder = root / "archive.contents" / "folder"
            folder.mkdir(parents=True)
            first = folder / "first.json"
            second = folder / "second.json"
            first.write_text("first", encoding="utf-8")
            second.write_text("second", encoding="utf-8")
            original_resolve = Path.resolve
            resolver = _ContainedPathResolver(root)

            with patch.object(
                Path,
                "resolve",
                autospec=True,
                side_effect=lambda path, *args, **kwargs: original_resolve(
                    path, *args, **kwargs,
                ),
            ) as resolve_mock:
                self.assertEqual(resolver.resolve(first), first)
                self.assertEqual(resolver.resolve(second), second)
                self.assertEqual(resolve_mock.call_count, 1)

            outside = project / "outside"
            outside.mkdir()
            escaped_file = outside / "secret.json"
            escaped_file.write_text("secret", encoding="utf-8")
            leaf_link = folder / "linked.json"
            escaped_dir = root / "escape"
            try:
                leaf_link.symlink_to(escaped_file)
                escaped_dir.symlink_to(outside, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("symlink creation is unavailable on this host")

            with self.assertRaisesRegex(ValueError, "symlink"):
                resolver.resolve(leaf_link)
            with self.assertRaisesRegex(ValueError, "outside allowed directory"):
                resolver.resolve(escaped_dir / "secret.json")

    def test_remove_receipts_rewrites_jsonl_and_csv_for_invalidated_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            bad_output = project / "decoded/romfs/bad.json"
            good_output = project / "decoded/romfs/good.json"
            add_receipts(project, [
                {"output_file": str(bad_output), "source_sha256": "a", "output_sha256": "b", "method": "amx"},
                {"output_file": str(good_output), "source_sha256": "c", "output_sha256": "d", "method": "other"},
            ], trusted_outputs=True)

            removed = remove_receipts(project, {bad_output}, method="amx")

            self.assertEqual(removed, 1)
            rows = [
                json.loads(line)
                for line in (project / "manifests/outputs.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual([row["output_file"] for row in rows], [str(good_output)])
            csv_text = (project / "manifests/outputs.csv").read_text(encoding="utf-8-sig")
            self.assertIn("good.json", csv_text)
            self.assertNotIn("bad.json", csv_text)

    def test_source_list_normalizes_paths_and_ignores_comments(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sources.txt"
            path.write_text(
                "\ufeff# selected files\r\n bin\\pokelib\\evolution\\evo_001.bin \r\n\r\nbin/pokelib/waza/waza_data.bin\n",
                encoding="utf-8",
            )
            self.assertEqual(
                read_source_list(path),
                {"bin/pokelib/evolution/evo_001.bin", "bin/pokelib/waza/waza_data.bin"},
            )

    def test_verify_selected_container_outputs_checks_member_and_archive_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            container = project / VERSION / NCA / "1" / "bin/archive/a.gfpak"
            container.parent.mkdir(parents=True)
            container.write_bytes(b"original container")
            member = project / "decoded/1.0.2/romfs/bin/archive/a.gfpak.contents/folder/member"
            member.parent.mkdir(parents=True)
            member.write_bytes(b"raw member")
            output = member.with_suffix(".json")
            output.write_bytes(b"decoded json")
            sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
            manifest = project / "manifests/outputs.jsonl"
            manifest.parent.mkdir(parents=True)
            rows = [
                {
                    "relative_source": "bin/archive/a.gfpak", "partition": "romfs",
                    "output_file": str(output), "output_sha256": sha(output),
                    "source_file": str(member), "source_sha256": sha(member),
                    "internal_path": "folder/member.json", "source_internal_path": "folder/member",
                    "container_index": 4, "container_source_file": str(container),
                    "container_source_sha256": sha(container),
                },
                {"relative_source": "bin/archive/other.gfpak", "partition": "romfs"},
            ]
            manifest.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
            result = verify_outputs(
                project, only_sources={"bin/archive/a.gfpak"}, root=project,
            )
            self.assertEqual((result["registered"], result["verified"], result["bad"]), (1, 1, 0))
            container.write_bytes(b"changed container")
            result = verify_outputs(
                project, only_sources={"bin/archive/a.gfpak"}, root=project,
            )
            self.assertEqual(result["bad"], 1)
            self.assertIn("container source SHA256 mismatch", result["errors"][0]["error"])

    def test_verify_maps_windows_unc_receipts_to_local_mirrored_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "LGPE-Research"
            source_rel = Path("bin/message/English/common/itemname.dat")
            source = Path(tmp) / VERSION / NCA / "1" / source_rel
            output = project / "decoded" / VERSION / "romfs" / source_rel.with_suffix(".json")
            source.parent.mkdir(parents=True)
            output.parent.mkdir(parents=True)
            source.write_bytes(b"paired message dat")
            output.write_bytes(b"decoded message json")
            sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
            manifest = project / "manifests" / "outputs.jsonl"
            manifest.parent.mkdir(parents=True)
            row = {
                "relative_source": source_rel.as_posix(),
                "partition": "romfs",
                "output_file": (
                    r"\\192.168.1.5\j\ROMS\Nintendo Switch\Pokemon\Pokemon Lets Go Pikachu"
                    r"\LGPE-Research\decoded\1.0.2\romfs\bin\message\English\common\itemname.json"
                ),
                "output_sha256": sha(output),
                "source_file": (
                    rf"\\192.168.1.5\j\ROMS\Nintendo Switch\Pokemon\Pokemon Lets Go Pikachu"
                    rf"\1.0.2\{NCA}\1\bin\message\English\common\itemname.dat"
                ),
                "source_sha256": sha(source),
            }
            manifest.write_text(json.dumps(row) + "\n", encoding="utf-8")

            result = verify_outputs(project, only_sources={source_rel.as_posix()})

            self.assertEqual((result["registered"], result["verified"], result["bad"]), (1, 1, 0))

    def test_foreign_wsl_paths_map_only_to_exact_local_drive_mirror(self):
        root = PureWindowsPath(r"X:\LGPE-Research\decoded")
        expected = root / "1.0.2" / "romfs" / "bin" / "asset.json"
        foreign = "/mnt/x/lgpe-research/decoded/1.0.2/romfs/bin/asset.json"

        self.assertEqual(
            _map_foreign_posix_path(foreign, expected, root, "output path"),
            expected,
        )
        with self.assertRaisesRegex(ValueError, "does not match its local mirror"):
            _map_foreign_posix_path(
                foreign.replace("/mnt/x/", "/mnt/xy/"),
                expected, root, "output path",
            )
        with self.assertRaisesRegex(ValueError, "does not match its local mirror"):
            _map_foreign_posix_path(
                foreign.replace("asset.json", "other.json"),
                expected, root, "output path",
            )

        posix_root = PurePosixPath("/mnt/x/ROMS/Pokemon/LGPE-Research/decoded")
        posix_expected = posix_root / "1.0.2" / "romfs" / "bin" / "asset.json"
        posix_case_variant = (
            "/mnt/x/roms/pokemon/lgpe-research/decoded/1.0.2/romfs/bin/asset.json"
        )
        self.assertEqual(
            _map_foreign_posix_path(
                posix_case_variant, posix_expected, posix_root, "output path",
            ),
            posix_expected,
        )

    def test_verify_maps_windows_unc_container_receipt_to_local_container(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "LGPE-Research"
            container_rel = Path("bin/archive/test.gfpak")
            container = Path(tmp) / VERSION / NCA / "1" / container_rel
            member = (
                project / "decoded" / VERSION / "romfs" / "bin/archive"
                / "test.gfpak.contents/folder/member"
            )
            output = member.with_suffix(".json")
            container.parent.mkdir(parents=True)
            member.parent.mkdir(parents=True)
            output.parent.mkdir(parents=True, exist_ok=True)
            container.write_bytes(b"original archive")
            member.write_bytes(b"extracted member")
            output.write_bytes(b"decoded member")
            sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
            manifest = project / "manifests" / "outputs.jsonl"
            manifest.parent.mkdir(parents=True)
            row = {
                "relative_source": container_rel.as_posix(),
                "partition": "romfs",
                "internal_path": "folder/member.json",
                "output_file": (
                    r"\\server\share\LGPE-Research\decoded\1.0.2\romfs\bin\archive"
                    r"\test.gfpak.contents\folder\member.json"
                ),
                "output_sha256": sha(output),
                "source_file": str(member),
                "source_sha256": sha(member),
                "source_internal_path": "folder/member",
                "container_source_file": (
                    rf"\\server\share\Pokemon\1.0.2\{NCA}\1\bin\archive\test.gfpak"
                ),
                "container_source_sha256": sha(container),
            }
            manifest.write_text(json.dumps(row) + "\n", encoding="utf-8")

            result = verify_outputs(project, only_sources={container_rel.as_posix()})

            self.assertEqual((result["registered"], result["verified"], result["bad"]), (1, 1, 0))

    def test_successful_retry_clears_only_matching_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            manifest = project / "manifests" / "failures.jsonl"
            manifest.parent.mkdir()
            rows = [
                {"domain": "archive", "source": "a.gfpak", "status": "FAILED", "error": "old"},
                {"domain": "audio", "source": "b.wem", "status": "FAILED", "error": "other"},
            ]
            manifest.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
            result = merge_failures(
                project,
                [{"domain": "audio", "source": "b.wem", "status": "FAILED", "error": "other"}],
                resolved=[{"domain": "archive", "source": "A.GFPak"}],
            )
            self.assertEqual([(row["domain"], row["source"]) for row in result], [("audio", "b.wem")])

    def test_selective_retry_manifest_preserves_other_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "manifests" / "audio.jsonl"
            path.parent.mkdir()
            old = [
                {"source": "a.wem", "status": "DECODED"},
                {"source": "b.wem", "status": "FAILED"},
            ]
            path.write_text("".join(json.dumps(row) + "\n" for row in old), encoding="utf-8")
            write_jsonl_selected(
                path,
                [{"source": "b.wem", "status": "DECODED"}],
                only_sources={"b.wem"},
            )
            result = {row["source"]: row for row in map(json.loads, path.read_text(encoding="utf-8").splitlines())}
            self.assertEqual(result["a.wem"]["status"], "DECODED")
            self.assertEqual(result["b.wem"]["status"], "DECODED")


    def test_bounded_run_preserves_previous_terminal_results(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "manifests" / "audio.jsonl"
            path.parent.mkdir()
            old = [
                {"source": "a.wem", "status": "DECODED", "output_sha256": "keep"},
                {"source": "b.wem", "status": "FAILED", "error": "preserve until retry"},
            ]
            path.write_text("".join(json.dumps(row) + "\n" for row in old), encoding="utf-8")
            write_jsonl_selected(
                path,
                [
                    {"source": "a.wem", "status": "PENDING"},
                    {"source": "b.wem", "status": "DRY_RUN"},
                    {"source": "c.wem", "status": "PENDING"},
                ],
            )
            result = {
                row["source"]: row
                for row in map(json.loads, path.read_text(encoding="utf-8").splitlines())
            }
            self.assertEqual(result["a.wem"]["status"], "DECODED")
            self.assertEqual(result["a.wem"]["output_sha256"], "keep")
            self.assertEqual(result["b.wem"]["status"], "FAILED")
            self.assertEqual(result["c.wem"]["status"], "PENDING")


if __name__ == "__main__":
    unittest.main()
