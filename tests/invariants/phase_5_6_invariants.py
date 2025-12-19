#!/usr/bin/env python3
"""
Phase 5.6+ Structural Invariants Verification

CRITICAL: These invariants are architectural constraints, not implementation details.
Any regression against these guarantees is a Phase-blocking defect.

Enforced Invariants:
1. Manifest ≠ Disk consistency
2. Health metrics identity: attempted = saved + failed
3. Persistence boundary: FAILED ⇒ no file, PERSISTED ⇒ size > 0
4. Extraction log integrity with proper context (no placeholders)
5. Zero silent drops enforcement
"""

import json
from pathlib import Path
from typing import Dict, List


class InvariantViolation(Exception):
    """Raised when a structural invariant is violated."""
    pass


class Phase56Invariants:
    """Phase 5.6+ structural invariant verification."""

    def __init__(self, test_dir: Path):
        self.test_dir = test_dir
        self.violations: List[str] = []

    def verify_all_rulebooks(self) -> bool:
        """
        Verify all Phase 5.6+ invariants across all rulebooks in test directory.

        Returns:
            True if all invariants pass, False otherwise

        Raises:
            InvariantViolation: If critical structural invariants are violated
        """
        if not self.test_dir.exists():
            raise InvariantViolation(
                f"Test directory not found: {
                    self.test_dir}")

        all_passed = True
        total_invariants = 0
        passed_invariants = 0

        for rulebook_dir in self.test_dir.iterdir():
            if rulebook_dir.is_dir():
                invariants = self._verify_rulebook_invariants(rulebook_dir)

                rulebook_passed = all(invariants.values())
                rulebook_count = sum(invariants.values())

                total_invariants += len(invariants)
                passed_invariants += rulebook_count

                if not rulebook_passed:
                    all_passed = False
                    failed_invariants = [
                        k for k, v in invariants.items() if not v]
                    self.violations.append(
                        f"{rulebook_dir.name}: {failed_invariants}")

        if not all_passed:
            violation_summary = "; ".join(self.violations)
            raise InvariantViolation(
                f"CRITICAL: Phase 5.6+ invariant violations detected: {violation_summary}"
            )

        return True

    def _verify_rulebook_invariants(
            self, rulebook_path: Path) -> Dict[str, bool]:
        """Verify all Phase 5.6+ invariants for a single rulebook."""
        invariants = {
            "manifest_exists": False,
            "extraction_log_exists": False,
            "path_set_consistency": False,
            "persistence_boundary": False,
            "health_metrics_identity": False,
            "extraction_log_integrity": False
        }

        # Load manifest
        manifest_path = rulebook_path / "manifest.json"
        if not manifest_path.exists():
            return invariants

        invariants["manifest_exists"] = True

        with open(manifest_path) as f:
            manifest = json.load(f)

        # Load extraction log
        log_path = rulebook_path / "extraction_log.jsonl"
        if not log_path.exists():
            return invariants

        invariants["extraction_log_exists"] = True

        # Parse extraction log
        log_entries = []
        with open(log_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    log_entries.append(json.loads(line))

        # INVARIANT 1: Path set consistency (manifest_paths == disk_paths)
        invariants["path_set_consistency"] = self._verify_path_consistency(
            rulebook_path, manifest
        )

        # INVARIANT 2: Persistence boundary (FAILED ⇒ no file, PERSISTED ⇒ file
        # exists + size > 0)
        invariants["persistence_boundary"] = self._verify_persistence_boundary(
            log_entries)

        # INVARIANT 3: Health metrics identity (attempted = saved + failures)
        invariants["health_metrics_identity"] = self._verify_health_metrics_identity(
            manifest, log_entries
        )

        # INVARIANT 4: Extraction log integrity (no placeholders, proper
        # context)
        invariants["extraction_log_integrity"] = self._verify_extraction_log_integrity(
            log_entries, rulebook_path.name
        )

        return invariants

    def _verify_path_consistency(
            self, rulebook_path: Path, manifest: Dict) -> bool:
        """INVARIANT: manifest_paths == disk_paths"""
        images_dir = rulebook_path / "images" / "all"
        if not images_dir.exists():
            return False

        manifest_files = {item["file_name"] for item in manifest["items"]}
        disk_files = {f.name for f in images_dir.glob("*.png")}

        return manifest_files == disk_files

    def _verify_persistence_boundary(self, log_entries: List[Dict]) -> bool:
        """INVARIANT: FAILED ⇒ no file exists, PERSISTED ⇒ file exists with size > 0"""
        for entry in log_entries:
            status = entry["status"]
            output_path = entry.get("output_path")

            if status == "failed":
                # FAILED status must have no file on disk
                if output_path and Path(output_path).exists():
                    return False
            elif status == "persisted":
                # PERSISTED status must have file with content
                if not output_path:
                    return False
                file_path = Path(output_path)
                if not file_path.exists() or file_path.stat().st_size == 0:
                    return False

        return True

    def _verify_health_metrics_identity(
            self, manifest: Dict, log_entries: List[Dict]) -> bool:
        """INVARIANT: attempted = saved + failures"""
        health = manifest.get("extraction_health", {})
        if not health:
            return False

        # Health metrics identity
        attempted = health.get("images_attempted", 0)
        saved = health.get("images_saved", 0)
        failures = health.get("conversion_failures", 0)

        # Log confirmation
        log_attempted = len(log_entries)
        log_saved = sum(1 for e in log_entries if e["status"] == "persisted")
        log_failed = sum(1 for e in log_entries if e["status"] == "failed")

        # Manifest entries confirmation
        manifest_entries = len(manifest["items"])

        return (attempted == saved + failures and
                attempted == log_attempted and
                saved == log_saved and
                failures == log_failed and
                saved == manifest_entries)

    def _verify_extraction_log_integrity(
            self, log_entries: List[Dict], rulebook_name: str) -> bool:
        """INVARIANT: Complete log with proper context (no placeholders)"""
        if not log_entries:
            return False

        required_fields = [
            "rulebook_id",
            "image_id",
            "status",
            "reason_code",
            "colorspace_str"]

        for entry in log_entries:
            # Check required fields exist
            if not all(field in entry for field in required_fields):
                return False

            # CRITICAL: No placeholder context allowed
            image_id = entry.get("image_id", "")
            page_index = entry.get("page_index", -1)

            if image_id == "unknown" or page_index < 0:
                return False

        # Special assertion for SETI p23_img27 (Phase 5.6 requirement)
        if rulebook_name == "seti":
            p23_entries = [
                e for e in log_entries if e.get("image_id") == "p23_img27"]
            if len(p23_entries) != 1:
                return False

            entry = p23_entries[0]
            if entry.get("page_index") != 23 or entry.get(
                    "status") != "failed":
                return False

        return True


def verify_phase_5_6_invariants(test_dir: Path) -> bool:
    """
    Verify Phase 5.6+ structural invariants.

    Args:
        test_dir: Directory containing test results

    Returns:
        True if all invariants pass

    Raises:
        InvariantViolation: If critical invariants are violated
    """
    verifier = Phase56Invariants(test_dir)
    return verifier.verify_all_rulebooks()


def main():
    """CLI entry point for invariant verification."""
    import sys

    test_dir = Path("eval/phase_5_6_test")
    if len(sys.argv) > 1:
        test_dir = Path(sys.argv[1])

    try:
        success = verify_phase_5_6_invariants(test_dir)
        if success:
            print("ALL PHASE 5.6+ INVARIANTS VERIFIED")
            sys.exit(0)
        else:
            print("PHASE 5.6+ INVARIANT VIOLATIONS DETECTED")
            sys.exit(1)
    except InvariantViolation as e:
        print(f"CRITICAL INVARIANT VIOLATION: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"INVARIANT VERIFICATION FAILED: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
