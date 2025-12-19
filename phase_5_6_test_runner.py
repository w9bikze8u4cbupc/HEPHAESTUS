#!/usr/bin/env python3
"""
Phase 5.6 Test Runner - Colorspace Hardening Validation

This script tests the colorspace normalization fixes on the three rulebooks
that failed in Phase 5.5: Jaipur, 7 Wonders Duel, and Viticulture.

Usage:
    python phase_5_6_test_runner.py

Requirements:
    - Failed rulebooks must be present in data/rulebooks/
    - Colorspace normalization must be implemented in src/hephaestus/pdf/colorspace.py
"""

import sys
from pathlib import Path
import subprocess
import json
from typing import Dict, Any, List
import logging

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from hephaestus.logging import get_logger

logger = get_logger(__name__)

# Phase 5.6 test targets - the three rulebooks that failed in Phase 5.5
FAILED_RULEBOOKS = {
    "jaipur": {
        "filename": "Jaipur.pdf",
        "slug": "jaipur",
        "min_images_expected": 10,  # Conservative estimate
        "min_component_detection_rate": 0.80
    },
    "7wd": {
        "filename": "6b-7-wonders-duel-rules.pdf", 
        "slug": "7wd",
        "min_images_expected": 15,
        "min_component_detection_rate": 0.80
    },
    "viticulture": {
        "filename": "a5-viticulture-essential-edition-rulebook.pdf",
        "slug": "viticulture", 
        "min_images_expected": 30,
        "min_component_detection_rate": 0.80
    }
}

# Regression test targets - known good PDFs from Phase 5.5
REGRESSION_RULEBOOKS = {
    "dune_imperium": {
        "filename": "DUNE_IMPERIUM_Rules_2020_10_26.pdf",
        "slug": "dune_imperium",
        "min_images_expected": 20,
        "min_component_detection_rate": 0.70,
        "baseline_extraction_rate": 0.95,  # Expected from Phase 5.5
        "baseline_component_rate": 0.85
    },
    "seti": {
        "filename": "seti-rules-en.pdf",
        "slug": "seti", 
        "min_images_expected": 10,
        "min_component_detection_rate": 0.70,
        "baseline_extraction_rate": 0.95,
        "baseline_component_rate": 0.80
    }
}

def check_prerequisites() -> bool:
    """Check that all required files and directories exist."""
    logger.info("Checking Phase 5.6 prerequisites...")
    
    # Check data/rulebooks directory
    rulebooks_dir = Path("data/rulebooks")
    if not rulebooks_dir.exists():
        logger.error(f"Rulebooks directory not found: {rulebooks_dir}")
        return False
    
    # Check for failed rulebook PDFs
    missing_pdfs = []
    for rulebook_id, config in FAILED_RULEBOOKS.items():
        pdf_path = rulebooks_dir / config["filename"]
        if not pdf_path.exists():
            missing_pdfs.append(config["filename"])
    
    if missing_pdfs:
        logger.error(f"Missing required PDFs: {missing_pdfs}")
        logger.error("Please ensure all failed rulebooks are present in data/rulebooks/")
        return False
    
    # Check colorspace module exists
    colorspace_module = Path("src/hephaestus/pdf/colorspace.py")
    if not colorspace_module.exists():
        logger.error(f"Colorspace normalization module not found: {colorspace_module}")
        return False
    
    logger.info("Prerequisites check PASSED")
    return True


