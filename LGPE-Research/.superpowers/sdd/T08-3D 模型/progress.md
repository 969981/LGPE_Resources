# SDD ledger — plan: tasks/T08-3D 模型.md
Task 1: complete (commits f797dd3..652d6d3, tests: pwsh.exe -NoProfile -File scripts/Test-Project.ps1 → OK (skipped=1))

Final review: fresh reviewer found no Critical issues; both Important findings were fixed in one TDD pass.
Regrade: the reviewer P3 report-detail finding was treated as Important because complete source provenance is an explicit audit requirement; the report now stores 698 source hashes and 807 candidate observations.
Final: fixed repeated Ghidra trace replay — 	est_ghidra_wrappers_clear_append_only_script_logs_before_rerun RED→GREEN; actual two-run handler reproduction changed from report failure to two successful, same-hash report runs; suite 251 total, 250 passed, 1 expected skip.
Final: fixed incomplete ENTRY_XREF validation — 	est_owner_trace_rejects_code_reference_with_address_and_assembly_fields and 	est_owner_trace_rejects_reference_summary_count_mismatch RED→GREEN; actual Ghidra-prefixed trace parsing covered; suite 251 total, 250 passed, 1 expected skip.
Final: fixed cross-reference evidence retention — 	est_cross_reference_reports_literal_value_matches_without_assigning_schema RED→GREEN; actual report contains 698 unique source hashes and all 807 raw candidate records; suite 251 total, 250 passed, 1 expected skip.
Final: scoped JSON newline normalization — 	est_shared_json_writer_keeps_legacy_default_without_final_newline RED→GREEN; only the GFBCol report receives explicit CRLF; suite 251 total, 250 passed, 1 expected skip.
Final review disposition: initial verdict was not ready before the Important fixes; no Critical or deferred Minor findings remain. Commit 1d3d74e contains the fix pass.
