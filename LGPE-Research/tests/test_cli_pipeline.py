import argparse
import csv
import io
import json
import tempfile
import unittest
from contextlib import ExitStack, redirect_stdout
from pathlib import Path
from unittest.mock import Mock, patch

from lgpe_research.cli import cmd_plan, cmd_retry_failed, cmd_run, cmd_verify
from lgpe_research.runlog import RunJournal


class RunPipelineTests(unittest.TestCase):
    def test_retry_failed_dispatches_wave_sources_to_wave_batch(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            rel = "bin/app/palma/wave/retry_adpcm.wav"
            failures = project / "manifests" / "failures.jsonl"
            failures.parent.mkdir(parents=True)
            failures.write_text(json.dumps({
                "domain": "wave", "source": rel, "status": "FAILED",
                "error": "recorded conversion failure",
            }) + "\n", encoding="utf-8")
            tool = project / "vgmstream-cli.exe"
            wave_batch = Mock(return_value={"failed": 0, "decoded": 1})
            output = io.StringIO()
            args = argparse.Namespace(
                root=project, domain="wave", include_unsupported=False,
                execute=True, timeout=30, vgmstream=tool,
                blender=None, ffmpeg=None,
            )

            with (
                patch("lgpe_research.cli.PROJECT", project),
                patch("lgpe_research.cli.run_wave_batch", wave_batch),
                patch("lgpe_research.cli.build_coverage", return_value={}),
                redirect_stdout(output),
            ):
                self.assertEqual(cmd_retry_failed(args), 0)

            wave_batch.assert_called_once_with(
                project, project, 0, True, tool, timeout=30, only_sources={rel},
            )
            result = json.loads(output.getvalue())
            self.assertEqual(result["retried"]["wave"]["decoded"], 1)

    def test_retry_failed_dispatches_bffnt_sources_to_bffnt_batch(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            rel = "bin/font/num_00.bffnt"
            failures = project / "manifests" / "failures.jsonl"
            failures.parent.mkdir(parents=True)
            failures.write_text(json.dumps({
                "domain": "bffnt", "source": rel, "status": "FAILED",
                "error": "recorded BFFNT export failure",
            }) + "\n", encoding="utf-8")
            ffmpeg = project / "ffmpeg.exe"
            batch = Mock(return_value={"failed": 0, "decoded": 1})
            output = io.StringIO()
            args = argparse.Namespace(
                root=project, domain="bffnt", include_unsupported=False,
                execute=True, timeout=30, vgmstream=None,
                blender=None, ffmpeg=ffmpeg,
            )
            with (
                patch("lgpe_research.cli.PROJECT", project),
                patch("lgpe_research.cli.run_bffnt_batch", batch),
                patch("lgpe_research.cli.build_coverage", return_value={}),
                redirect_stdout(output),
            ):
                self.assertEqual(cmd_retry_failed(args), 0)
            batch.assert_called_once_with(
                project, project, 0, True, ffmpeg=ffmpeg, only_sources={rel},
            )
            self.assertEqual(json.loads(output.getvalue())["retried"]["bffnt"]["decoded"], 1)

    def test_plan_uses_coverage_status_and_exact_field_pocket_method(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            manifests = project / "manifests"
            manifests.mkdir()
            (manifests / "files.csv").write_text(
                "partition,relative_path,suffix\n"
                "romfs,bin/pokelib/item/field_pocket.dat,.dat\n"
                "romfs,bin/pokelib/item/battle_pocket.dat,.dat\n"
                "romfs,bin/pokelib/item/item_hash_to_index.dat,.dat\n",
                encoding="utf-8",
            )
            (manifests / "coverage.csv").write_text(
                "partition,relative_path,analysis_status\n"
                "romfs,bin/pokelib/item/field_pocket.dat,DECODED\n"
                "romfs,bin/pokelib/item/battle_pocket.dat,DECODED\n"
                "romfs,bin/pokelib/item/item_hash_to_index.dat,DECODED\n",
                encoding="utf-8",
            )

            with patch("lgpe_research.cli.PROJECT", project):
                self.assertEqual(cmd_plan(argparse.Namespace()), 0)

            with (manifests / "plan.csv").open(encoding="utf-8-sig", newline="") as stream:
                rows = {row["relative_path"]: row for row in csv.DictReader(stream)}
            field_pocket = rows["bin/pokelib/item/field_pocket.dat"]
            battle_pocket = rows["bin/pokelib/item/battle_pocket.dat"]
            item_hash = rows["bin/pokelib/item/item_hash_to_index.dat"]
            self.assertEqual(
                field_pocket["method"],
                "exact 1.0.2 byte-map reader; 1,058/1,058 pkNX PocketField cross-checks -> JSON",
            )
            self.assertEqual(field_pocket["status"], "DECODED")
            self.assertEqual(
                battle_pocket["method"],
                "byte map matches pinned pkNX GameManagerGG Item.PocketBattle for 1,058/1,058 items; main loader/accessor not confirmed -> JSON",
            )
            self.assertEqual(battle_pocket["status"], "DECODED")
            self.assertEqual(
                item_hash["method"],
                "exact LGPE 1.0.2 main reader confirms count + 0x10 rows; raw fields preserved -> JSON",
            )
            self.assertEqual(item_hash["status"], "DECODED")

    def test_targeted_verification_ignores_failures_for_other_sources(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            manifests = project / "manifests"
            manifests.mkdir()
            (manifests / "failures.jsonl").write_text(
                json.dumps({"domain": "model", "source": "bin/field/model/a.gfbmdl", "status": "FAILED"}) + "\n"
                + json.dumps({"domain": "texture", "source": "bin/ui/a.bntx", "status": "FAILED"}) + "\n",
                encoding="utf-8",
            )
            sources = project / "sources.txt"
            sources.write_text("bin/ui/b.bntx\n", encoding="utf-8")
            args = argparse.Namespace(sources_file=sources, root=project)
            output = io.StringIO()
            with (
                patch("lgpe_research.cli.PROJECT", project),
                patch("lgpe_research.cli.verify_outputs", return_value={"bad": 0, "verified": 2}),
                redirect_stdout(output),
            ):
                self.assertEqual(cmd_verify(args), 0)

            result = json.loads(output.getvalue())
            self.assertEqual(result["failed_or_unsupported"], 0)

    def test_targeted_verification_keeps_unsupported_separate_from_bad_receipts(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            manifests = project / "manifests"
            manifests.mkdir(parents=True)
            (manifests / "failures.jsonl").write_text(
                json.dumps({
                    "domain": "bnk-media", "source": "bin/sound/bank/a.bnk",
                    "status": "UNSUPPORTED", "error": "partial media",
                }) + "\n",
                encoding="utf-8",
            )
            sources = project / "sources.txt"
            sources.write_text("bin/sound/bank/a.bnk\n", encoding="utf-8")
            args = argparse.Namespace(sources_file=sources, root=project)
            output = io.StringIO()
            with (
                patch("lgpe_research.cli.PROJECT", project),
                patch("lgpe_research.cli.verify_outputs", return_value={"bad": 0, "verified": 1}),
                redirect_stdout(output),
            ):
                self.assertEqual(cmd_verify(args), 0)

            result = json.loads(output.getvalue())
            self.assertEqual(result["failed_or_unsupported"], 1)
            self.assertEqual(result["failed"], 0)
            self.assertEqual(result["unsupported"], 1)

    def test_full_verification_fails_only_for_failed_sources_not_expected_unsupported(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            manifests = project / "manifests"
            manifests.mkdir()
            (manifests / "outputs.jsonl").write_text("", encoding="utf-8")
            args = argparse.Namespace(sources_file=None, root=project)

            for rows, want_failed, want_unsupported, want_unclassified, want_exit in (
                ([{"status": "UNSUPPORTED"}], 0, 1, 0, 0),
                ([{"status": "FAILED"}], 1, 0, 0, 5),
                ([{"status": "FAILED"}, {"status": "UNSUPPORTED"}], 1, 1, 0, 5),
                ([{"status": "UNRECOGNIZED"}], 0, 0, 1, 5),
            ):
                with self.subTest(statuses=[row["status"] for row in rows]):
                    (manifests / "failures.jsonl").write_text(
                        "".join(json.dumps(row) + "\n" for row in rows),
                        encoding="utf-8",
                    )
                    output = io.StringIO()
                    with (
                        patch("lgpe_research.cli.PROJECT", project),
                        patch("lgpe_research.batch.register_sample_evidence", return_value={}),
                        redirect_stdout(output),
                    ):
                        result = cmd_verify(args)

                    summary = json.loads(output.getvalue())
                    self.assertEqual(result, want_exit)
                    self.assertEqual(summary["bad"], 0)
                    self.assertEqual(summary["failed"], want_failed)
                    self.assertEqual(summary["unsupported"], want_unsupported)
                    self.assertEqual(summary["unclassified_failure_statuses"], want_unclassified)
                    self.assertEqual(summary["failed_or_unsupported"], len(rows))

    def test_verify_persists_its_summary_in_the_run_journal(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            manifests = project / "manifests"
            manifests.mkdir()
            (manifests / "outputs.jsonl").write_text("", encoding="utf-8")
            (manifests / "failures.jsonl").write_text(
                json.dumps({"source": "demo.bseq", "status": "UNSUPPORTED"}) + "\n",
                encoding="utf-8",
            )
            journal = RunJournal(project, "verify", {})
            args = argparse.Namespace(sources_file=None, root=project, _journal=journal)
            output = io.StringIO()

            with (
                patch("lgpe_research.cli.PROJECT", project),
                patch("lgpe_research.batch.register_sample_evidence", return_value={}),
                redirect_stdout(output),
            ):
                exit_code = cmd_verify(args)
            journal.finish(exit_code)

            rows = [
                json.loads(line)
                for line in (manifests / "runs.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            checkpoints = [row for row in rows if row["status"] == "CHECKPOINT"]
            self.assertEqual(exit_code, 0)
            self.assertEqual([row["status"] for row in rows], ["RUNNING", "CHECKPOINT", "COMPLETED"])
            self.assertEqual(len(checkpoints), 1)
            self.assertEqual(checkpoints[0]["detail"]["name"], "verification")
            result = checkpoints[0]["detail"]["result"]
            self.assertEqual(result["registered"], 0)
            self.assertEqual(result["verified"], 0)
            self.assertEqual(result["bad"], 0)
            self.assertEqual(result["failed"], 0)
            self.assertEqual(result["unsupported"], 1)
            self.assertEqual(json.loads(output.getvalue())["unsupported"], 1)

    def test_run_invokes_learnset_decoder_after_archive_phase(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            catalog = project / "manifests" / "archives.jsonl"
            catalog.parent.mkdir(parents=True)
            catalog.write_text(
                json.dumps({
                    "source": "bin/archive/waza_oboe.gfpak",
                    "status": "DECODED", "member_count": 980,
                }) + "\n",
                encoding="utf-8",
            )
            tree_diff = project / "docs" / "catalog" / "scan_snapshot_diff.json"
            tree_diff.parent.mkdir(parents=True)
            tree_diff.write_text(json.dumps({
                "matched_paths": 1, "snapshot_only": [], "scan_only": [],
            }), encoding="utf-8")
            archive = Mock(return_value={"failed": 0})
            learnsets = Mock(return_value={"failed": 0, "decoded_members": 980})
            wave = Mock(return_value={"failed": 0, "decoded": 4, "unknown": 1})
            collisions = Mock(return_value={"failed": 0, "root_table_envelope_decoded": 0})
            sequences = Mock(return_value={"failed": 0, "decoded": 0})
            journal = Mock()
            args = argparse.Namespace(
                root=project, full_sha256=False, limit=20, execute=True, timeout=10,
                blender=None, ffmpeg=None, vgmstream=None, _journal=journal,
            )
            output = io.StringIO()
            wave_patch = patch("lgpe_research.cli.run_wave_batch", wave)
            self.addCleanup(wave_patch.stop)
            wave_patch.start()
            fonts = Mock(return_value={"failed": 0, "decoded": 0})
            amx = Mock(return_value={"failed": 0, "unknown": 7})
            amx_decode = Mock(return_value={"failed": 0, "decoded": 0})
            patchers = [
                patch("lgpe_research.cli.PROJECT", project),
                patch("lgpe_research.cli.snapshot_scan", return_value={"scanned": 1, "anomalies": []}),
                patch("lgpe_research.cli.cmd_tree"),
                patch("lgpe_research.cli.cmd_compare_tree"),
                patch("lgpe_research.cli.cmd_plan"),
                patch("lgpe_research.cli.run_archive_batch", archive),
                patch("lgpe_research.cli.run_learnset_batch", learnsets),
                patch("lgpe_research.cli.run_gamedata_batch", return_value={"failed": 0}),
                patch("lgpe_research.cli.run_bnk_batch", return_value={"failed": 0}),
                patch("lgpe_research.cli.run_asset_batch", return_value={"failed": 0}),
                patch("lgpe_research.cli.run_font_batch", fonts),
                patch("lgpe_research.cli.run_bffnt_batch", return_value={"failed": 0, "decoded": 0}),
                patch("lgpe_research.cli.run_collision_batch", collisions),
                patch("lgpe_research.cli.run_audio_batch", return_value={"failed": 0}),
                patch("lgpe_research.cli.catalog_amx_headers", amx),
                patch("lgpe_research.cli.decode_amx", amx_decode),
                patch("lgpe_research.cli.run_bseq_batch", sequences),
                patch("lgpe_research.cli.build_coverage", return_value={}),
                patch("lgpe_research.cli.register_sample_evidence", return_value={}),
                patch("lgpe_research.cli.verify_outputs", return_value={"bad": 0}),
            ]
            with ExitStack() as stack:
                for patcher in patchers:
                    stack.enter_context(patcher)
                stack.enter_context(redirect_stdout(output))
                self.assertEqual(cmd_run(args), 0)

            archive.assert_called_once_with(project, project, 20, True)
            learnsets.assert_called_once_with(project, project, 20, True)
            fonts.assert_called_once_with(project, project, 20, True)
            collisions.assert_called_once_with(project, project, 20, True)
            amx.assert_called_once_with(project, project, limit=20)
            amx_decode.assert_called_once_with(project, project, 20, True)
            sequences.assert_called_once_with(project, project, 20, True)
            wave.assert_called_once_with(project, project, 20, True, tool=None, timeout=10)
            checkpoints = [call.args[0] for call in journal.checkpoint.call_args_list]
            self.assertIn("learnsets", checkpoints)
            self.assertIn("font", checkpoints)
            self.assertIn("bffnt", checkpoints)
            self.assertIn("wave", checkpoints)
            self.assertIn("collision", checkpoints)
            self.assertIn("amx", checkpoints)
            self.assertIn("amx_decode", checkpoints)
            self.assertIn("sequences", checkpoints)
            result = json.loads(output.getvalue())
            self.assertEqual(result["learnsets"]["decoded_members"], 980)
            self.assertEqual(result["font"]["decoded"], 0)
            self.assertEqual(result["bffnt"]["decoded"], 0)
            self.assertEqual(result["wave"]["decoded"], 4)
            self.assertEqual(result["collision"]["root_table_envelope_decoded"], 0)
            self.assertEqual(result["amx"]["unknown"], 7)
            self.assertEqual(result["amx_decode"]["decoded"], 0)

    def test_full_run_maps_internal_audio_after_bnk_and_sequence_batches(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            tree_diff = project / "docs" / "catalog" / "scan_snapshot_diff.json"
            tree_diff.parent.mkdir(parents=True)
            tree_diff.write_text(json.dumps({
                "matched_paths": 1, "snapshot_only": [], "scan_only": [],
            }), encoding="utf-8")
            order = []

            def stage(name, result):
                def run(*args, **kwargs):
                    order.append(name)
                    return result
                return run

            journal = Mock()
            args = argparse.Namespace(
                root=project, full_sha256=False, limit=0, execute=True, timeout=10,
                blender=None, ffmpeg=None, vgmstream=None, _journal=journal,
            )
            output = io.StringIO()
            patchers = [
                patch("lgpe_research.cli.PROJECT", project),
                patch("lgpe_research.cli.snapshot_scan", return_value={"scanned": 1, "anomalies": []}),
                patch("lgpe_research.cli.cmd_tree"),
                patch("lgpe_research.cli.cmd_compare_tree"),
                patch("lgpe_research.cli.cmd_plan"),
                patch("lgpe_research.cli.run_archive_batch", return_value={"failed": 0}),
                patch("lgpe_research.cli.run_learnset_batch", return_value={"failed": 0}),
                patch("lgpe_research.cli.run_gamedata_batch", return_value={"failed": 0}),
                patch("lgpe_research.cli.run_bnk_batch", return_value={"failed": 0}),
                patch("lgpe_research.cli.run_asset_batch", return_value={"failed": 0}),
                patch("lgpe_research.cli.run_font_batch", side_effect=stage("font", {"failed": 0})),
                patch("lgpe_research.cli.run_bffnt_batch", side_effect=stage("bffnt", {"failed": 0})),
                patch("lgpe_research.cli.run_collision_batch", return_value={"failed": 0}),
                patch("lgpe_research.cli.run_audio_batch", return_value={"failed": 0}),
                patch("lgpe_research.cli.run_wave_batch", side_effect=stage("wave", {"failed": 0})),
                patch("lgpe_research.cli.catalog_amx_headers", return_value={"failed": 0}),
                patch("lgpe_research.cli.decode_amx", return_value={"failed": 0}),
                patch("lgpe_research.cli.run_bseq_batch", side_effect=stage("sequences", {"failed": 0})),
                patch("lgpe_research.cli.run_bnk_media_batch", side_effect=stage("bnk_media", {"failed_members": 0, "banks_failed": 0})),
                patch("lgpe_research.cli.build_wwise_event_media_map", side_effect=stage("audio_event_map", {"banksFailed": 0})),
                patch("lgpe_research.cli.build_sequence_wwise_map", side_effect=stage("sequence_audio_map", {"status": "ANALYZED", "failedSequences": 0, "pendingSequences": 0})),
                patch("lgpe_research.cli.write_demo_audio_report", side_effect=stage("demo_audio_map", {"status": "ANALYZED", "failedSequences": 0, "semanticsStatus": "UNKNOWN"})),
                patch("lgpe_research.cli.register_sample_evidence", return_value={}),
                patch("lgpe_research.cli.verify_outputs", return_value={"bad": 0}),
                patch("lgpe_research.cli.build_coverage", return_value={}),
            ]
            with ExitStack() as stack:
                for patcher in patchers:
                    stack.enter_context(patcher)
                stack.enter_context(redirect_stdout(output))
                self.assertEqual(cmd_run(args), 0)

            self.assertEqual(order, ["font", "bffnt", "wave", "sequences", "bnk_media", "audio_event_map", "sequence_audio_map", "demo_audio_map"])
            checkpoints = [call.args[0] for call in journal.checkpoint.call_args_list]
            self.assertIn("bnk_media", checkpoints)
            self.assertIn("font", checkpoints)
            self.assertIn("bffnt", checkpoints)
            self.assertIn("audio_event_map", checkpoints)
            self.assertIn("sequence_audio_map", checkpoints)
            self.assertIn("demo_audio_map", checkpoints)
            result = json.loads(output.getvalue())
            self.assertEqual(result["bnk_media"]["failed_members"], 0)
            self.assertEqual(result["audio_event_map"]["banksFailed"], 0)
            self.assertEqual(result["sequence_audio_map"]["status"], "ANALYZED")
            self.assertEqual(result["demo_audio_map"]["semanticsStatus"], "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