def run_extraction(rulebook_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """Run extraction on a single rulebook and return results."""
    logger.info(f"Running Phase 5.6 extraction for {rulebook_id}...")
    
    # Set up paths
    pdf_path = Path("data/rulebooks") / config["filename"]
    output_dir = Path("eval/phase_5_6_test") / config["slug"]
    
    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Run hephaestus extraction
    cmd = [
        sys.executable, "-m", "hephaestus",
        str(pdf_path),
        "--out", str(output_dir)
    ]
    
    logger.info(f"Executing: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        if result.returncode != 0:
            logger.error(f"Extraction failed for {rulebook_id}")
            logger.error(f"STDOUT: {result.stdout}")
            logger.error(f"STDERR: {result.stderr}")
            return {
                "success": False,
                "error": f"Process failed with code {result.returncode}",
                "stdout": result.stdout,
                "stderr": result.stderr
            }
        
        # Parse results
        manifest_path = output_dir / "manifest.json"
        extraction_log_path = output_dir / "extraction_log.jsonl"
        
        results = {
            "success": True,
            "output_dir": str(output_dir),
            "stdout": result.stdout,
            "stderr": result.stderr
        }
        
        # Load manifest if available
        if manifest_path.exists():
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
                results["manifest"] = manifest
                results["total_items"] = manifest.get("total_items", 0)
                results["extraction_health"] = manifest.get("extraction_health", {})
        else:
            logger.warning(f"No manifest found for {rulebook_id}")
            results["total_items"] = 0
            results["extraction_health"] = {}
        
        # Count actual image files
        images_dir = output_dir / "images" / "all"
        if images_dir.exists():
            image_files = list(images_dir.glob("*.png"))
            results["images_saved"] = len(image_files)
        else:
            results["images_saved"] = 0
        
        # Load extraction log if available
        if extraction_log_path.exists():
            log_entries = []
            with open(extraction_log_path, 'r') as f:
                for line in f:
                    if line.strip():
                        log_entries.append(json.loads(line))
            results["extraction_log"] = log_entries
        
        logger.info(f"Extraction completed for {rulebook_id}: {results['images_saved']} images saved")
        return results
        
    except subprocess.TimeoutExpired:
        logger.error(f"Extraction timed out for {rulebook_id}")
        return {
            "success": False,
            "error": "Process timed out after 5 minutes"
        }
    except Exception as exc:
        logger.error(f"Extraction failed for {rulebook_id}: {exc}")
        return {
            "success": False,
            "error": str(exc)
        }


def validate_invariants(rulebook_id: str, results: Dict[str, Any]) -> Dict[str, Any]:
    """Validate critical invariants for zero silent drops."""
    invariant_checks = {
        "manifest_file_consistency": False,
        "extraction_health_present": False,
        "colorspace_conversion_evidence": False,
        "extraction_log_integrity": False,
        "persistence_boundary_invariants": False
    }
    
    if not results.get("success", False):
        return invariant_checks
    
    output_dir = Path(results["output_dir"])
    manifest = results.get("manifest", {})
    health = results.get("extraction_health", {})
    
    # Check 1: Manifest count matches files on disk
    manifest_items = manifest.get("items", [])
    images_dir = output_dir / "images" / "all"
    
    if images_dir.exists():
        actual_files = list(images_dir.glob("*.png"))
        manifest_count = len(manifest_items)
        file_count = len(actual_files)
        
        # Verify every manifest entry points to existing file
        missing_files = []
        for item in manifest_items:
            file_path = output_dir / item.get("path_all", "")
            if not file_path.exists():
                missing_files.append(str(file_path))
        
        invariant_checks["manifest_file_consistency"] = (
            manifest_count == file_count and len(missing_files) == 0
        )
        
        if not invariant_checks["manifest_file_consistency"]:
            logger.error(f"INVARIANT VIOLATION: Manifest count {manifest_count} != file count {file_count}")
            if missing_files:
                logger.error(f"Missing files: {missing_files[:5]}...")  # Show first 5
    
    # Check 2: Extraction health metrics present and valid
    if health and "images_attempted" in health and "images_saved" in health:
        invariant_checks["extraction_health_present"] = True
        
        # Verify no silent drops: attempted == saved + failures
        attempted = health.get("images_attempted", 0)
        saved = health.get("images_saved", 0)
        failures = health.get("conversion_failures", 0)
        
        if attempted != saved + failures:
            logger.error(f"INVARIANT VIOLATION: attempted {attempted} != saved {saved} + failures {failures}")
            invariant_checks["extraction_health_present"] = False
    
    # Check 3: Colorspace conversion evidence for formerly failing PDFs
    colorspace_dist = health.get("colorspace_distribution", {})
    conversion_ops = health.get("conversion_operations", {})
    
    # For Jaipur, 7WD, Viticulture - should see CMYK conversion
    if rulebook_id in ["jaipur", "7wd", "viticulture"]:
        has_cmyk = any("CMYK" in cs for cs in colorspace_dist.keys())
        has_conversion = any("CMYK_to_RGB" in op for op in conversion_ops.keys())
        invariant_checks["colorspace_conversion_evidence"] = has_cmyk and has_conversion
        
        if not invariant_checks["colorspace_conversion_evidence"]:
            logger.error(f"INVARIANT VIOLATION: No CMYK conversion evidence for {rulebook_id}")
    else:
        invariant_checks["colorspace_conversion_evidence"] = True  # Not applicable
    
    # Check 4: Extraction log integrity
    log_path = output_dir / "extraction_log.jsonl"
    if log_path.exists() and log_path.stat().st_size > 0:
        try:
            # Count lines and verify JSON parsing
            line_count = 0
            with open(log_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    if line.strip():
                        try:
                            entry = json.loads(line)
                            # Verify required fields
                            required_fields = ["rulebook_id", "image_id", "status", "reason_code"]
                            if all(field in entry for field in required_fields):
                                line_count += 1
                            else:
                                logger.error(f"Log line {line_num} missing required fields")
                                break
                        except json.JSONDecodeError as e:
                            logger.error(f"Log line {line_num} invalid JSON: {e}")
                            break
            
            # Verify line count matches attempted images
            images_attempted = health.get("images_attempted", 0)
            if line_count == images_attempted and line_count > 0:
                invariant_checks["extraction_log_integrity"] = True
            else:
                logger.error(f"Log integrity failed: {line_count} lines, {images_attempted} attempted")
                
        except Exception as log_exc:
            logger.error(f"Failed to validate extraction log: {log_exc}")
    else:
        logger.error(f"Extraction log missing or empty: {log_path}")
    
    # Check 5: Persistence boundary invariants
    # For each manifest item, verify file exists and has content
    persistence_violations = []
    for item in manifest_items:
        if "path_all" in item:
            file_path = output_dir / item["path_all"]
            if not file_path.exists():
                persistence_violations.append(f"Manifest references missing file: {file_path}")
            elif file_path.stat().st_size == 0:
                persistence_violations.append(f"Manifest references empty file: {file_path}")
    
    # Verify no orphaned files (files on disk not in manifest)
    if images_dir.exists():
        manifest_files = {item.get("file_name", "") for item in manifest_items}
        disk_files = {f.name for f in images_dir.glob("*.png")}
        orphaned = disk_files - manifest_files
        
        if orphaned:
            persistence_violations.extend([f"Orphaned file: {f}" for f in orphaned])
    
    invariant_checks["persistence_boundary_invariants"] = len(persistence_violations) == 0
    
    if persistence_violations:
        for violation in persistence_violations[:5]:  # Show first 5
            logger.error(f"PERSISTENCE VIOLATION: {violation}")
    
    return invariant_checks


def evaluate_results(rulebook_id: str, config: Dict[str, Any], results: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate extraction results against Phase 5.6 acceptance criteria."""
    logger.info(f"Evaluating results for {rulebook_id}...")
    
    evaluation = {
        "rulebook_id": rulebook_id,
        "success": results.get("success", False),
        "criteria_met": {},
        "invariant_checks": {},
        "overall_pass": False
    }
    
    if not results.get("success", False):
        evaluation["criteria_met"]["extraction_completed"] = False
        evaluation["failure_reason"] = results.get("error", "Unknown error")
        return evaluation
    
    evaluation["criteria_met"]["extraction_completed"] = True
    
    # INVARIANT VALIDATION (must pass before criteria evaluation)
    evaluation["invariant_checks"] = validate_invariants(rulebook_id, results)
    invariants_pass = all(evaluation["invariant_checks"].values())
    
    if not invariants_pass:
        logger.error(f"CRITICAL: {rulebook_id} failed invariant checks - Phase 5.6 incomplete")
        evaluation["overall_pass"] = False
        evaluation["failure_reason"] = "Invariant violations detected"
        return evaluation
    
    # Criterion 1: Extraction Success Rate (images persisted vs attempted)
    health = results.get("extraction_health", {})
    images_attempted = health.get("images_attempted", 0)
    images_saved = health.get("images_saved", 0)
    extraction_success_rate = images_saved / images_attempted if images_attempted > 0 else 0.0
    
    min_expected = config["min_images_expected"]
    
    evaluation["criteria_met"]["images_persisted"] = images_saved > 0
    evaluation["criteria_met"]["meets_minimum_count"] = images_saved >= min_expected
    evaluation["criteria_met"]["acceptable_failure_rate"] = health.get("failure_rate", 1.0) <= 0.20
    evaluation["criteria_met"]["zero_silent_drops"] = health.get("conversion_failures", -1) >= 0
    
    # Store extraction metrics
    evaluation["images_attempted"] = images_attempted
    evaluation["images_saved"] = images_saved
    evaluation["extraction_success_rate"] = extraction_success_rate
    evaluation["min_expected"] = min_expected
    evaluation["extraction_health"] = health
    
    # Criterion 2: Component Detection Rate (components identified vs images evaluated)
    manifest = results.get("manifest", {})
    summary = manifest.get("summary", {})
    
    # Component detection = components classified / total images evaluated
    total_evaluated = summary.get("total_items", 0)
    components_identified = summary.get("components", 0)
    component_detection_rate = components_identified / total_evaluated if total_evaluated > 0 else 0.0
    
    min_detection_rate = config["min_component_detection_rate"]
    evaluation["criteria_met"]["component_detection_rate"] = component_detection_rate >= min_detection_rate
    
    # Store component detection metrics  
    evaluation["total_evaluated"] = total_evaluated
    evaluation["components_identified"] = components_identified
    evaluation["component_detection_rate"] = component_detection_rate
    evaluation["min_detection_rate"] = min_detection_rate
    
    # Overall pass/fail
    all_criteria = [
        evaluation["criteria_met"]["extraction_completed"],
        evaluation["criteria_met"]["images_persisted"],
        evaluation["criteria_met"]["acceptable_failure_rate"],
        evaluation["criteria_met"]["zero_silent_drops"],
        evaluation["criteria_met"]["component_detection_rate"]
    ]
    
    evaluation["overall_pass"] = all(all_criteria) and invariants_pass
    evaluation["criteria_passed"] = sum(all_criteria)
    evaluation["criteria_total"] = len(all_criteria)
    
    # Log results with proper metrics
    if evaluation["overall_pass"]:
        logger.info(f"✅ {rulebook_id} PASSED all Phase 5.6 criteria")
        logger.info(f"  Extraction: {images_saved}/{images_attempted} ({extraction_success_rate:.1%})")
        logger.info(f"  Components: {components_identified}/{total_evaluated} ({component_detection_rate:.1%})")
    else:
        logger.warning(f"❌ {rulebook_id} FAILED Phase 5.6 criteria ({evaluation['criteria_passed']}/{evaluation['criteria_total']})")
        for criterion, passed in evaluation["criteria_met"].items():
            status = "✅" if passed else "❌"
            logger.info(f"  {status} {criterion}")
    
    return evaluation


def generate_phase_5_6_report(evaluations: List[Dict[str, Any]]) -> None:
    """Generate comprehensive Phase 5.6 test report."""
    logger.info("Generating Phase 5.6 test report...")
    
    # Calculate overall statistics
    total_rulebooks = len(evaluations)
    passed_rulebooks = sum(1 for e in evaluations if e["overall_pass"])
    failed_rulebooks = total_rulebooks - passed_rulebooks
    
    # Create report
    report_path = Path("eval/phase_5_6_test/phase_5_6_report.md")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("# Phase 5.6 Colorspace Hardening Test Report\n\n")
        f.write(f"**Generated:** {Path(__file__).name} on {Path.cwd()}\n")
        f.write(f"**Test Date:** 2025-12-19\n\n")
        
        f.write("## Executive Summary\n\n")
        f.write(f"- **Total Rulebooks Tested:** {total_rulebooks}\n")
        f.write(f"- **Passed:** {passed_rulebooks}\n")
        f.write(f"- **Failed:** {failed_rulebooks}\n")
        f.write(f"- **Success Rate:** {passed_rulebooks/total_rulebooks:.1%}\n\n")
        
        if passed_rulebooks == total_rulebooks:
            f.write("🎉 **PHASE 5.6 ACCEPTANCE CRITERIA MET** - All failed rulebooks now functional\n\n")
        else:
            f.write("⚠️ **PHASE 5.6 ACCEPTANCE CRITERIA NOT MET** - Additional work required\n\n")
        
        f.write("## Individual Rulebook Results\n\n")
        
        for evaluation in evaluations:
            rulebook_id = evaluation["rulebook_id"]
            status = "✅ PASS" if evaluation["overall_pass"] else "❌ FAIL"
            
            f.write(f"### {rulebook_id.upper()} - {status}\n\n")
            
            if evaluation.get("success", False):
                f.write("**Extraction Results:**\n")
                f.write(f"- Images Attempted: {evaluation.get('images_attempted', 0)}\n")
                f.write(f"- Images Saved: {evaluation.get('images_saved', 0)}\n")
                f.write(f"- Extraction Success Rate: {evaluation.get('extraction_success_rate', 0):.1%}\n")
                f.write(f"- Total Images Evaluated: {evaluation.get('total_evaluated', 0)}\n")
                f.write(f"- Components Identified: {evaluation.get('components_identified', 0)}\n")
                f.write(f"- Component Detection Rate: {evaluation.get('component_detection_rate', 0):.1%}\n")
                
                health = evaluation.get("extraction_health", {})
                if health:
                    f.write(f"- Conversion Failure Rate: {health.get('failure_rate', 0):.1%}\n")
                    f.write(f"- Colorspace Distribution: {health.get('colorspace_distribution', {})}\n")
                    f.write(f"- Conversion Operations: {health.get('conversion_operations', {})}\n")
                
                f.write("\n**Invariant Checks:**\n")
                invariants = evaluation.get("invariant_checks", {})
                for check, passed in invariants.items():
                    status_icon = "✅" if passed else "❌"
                    f.write(f"- {status_icon} {check.replace('_', ' ').title()}\n")
                
                f.write("\n**Criteria Assessment:**\n")
                for criterion, passed in evaluation["criteria_met"].items():
                    status_icon = "✅" if passed else "❌"
                    f.write(f"- {status_icon} {criterion.replace('_', ' ').title()}\n")
            else:
                f.write(f"**Extraction Failed:** {evaluation.get('failure_reason', 'Unknown error')}\n")
            
            f.write("\n")
        
        f.write("## Phase 6 Readiness\n\n")
        if passed_rulebooks == total_rulebooks:
            f.write("✅ **Phase 6 is UNBLOCKED** - All colorspace issues resolved\n\n")
            f.write("The following Phase 5.6 objectives have been achieved:\n")
            f.write("- Zero silent drops across all failed rulebooks\n")
            f.write("- >80% component detection on recovered PDFs\n")
            f.write("- Robust colorspace normalization implementation\n")
            f.write("- Health metrics integration in manifests\n")
        else:
            f.write("🚫 **Phase 6 remains BLOCKED** - Colorspace issues not fully resolved\n\n")
            f.write("Additional work required:\n")
            for evaluation in evaluations:
                if not evaluation["overall_pass"]:
                    f.write(f"- Fix remaining issues in {evaluation['rulebook_id']}\n")
        
        f.write("\n---\n")
        f.write("*This report was generated by the Phase 5.6 automated test runner*\n")
    
    logger.info(f"Phase 5.6 report written to {report_path}")
    print(f"\n📊 Phase 5.6 test report: {report_path}")


def run_regression_tests() -> List[Dict[str, Any]]:
    """Run regression tests on known-good PDFs to ensure no degradation."""
    print("\n🔄 Running regression tests on known-good PDFs...")
    
    regression_evaluations = []
    
    for rulebook_id, config in REGRESSION_RULEBOOKS.items():
        print(f"\n📋 Regression testing {rulebook_id}...")
        
        # Run extraction
        results = run_extraction(rulebook_id, config)
        
        # Evaluate with regression-specific criteria
        evaluation = evaluate_results(rulebook_id, config, results)
        
        # Additional regression checks
        if evaluation.get("success", False):
            extraction_rate = evaluation.get("extraction_success_rate", 0.0)
            component_rate = evaluation.get("component_detection_rate", 0.0)
            
            baseline_extraction = config.get("baseline_extraction_rate", 0.90)
            baseline_component = config.get("baseline_component_rate", 0.70)
            
            # Check for regression (allow 5% tolerance)
            extraction_regression = extraction_rate < (baseline_extraction - 0.05)
            component_regression = component_rate < (baseline_component - 0.05)
            
            evaluation["regression_detected"] = extraction_regression or component_regression
            evaluation["baseline_extraction_rate"] = baseline_extraction
            evaluation["baseline_component_rate"] = baseline_component
            
            if evaluation["regression_detected"]:
                logger.error(f"REGRESSION DETECTED in {rulebook_id}:")
                if extraction_regression:
                    logger.error(f"  Extraction: {extraction_rate:.1%} < {baseline_extraction:.1%}")
                if component_regression:
                    logger.error(f"  Component: {component_rate:.1%} < {baseline_component:.1%}")
                evaluation["overall_pass"] = False
        
        regression_evaluations.append(evaluation)
        
        # Print immediate feedback
        if evaluation["overall_pass"]:
            print(f"✅ {rulebook_id} regression test PASSED")
        else:
            print(f"❌ {rulebook_id} regression test FAILED")
    
    return regression_evaluations


def main():
    """Main Phase 5.6 test runner."""
    print("🔧 Phase 5.6 Colorspace Hardening Test Runner")
    print("=" * 50)
    
    # Check prerequisites
    if not check_prerequisites():
        print("❌ Prerequisites check failed - cannot proceed")
        sys.exit(1)
    
    # Run extractions on all failed rulebooks
    evaluations = []
    
    for rulebook_id, config in FAILED_RULEBOOKS.items():
        print(f"\n🧪 Testing {rulebook_id}...")
        
        # Run extraction
        results = run_extraction(rulebook_id, config)
        
        # Evaluate results
        evaluation = evaluate_results(rulebook_id, config, results)
        evaluations.append(evaluation)
        
        # Print immediate feedback
        if evaluation["overall_pass"]:
            print(f"✅ {rulebook_id} PASSED")
        else:
            print(f"❌ {rulebook_id} FAILED ({evaluation['criteria_passed']}/{evaluation['criteria_total']} criteria)")
    
    # Run regression tests
    regression_evaluations = run_regression_tests()
    
    # Generate comprehensive report
    print(f"\n📊 Generating Phase 5.6 test report...")
    generate_phase_5_6_report(evaluations + regression_evaluations)
    
    # Final summary
    failed_tests = sum(1 for e in evaluations if not e["overall_pass"])
    regression_failures = sum(1 for e in regression_evaluations if not e["overall_pass"])
    total_failed = len(evaluations)
    total_regression = len(regression_evaluations)
    
    print(f"\n🏁 Phase 5.6 Test Summary:")
    print(f"   Failed Rulebooks: {total_failed - failed_tests}/{total_failed} recovered")
    print(f"   Regression Tests: {total_regression - regression_failures}/{total_regression} passed")
    
    if failed_tests == 0 and regression_failures == 0:
        print("🎉 PHASE 5.6 COMPLETE - Phase 6 is unblocked!")
        sys.exit(0)
    else:
        print("⚠️  PHASE 5.6 INCOMPLETE - Additional work required")
        if failed_tests > 0:
            print(f"     {failed_tests} failed rulebooks still not recovered")
        if regression_failures > 0:
            print(f"     {regression_failures} regression failures detected")
        sys.exit(1)


if __name__ == "__main__":
    main()