#!/usr/bin/env python3
"""
Phase 5.6+ Structural Invariants Test Suite

This test suite enforces the Phase 5.6 guarantees as permanent structural constraints.
These tests must pass for all future development - any failure is a Phase-blocking defect.
"""

import json
import pytest
from pathlib import Path
from .phase_5_6_invariants import verify_phase_5_6_invariants, Phase56Invariants


class TestPhase56Invariants:
    """Test suite for Phase 5.6+ structural invariants."""

    @pytest.fixture
    def test_dir(self):
        """Test directory containing extraction results."""
        return Path("eval/phase_5_6_test")

    @pytest.fixture
    def mini_corpus_config(self):
        """Load mini-corpus configuration."""
        config_path = Path(__file__).parent / "mini_corpus.json"
        with open(config_path) as f:
            return json.load(f)

    def test_all_invariants_pass(self, test_dir):
        """CRITICAL: All Phase 5.6+ invariants must pass."""
        if not test_dir.exists():
            pytest.skip(f"Test directory not found: {test_dir}")

        # This test MUST pass - any failure is a Phase-blocking defect
        success = verify_phase_5_6_invariants(test_dir)
        assert success, "Phase 5.6+ invariant violations detected - this is a Phase-blocking defect"

    def test_mini_corpus_coverage(self, test_dir, mini_corpus_config):
        """Verify mini-corpus rulebooks are present and tested."""
        if not test_dir.exists():
            pytest.skip(f"Test directory not found: {test_dir}")

        expected_rulebooks = {rb["slug"]
                              for rb in mini_corpus_config["rulebooks"]}
        actual_rulebooks = {d.name for d in test_dir.iterdir() if d.is_dir()}

        missing = expected_rulebooks - actual_rulebooks
        assert not missing, f"Mini-corpus rulebooks missing: {missing}"

    def test_manifest_disk_consistency(self, test_dir):
        """INVARIANT: manifest_paths == disk_paths"""
        if not test_dir.exists():
            pytest.skip(f"Test directory not found: {test_dir}")

        verifier = Phase56Invariants(test_dir)

        for rulebook_dir in test_dir.iterdir():
            if rulebook_dir.is_dir():
                manifest_path = rulebook_dir / "manifest.json"
                if manifest_path.exists():
                    with open(manifest_path) as f:
                        manifest = json.load(f)

                    consistency = verifier._verify_path_consistency(
                        rulebook_dir, manifest)
                    assert consistency, f"Path consistency violation in {
                        rulebook_dir.name}"

    def test_persistence_boundary(self, test_dir):
        """INVARIANT: FAILED ⇒ no file, PERSISTED ⇒ file exists with size > 0"""
        if not test_dir.exists():
            pytest.skip(f"Test directory not found: {test_dir}")

        verifier = Phase56Invariants(test_dir)

        for rulebook_dir in test_dir.iterdir():
            if rulebook_dir.is_dir():
                log_path = rulebook_dir / "extraction_log.jsonl"
                if log_path.exists():
                    log_entries = []
                    with open(log_path, 'r', encoding='utf-8') as f:
                        for line in f:
                            if line.strip():
                                log_entries.append(json.loads(line))

                    boundary = verifier._verify_persistence_boundary(
                        log_entries)
                    assert boundary, f"Persistence boundary violation in {
                        rulebook_dir.name}"

    def test_health_metrics_identity(self, test_dir):
        """INVARIANT: attempted = saved + failures"""
        if not test_dir.exists():
            pytest.skip(f"Test directory not found: {test_dir}")

        verifier = Phase56Invariants(test_dir)

        for rulebook_dir in test_dir.iterdir():
            if rulebook_dir.is_dir():
                manifest_path = rulebook_dir / "manifest.json"
                log_path = rulebook_dir / "extraction_log.jsonl"

                if manifest_path.exists() and log_path.exists():
                    with open(manifest_path) as f:
                        manifest = json.load(f)

                    log_entries = []
                    with open(log_path, 'r', encoding='utf-8') as f:
                        for line in f:
                            if line.strip():
                                log_entries.append(json.loads(line))

                    identity = verifier._verify_health_metrics_identity(
                        manifest, log_entries)
                    assert identity, f"Health metrics identity violation in {
                        rulebook_dir.name}"

    def test_extraction_log_integrity(self, test_dir):
        """INVARIANT: Complete log with proper context (no placeholders)"""
        if not test_dir.exists():
            pytest.skip(f"Test directory not found: {test_dir}")

        verifier = Phase56Invariants(test_dir)

        for rulebook_dir in test_dir.iterdir():
            if rulebook_dir.is_dir():
                log_path = rulebook_dir / "extraction_log.jsonl"
                if log_path.exists():
                    log_entries = []
                    with open(log_path, 'r', encoding='utf-8') as f:
                        for line in f:
                            if line.strip():
                                log_entries.append(json.loads(line))

                    integrity = verifier._verify_extraction_log_integrity(
                        log_entries, rulebook_dir.name)
                    assert integrity, f"Extraction log integrity violation in {
                        rulebook_dir.name}"

    def test_seti_p23_img27_assertion(self, test_dir):
        """SPECIAL: SETI p23_img27 must be logged as failed on page_index=23"""
        seti_dir = test_dir / "seti"
        if not seti_dir.exists():
            pytest.skip("SETI test directory not found")

        log_path = seti_dir / "extraction_log.jsonl"
        if not log_path.exists():
            pytest.fail("SETI extraction log not found")

        log_entries = []
        with open(log_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    log_entries.append(json.loads(line))

        p23_entries = [e for e in log_entries if e.get(
            "image_id") == "p23_img27"]
        assert len(p23_entries) == 1, f"Expected exactly 1 p23_img27 entry, found {
            len(p23_entries)}"

        entry = p23_entries[0]
        assert entry.get("page_index") == 23, f"Expected page_index=23, got {
            entry.get('page_index')}"
        assert entry.get("status") == "failed", f"Expected status=failed, got {
            entry.get('status')}"

    def test_no_placeholder_context(self, test_dir):
        """CRITICAL: No placeholder context allowed (image_id=unknown, page_index=-1)"""
        if not test_dir.exists():
            pytest.skip(f"Test directory not found: {test_dir}")

        violations = []

        for rulebook_dir in test_dir.iterdir():
            if rulebook_dir.is_dir():
                log_path = rulebook_dir / "extraction_log.jsonl"
                if log_path.exists():
                    with open(log_path, 'r', encoding='utf-8') as f:
                        for line_num, line in enumerate(f, 1):
                            if line.strip():
                                entry = json.loads(line)
                                image_id = entry.get("image_id", "")
                                page_index = entry.get("page_index", -1)

                                if image_id == "unknown" or page_index < 0:
                                    violations.append(
                                        f"{rulebook_dir.name}:{line_num} - "
                                        f"image_id='{image_id}', page_index={page_index}"
                                    )

        assert not violations, f"Placeholder context violations: {violations}"

    def test_baseline_metrics_maintained(self, test_dir, mini_corpus_config):
        """Verify baseline metrics are maintained for mini-corpus."""
        if not test_dir.exists():
            pytest.skip(f"Test directory not found: {test_dir}")

        for rulebook_config in mini_corpus_config["rulebooks"]:
            slug = rulebook_config["slug"]
            baseline = rulebook_config["baseline"]

            rulebook_dir = test_dir / slug
            if not rulebook_dir.exists():
                continue

            manifest_path = rulebook_dir / "manifest.json"
            if manifest_path.exists():
                with open(manifest_path) as f:
                    manifest = json.load(f)

                health = manifest.get("extraction_health", {})

                # Check critical baseline metrics
                attempted = health.get("images_attempted", 0)
                saved = health.get("images_saved", 0)
                failures = health.get("conversion_failures", 0)

                assert attempted >= baseline["images_attempted"], \
                    f"{slug}: attempted {attempted} < baseline {
                    baseline['images_attempted']}"

                assert saved >= baseline["images_saved"], \
                    f"{slug}: saved {saved} < baseline {
                    baseline['images_saved']}"

                assert failures <= baseline["conversion_failures"], \
                    f"{slug}: failures {failures} > baseline {
                    baseline['conversion_failures']}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
