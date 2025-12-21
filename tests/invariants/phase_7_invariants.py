#!/usr/bin/env python3
"""
Phase 7 Corpus Analytics Invariants

Structural invariants for corpus-level analytics to ensure:
1. Analytics schema consistency and completeness
2. Evidence traceability to source artifacts
3. Mathematical consistency of aggregated metrics
4. Report generation completeness and accuracy

These invariants extend Phase 5.6+ invariants with corpus-level validation.

Usage:
    python tests/invariants/phase_7_invariants.py <analytics_dir>
    python -m tests.invariants.phase_7_invariants <analytics_dir>
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any


class InvariantViolation(Exception):
    """Raised when a structural invariant is violated."""
    pass


class Phase7Invariants:
    """Phase 7 corpus analytics invariant verification."""

    def __init__(self, analytics_dir: Path):
        self.analytics_dir = analytics_dir
        self.violations: List[str] = []

    def verify_all_invariants(self) -> bool:
        """
        Verify all Phase 7 corpus analytics invariants.

        Returns:
            True if all invariants pass, False otherwise

        Raises:
            InvariantViolation: If critical structural invariants are violated
        """
        if not self.analytics_dir.exists():
            raise InvariantViolation(f"Analytics directory not found: {self.analytics_dir}")

        invariants = {
            "corpus_analytics_exists": False,
            "schema_version_valid": False,
            "analytics_completeness": False,
            "aggregate_consistency": False,
            "evidence_traceability": False,
            "report_generation": False,
            "mathematical_consistency": False
        }

        # Load corpus analytics
        analytics_file = self.analytics_dir / "corpus_analytics.json"
        if not analytics_file.exists():
            raise InvariantViolation(f"Corpus analytics file not found: {analytics_file}")

        invariants["corpus_analytics_exists"] = True

        with open(analytics_file, 'r', encoding='utf-8') as f:
            analytics = json.load(f)

        # INVARIANT 1: Schema version validation
        invariants["schema_version_valid"] = self._verify_schema_version(analytics)

        # INVARIANT 2: Analytics completeness
        invariants["analytics_completeness"] = self._verify_analytics_completeness(analytics)

        # INVARIANT 3: Aggregate consistency
        invariants["aggregate_consistency"] = self._verify_aggregate_consistency(analytics)

        # INVARIANT 4: Evidence traceability
        invariants["evidence_traceability"] = self._verify_evidence_traceability(analytics)

        # INVARIANT 5: Report generation
        invariants["report_generation"] = self._verify_report_generation()

        # INVARIANT 6: Mathematical consistency
        invariants["mathematical_consistency"] = self._verify_mathematical_consistency(analytics)

        all_passed = all(invariants.values())
        if not all_passed:
            failed_invariants = [k for k, v in invariants.items() if not v]
            raise InvariantViolation(
                f"CRITICAL: Phase 7 invariant violations: {failed_invariants}"
            )

        return True

    def _verify_schema_version(self, analytics: Dict) -> bool:
        """INVARIANT: Valid schema version and structure."""
        required_fields = [
            "schema_version", "analysis_timestamp", "input_directory",
            "rulebook_analytics", "corpus_aggregates"
        ]

        if not all(field in analytics for field in required_fields):
            self.violations.append("Missing required top-level fields")
            return False

        if analytics["schema_version"] != "1.0.0":
            self.violations.append(f"Invalid schema version: {analytics['schema_version']}")
            return False

        return True

    def _verify_analytics_completeness(self, analytics: Dict) -> bool:
        """INVARIANT: Complete analytics for all rulebooks."""
        rulebook_analytics = analytics.get("rulebook_analytics", [])

        if not rulebook_analytics:
            self.violations.append("No rulebook analytics found")
            return False

        required_sections = [
            "identity", "pdf_characteristics", "extraction_outcome",
            "classification_outcome", "deduplication_outcome",
            "text_extraction_outcome", "failure_taxonomy"
        ]

        for rb in rulebook_analytics:
            if not all(section in rb for section in required_sections):
                missing = [s for s in required_sections if s not in rb]
                self.violations.append(f"Missing sections in {rb.get('identity', {}).get('rulebook_id', 'unknown')}: {missing}")
                return False

            # Verify enhanced fields are present
            extraction = rb.get("extraction_outcome", {})
            enhanced_extraction_fields = [
                "failures_by_page_bucket", "silent_drops_proof", "failed_image_ids",
                "failure_patterns", "failure_severity_distribution"
            ]
            if not all(field in extraction for field in enhanced_extraction_fields):
                missing = [f for f in enhanced_extraction_fields if f not in extraction]
                self.violations.append(f"Missing enhanced extraction fields: {missing}")
                return False

            classification = rb.get("classification_outcome", {})
            enhanced_classification_fields = [
                "confidence_histogram", "low_confidence_components",
                "is_anomalous", "anomaly_details"
            ]
            if not all(field in classification for field in enhanced_classification_fields):
                missing = [f for f in enhanced_classification_fields if f not in classification]
                self.violations.append(f"Missing enhanced classification fields: {missing}")
                return False

        return True

    def _verify_aggregate_consistency(self, analytics: Dict) -> bool:
        """INVARIANT: Corpus aggregates match sum of individual rulebooks."""
        rulebook_analytics = analytics.get("rulebook_analytics", [])
        corpus_aggregates = analytics.get("corpus_aggregates", {})

        # Verify total rulebooks
        expected_total = len(rulebook_analytics)
        actual_total = corpus_aggregates.get("total_rulebooks", 0)
        if expected_total != actual_total:
            self.violations.append(f"Rulebook count mismatch: {expected_total} != {actual_total}")
            return False

        # Verify total pages
        expected_pages = sum(rb["pdf_characteristics"]["page_count"] for rb in rulebook_analytics)
        actual_pages = corpus_aggregates.get("total_pages", 0)
        if expected_pages != actual_pages:
            self.violations.append(f"Page count mismatch: {expected_pages} != {actual_pages}")
            return False

        # Verify total images attempted
        expected_attempted = sum(rb["extraction_outcome"]["images_attempted"] for rb in rulebook_analytics)
        actual_attempted = corpus_aggregates.get("total_images_attempted", 0)
        if expected_attempted != actual_attempted:
            self.violations.append(f"Images attempted mismatch: {expected_attempted} != {actual_attempted}")
            return False

        # Verify total images saved
        expected_saved = sum(rb["extraction_outcome"]["images_saved"] for rb in rulebook_analytics)
        actual_saved = corpus_aggregates.get("total_images_saved", 0)
        if expected_saved != actual_saved:
            self.violations.append(f"Images saved mismatch: {expected_saved} != {actual_saved}")
            return False

        # Verify success rate calculation
        if actual_attempted > 0:
            expected_success_rate = actual_saved / actual_attempted
            actual_success_rate = corpus_aggregates.get("corpus_success_rate", 0)
            if abs(expected_success_rate - actual_success_rate) > 0.001:
                self.violations.append(f"Success rate mismatch: {expected_success_rate:.4f} != {actual_success_rate:.4f}")
                return False

        return True

    def _verify_evidence_traceability(self, analytics: Dict) -> bool:
        """INVARIANT: All analytics are traceable to source artifacts."""
        input_directory = Path(analytics.get("input_directory", ""))
        
        if not input_directory.exists():
            self.violations.append(f"Input directory not found: {input_directory}")
            return False

        for rb in analytics.get("rulebook_analytics", []):
            rulebook_id = rb.get("identity", {}).get("rulebook_id", "unknown")
            rulebook_dir = input_directory / rulebook_id

            if not rulebook_dir.exists():
                self.violations.append(f"Rulebook directory not found: {rulebook_dir}")
                return False

            # Verify required artifacts exist
            required_artifacts = ["manifest.json", "extraction_log.jsonl"]
            for artifact in required_artifacts:
                artifact_path = rulebook_dir / artifact
                if not artifact_path.exists():
                    self.violations.append(f"Required artifact missing: {artifact_path}")
                    return False

            # Verify text artifacts if referenced
            if rb.get("pdf_characteristics", {}).get("has_text_artifacts", False):
                # Should have page_text.jsonl or equivalent
                text_artifact_found = False
                for possible_name in ["page_text.jsonl", "text_artifacts.jsonl"]:
                    if (rulebook_dir / possible_name).exists():
                        text_artifact_found = True
                        break
                
                if not text_artifact_found:
                    self.violations.append(f"Text artifacts claimed but not found for {rulebook_id}")
                    return False

        return True

    def _verify_report_generation(self) -> bool:
        """INVARIANT: All required reports can be generated."""
        expected_reports = [
            "analytics_overview.md",
            "extraction_failures.md", 
            "classification_analysis.md",
            "deduplication_report.md",
            "text_extraction_report.md"
        ]

        for report_name in expected_reports:
            report_path = self.analytics_dir / report_name
            if not report_path.exists():
                self.violations.append(f"Required report missing: {report_name}")
                return False

            # Verify report is not empty
            if report_path.stat().st_size == 0:
                self.violations.append(f"Report is empty: {report_name}")
                return False

            # Verify report contains evidence traceability
            with open(report_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if "Evidence Sources" not in content and "evidence" not in content.lower():
                    self.violations.append(f"Report lacks evidence traceability: {report_name}")
                    return False

        return True

    def _verify_mathematical_consistency(self, analytics: Dict) -> bool:
        """INVARIANT: Mathematical relationships are consistent."""
        for rb in analytics.get("rulebook_analytics", []):
            rulebook_id = rb.get("identity", {}).get("rulebook_id", "unknown")

            # Extraction outcome consistency
            extraction = rb.get("extraction_outcome", {})
            attempted = extraction.get("images_attempted", 0)
            saved = extraction.get("images_saved", 0)
            failed = extraction.get("conversion_failures", 0)

            if attempted != saved + failed:
                self.violations.append(f"{rulebook_id}: Extraction math error: {attempted} != {saved} + {failed}")
                return False

            # Success rate consistency
            if attempted > 0:
                expected_success = saved / attempted
                actual_success = extraction.get("success_rate", 0)
                if abs(expected_success - actual_success) > 0.001:
                    self.violations.append(f"{rulebook_id}: Success rate error: {expected_success:.4f} != {actual_success:.4f}")
                    return False

            # Classification outcome consistency
            classification = rb.get("classification_outcome", {})
            total_components = classification.get("total_components", 0)
            distribution = classification.get("classification_distribution", {})
            distribution_sum = sum(distribution.values())

            if total_components != distribution_sum:
                self.violations.append(f"{rulebook_id}: Classification count error: {total_components} != {distribution_sum}")
                return False

            # Confidence histogram consistency
            histogram = classification.get("confidence_histogram", {})
            histogram_sum = sum(histogram.values())
            if histogram_sum > 0 and histogram_sum != total_components:
                self.violations.append(f"{rulebook_id}: Confidence histogram error: {histogram_sum} != {total_components}")
                return False

            # Deduplication consistency
            dedup = rb.get("deduplication_outcome", {})
            total_images = dedup.get("total_images", 0)
            canonical = dedup.get("canonical_images", 0)
            duplicates = dedup.get("duplicate_images", 0)

            if total_images != canonical + duplicates:
                self.violations.append(f"{rulebook_id}: Dedup math error: {total_images} != {canonical} + {duplicates}")
                return False

        return True


def verify_phase_7_invariants(analytics_dir: Path) -> bool:
    """
    Verify Phase 7 corpus analytics invariants.

    Args:
        analytics_dir: Directory containing corpus analytics and reports

    Returns:
        True if all invariants pass

    Raises:
        InvariantViolation: If critical invariants are violated
    """
    verifier = Phase7Invariants(analytics_dir)
    return verifier.verify_all_invariants()


def main():
    """CLI entry point for Phase 7 invariant verification."""
    import sys

    analytics_dir = Path("analytics/phase_7_full")
    if len(sys.argv) > 1:
        analytics_dir = Path(sys.argv[1])

    try:
        success = verify_phase_7_invariants(analytics_dir)
        if success:
            print("✅ ALL PHASE 7 INVARIANTS VERIFIED")
            sys.exit(0)
        else:
            print("❌ PHASE 7 INVARIANT VIOLATIONS DETECTED")
            sys.exit(1)
    except InvariantViolation as e:
        print(f"CRITICAL PHASE 7 INVARIANT VIOLATION: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"PHASE 7 INVARIANT VERIFICATION FAILED: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
