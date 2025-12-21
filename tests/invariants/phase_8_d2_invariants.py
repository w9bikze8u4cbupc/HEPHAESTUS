"""
Phase 8 D2 Invariants: QA Scorecard Schema Versioning & Analytical Expansion

RED BY DESIGN: These invariants MUST fail initially to establish enforcement before implementation.

Validates:
- Schema versioning (8.1 backward compatibility, 8.2 additive fields)
- Invariant tiering (Tier 0/1/2 enforcement)
- Deterministic expansion (new metrics without regression)
- CI signal quality (clear failure messages)
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Tuple
import hashlib


# Tier 2 Exploratory Fields Manifest
TIER_2_EXPLORATORY_MANIFEST = {
    'experimental_risk_score': {
        'expected_type': 'float',
        'expected_range': '[0.0, 1.0]',
        'planned_source': 'weighted composite of extraction_risk + classification_risk + deduplication_risk',
        'promotion_criteria': 'stable formula validated across 10+ rulebooks, correlation with manual QA assessment'
    },
    'ml_confidence_prediction': {
        'expected_type': 'dict',
        'expected_range': '{"predicted_accuracy": [0.0, 1.0], "confidence_interval": [0.0, 1.0]}',
        'planned_source': 'classification_outcome.confidence_stats + historical accuracy data',
        'promotion_criteria': 'ML model trained and validated, prediction accuracy >80% on test set'
    },
    'cross_rulebook_similarity': {
        'expected_type': 'dict', 
        'expected_range': '{"most_similar": "rulebook_id", "similarity_score": [0.0, 1.0], "similarity_basis": "string"}',
        'planned_source': 'component_type_entropy + classification_distribution + pdf_characteristics',
        'promotion_criteria': 'similarity algorithm validated, useful for QA triage and anomaly detection'
    }
}


def validate_phase_8_d2_scorecards(analytics_dir: Path, qa_dir: Path) -> Dict[str, Any]:
    """Validate Phase 8 D2 QA scorecard schema versioning and analytical expansion."""
    
    results = {
        "phase": "8_d2",
        "validation_type": "schema_versioning_and_expansion",
        "checks": [],
        "passed": True,
        "summary": {},
        "tier_failures": {"tier_0": [], "tier_1": [], "tier_2": []}
    }
    
    # Load corpus analytics
    analytics_file = analytics_dir / "corpus_analytics.json"
    if not analytics_file.exists():
        _add_tier_0_failure(results, "corpus_analytics_missing", 
                           f"TIER 0 FOUNDATIONAL: corpus_analytics.json not found in {analytics_dir}")
        return results
    
    with open(analytics_file, 'r') as f:
        corpus_data = json.load(f)
    
    rulebooks = corpus_data['rulebook_analytics']
    rulebook_ids = [rb['identity']['rulebook_id'] for rb in rulebooks]
    
    results["summary"]["expected_rulebooks"] = len(rulebook_ids)
    
    # Check QA directory structure
    qa_rulebooks_dir = qa_dir / "rulebooks"
    if not qa_rulebooks_dir.exists():
        _add_tier_0_failure(results, "qa_directory_missing",
                           "TIER 0 FOUNDATIONAL: qa/rulebooks directory not found")
        return results
    
    # TIER 0 (Foundational) - Phase 8 D1 Compatibility
    _validate_tier_0_compatibility(results, qa_rulebooks_dir, rulebook_ids)
    
    # TIER 1 (Analytical) - Schema Versioning
    _validate_tier_1_schema_versioning(results, qa_rulebooks_dir, rulebook_ids)
    
    # TIER 1 (Analytical) - Additive Fields
    _validate_tier_1_additive_fields(results, qa_rulebooks_dir, rulebook_ids)
    
    # TIER 1 (Analytical) - Determinism Contract
    _validate_tier_1_determinism(results, qa_rulebooks_dir, rulebook_ids)
    
    # TIER 2 (Exploratory) - Future Metrics
    _validate_tier_2_exploratory(results, qa_rulebooks_dir, rulebook_ids)
    
    # Overall pass/fail based on Tier 0 and Tier 1 only
    tier_0_passed = len(results["tier_failures"]["tier_0"]) == 0
    tier_1_passed = len(results["tier_failures"]["tier_1"]) == 0
    results["passed"] = tier_0_passed and tier_1_passed
    
    return results


def _add_tier_0_failure(results: Dict[str, Any], name: str, message: str):
    """Add a Tier 0 (foundational) failure."""
    results["checks"].append({"name": name, "passed": False, "message": message, "tier": 0})
    results["tier_failures"]["tier_0"].append(name)
    results["passed"] = False


def _add_tier_1_failure(results: Dict[str, Any], name: str, message: str):
    """Add a Tier 1 (analytical) failure."""
    results["checks"].append({"name": name, "passed": False, "message": message, "tier": 1})
    results["tier_failures"]["tier_1"].append(name)
    results["passed"] = False


def _add_tier_2_failure(results: Dict[str, Any], name: str, message: str):
    """Add a Tier 2 (exploratory) failure - does not block CI."""
    results["checks"].append({"name": name, "passed": False, "message": message, "tier": 2})
    results["tier_failures"]["tier_2"].append(name)
    # Note: Tier 2 failures do NOT set results["passed"] = False


def _add_success(results: Dict[str, Any], name: str, message: str, tier: int):
    """Add a successful check."""
    results["checks"].append({"name": name, "passed": True, "message": message, "tier": tier})


def _validate_tier_0_compatibility(results: Dict[str, Any], qa_dir: Path, rulebook_ids: List[str]):
    """TIER 0: Validate Phase 8 D1 compatibility (immutable)."""
    
    missing_files = []
    invalid_json = []
    missing_d1_fields = []
    
    # Phase 8 D1 required fields (immutable)
    d1_required_fields = ['rulebook_id', 'source_pdf', 'total_images', 
                         'success_rate', 'failure_rate', 'analytics_source']
    
    for rulebook_id in rulebook_ids:
        json_file = qa_dir / f"{rulebook_id}.json"
        md_file = qa_dir / f"{rulebook_id}.md"
        
        # Check JSON file exists and is valid
        if not json_file.exists():
            missing_files.append(f"{rulebook_id}.json")
        else:
            try:
                with open(json_file, 'r') as f:
                    scorecard_data = json.load(f)
                
                # Check Phase 8 D1 required fields (IMMUTABLE)
                for field in d1_required_fields:
                    if field not in scorecard_data:
                        missing_d1_fields.append(f"{rulebook_id}.json missing D1 field: {field}")
                
            except json.JSONDecodeError:
                invalid_json.append(f"{rulebook_id}.json")
        
        # Check MD file exists
        if not md_file.exists():
            missing_files.append(f"{rulebook_id}.md")
    
    # Report Tier 0 failures
    if missing_files:
        _add_tier_0_failure(results, "d1_files_missing", 
                           f"TIER 0 FOUNDATIONAL: Phase 8 D1 files missing: {missing_files}")
    else:
        _add_success(results, "d1_files_exist", "All Phase 8 D1 files exist", 0)
    
    if invalid_json:
        _add_tier_0_failure(results, "d1_json_invalid", 
                           f"TIER 0 FOUNDATIONAL: Invalid JSON files: {invalid_json}")
    else:
        _add_success(results, "d1_json_valid", "All JSON files valid", 0)
    
    if missing_d1_fields:
        _add_tier_0_failure(results, "d1_fields_missing", 
                           f"TIER 0 FOUNDATIONAL: Phase 8 D1 required fields missing: {missing_d1_fields}")
    else:
        _add_success(results, "d1_fields_present", "All Phase 8 D1 required fields present", 0)


def _validate_tier_1_schema_versioning(results: Dict[str, Any], qa_dir: Path, rulebook_ids: List[str]):
    """TIER 1: Validate schema versioning compliance."""
    
    missing_schema_version = []
    invalid_schema_version = []
    
    for rulebook_id in rulebook_ids:
        json_file = qa_dir / f"{rulebook_id}.json"
        
        if json_file.exists():
            try:
                with open(json_file, 'r') as f:
                    scorecard_data = json.load(f)
                
                # RED BY DESIGN: This MUST fail initially
                if "schema_version" not in scorecard_data:
                    missing_schema_version.append(rulebook_id)
                else:
                    version = scorecard_data["schema_version"]
                    if version not in ["8.1", "8.2"]:
                        invalid_schema_version.append(f"{rulebook_id}: {version}")
                
            except json.JSONDecodeError:
                # Already caught in Tier 0
                pass
    
    # RED BY DESIGN: These MUST fail initially
    if missing_schema_version:
        _add_tier_1_failure(results, "schema_version_missing", 
                           f"TIER 1 ANALYTICAL: schema_version field missing in: {missing_schema_version}. "
                           f"REQUIRED: All scorecards must include schema_version (8.1 or 8.2)")
    else:
        _add_success(results, "schema_version_present", "All scorecards have schema_version", 1)
    
    if invalid_schema_version:
        _add_tier_1_failure(results, "schema_version_invalid", 
                           f"TIER 1 ANALYTICAL: Invalid schema_version values: {invalid_schema_version}. "
                           f"REQUIRED: Must be '8.1' or '8.2'")
    else:
        _add_success(results, "schema_version_valid", "All schema_version values valid", 1)


def _validate_tier_1_additive_fields(results: Dict[str, Any], qa_dir: Path, rulebook_ids: List[str]):
    """TIER 1: Validate additive fields for 8.2 scorecards."""
    
    # RED BY DESIGN: These fields don't exist yet
    d2_additive_fields = ['coverage_density', 'classification_confidence_distribution', 'component_type_entropy']
    
    missing_d2_fields = []
    invalid_d2_values = []
    v82_scorecards = []
    
    for rulebook_id in rulebook_ids:
        json_file = qa_dir / f"{rulebook_id}.json"
        
        if json_file.exists():
            try:
                with open(json_file, 'r') as f:
                    scorecard_data = json.load(f)
                
                if scorecard_data.get("schema_version") == "8.2":
                    v82_scorecards.append(rulebook_id)
                    
                    # Check for D2 additive fields
                    for field in d2_additive_fields:
                        if field not in scorecard_data:
                            missing_d2_fields.append(f"{rulebook_id}.{field}")
                    
                    # Tier 1 monotonicity checks for 8.2 scorecards
                    if 'classification_confidence_distribution' in scorecard_data:
                        dist = scorecard_data['classification_confidence_distribution']
                        if isinstance(dist, dict) and 'known_ratio' in dist and 'unknown_ratio' in dist:
                            known = dist['known_ratio']
                            unknown = dist['unknown_ratio']
                            ratio_sum = known + unknown
                            # Check ratios sum to 1.0 within epsilon
                            if abs(ratio_sum - 1.0) > 1e-9:
                                invalid_d2_values.append(f"{rulebook_id}.classification_confidence_distribution ratios sum to {ratio_sum}, expected 1.0")
                            # Check ratios are in valid range
                            if not (0.0 <= known <= 1.0) or not (0.0 <= unknown <= 1.0):
                                invalid_d2_values.append(f"{rulebook_id}.classification_confidence_distribution ratios out of [0,1] range")
                    
                    if 'coverage_density' in scorecard_data:
                        coverage = scorecard_data['coverage_density']
                        if not (0.0 <= coverage <= 1.0):
                            invalid_d2_values.append(f"{rulebook_id}.coverage_density = {coverage}, expected [0,1]")
                    
                    if 'component_type_entropy' in scorecard_data:
                        entropy = scorecard_data['component_type_entropy']
                        if entropy < 0.0:
                            invalid_d2_values.append(f"{rulebook_id}.component_type_entropy = {entropy}, expected >= 0")
                
            except json.JSONDecodeError:
                # Already caught in Tier 0
                pass
    
    # RED BY DESIGN: This MUST fail initially (no 8.2 scorecards exist yet)
    if not v82_scorecards:
        _add_tier_1_failure(results, "no_v82_scorecards", 
                           f"TIER 1 ANALYTICAL: No schema_version 8.2 scorecards found. "
                           f"REQUIRED: Phase 8 D2 must generate 8.2 scorecards with additive fields")
    else:
        _add_success(results, "v82_scorecards_exist", f"Found {len(v82_scorecards)} v8.2 scorecards", 1)
    
    if missing_d2_fields:
        _add_tier_1_failure(results, "d2_additive_fields_missing", 
                           f"TIER 1 ANALYTICAL: Phase 8 D2 additive fields missing: {missing_d2_fields}. "
                           f"REQUIRED: v8.2 scorecards must include: {d2_additive_fields}")
    elif v82_scorecards:  # Only check if we have v8.2 scorecards
        _add_success(results, "d2_additive_fields_present", "All D2 additive fields present", 1)
    
    if invalid_d2_values:
        _add_tier_1_failure(results, "d2_field_values_invalid", 
                           f"TIER 1 ANALYTICAL: Invalid D2 field values: {invalid_d2_values}. "
                           f"REQUIRED: All D2 metrics must satisfy monotonicity constraints")
    elif v82_scorecards:  # Only check if we have v8.2 scorecards
        _add_success(results, "d2_field_values_valid", "All D2 field values satisfy constraints", 1)


def _validate_tier_1_determinism(results: Dict[str, Any], qa_dir: Path, rulebook_ids: List[str]):
    """TIER 1: Validate deterministic output contract."""
    
    # Check for deterministic JSON key ordering and stable float representation
    non_deterministic_files = []
    first_diff_details = None
    
    for rulebook_id in rulebook_ids:
        json_file = qa_dir / f"{rulebook_id}.json"
        
        if json_file.exists():
            try:
                with open(json_file, 'r') as f:
                    content = f.read()
                
                # Parse and re-serialize to check determinism
                scorecard_data = json.loads(content)
                canonical_content = json.dumps(scorecard_data, sort_keys=True, indent=2)
                
                # Check if content is deterministically formatted
                if content.strip() != canonical_content.strip():
                    non_deterministic_files.append(rulebook_id)
                    
                    # Capture diff details for first failing file only
                    if first_diff_details is None:
                        import difflib
                        actual_lines = content.strip().split('\n')
                        expected_lines = canonical_content.strip().split('\n')
                        diff_lines = list(difflib.unified_diff(
                            actual_lines, expected_lines,
                            fromfile=f"actual_{rulebook_id}.json",
                            tofile=f"expected_{rulebook_id}.json",
                            lineterm='',
                            n=3
                        ))
                        # Limit diff output to prevent log flooding
                        if len(diff_lines) > 50:
                            diff_lines = diff_lines[:47] + ['...', '(diff truncated - too many lines)', '...']
                        first_diff_details = '\n'.join(diff_lines)
                
            except json.JSONDecodeError:
                # Already caught in Tier 0
                pass
    
    if non_deterministic_files:
        failure_message = f"TIER 1 ANALYTICAL: Non-deterministic JSON formatting in: {non_deterministic_files}. " \
                         f"REQUIRED: All JSON must be deterministically formatted (sorted keys, stable floats)"
        if first_diff_details:
            failure_message += f"\n\nFirst failing file diff:\n{first_diff_details}"
        _add_tier_1_failure(results, "non_deterministic_output", failure_message)
    else:
        _add_success(results, "deterministic_output", "All JSON output is deterministic", 1)


def _validate_tier_2_exploratory(results: Dict[str, Any], qa_dir: Path, rulebook_ids: List[str]):
    """TIER 2: Validate exploratory metrics (warnings only)."""
    
    # Check implementation status for each exploratory field
    field_implementation_status = {}
    field_validation_errors = []
    
    for field_name, field_spec in TIER_2_EXPLORATORY_MANIFEST.items():
        implemented_count = 0
        total_count = len(rulebook_ids)
        
        for rulebook_id in rulebook_ids:
            json_file = qa_dir / f"{rulebook_id}.json"
            
            if json_file.exists():
                try:
                    with open(json_file, 'r') as f:
                        scorecard_data = json.load(f)
                    
                    if field_name in scorecard_data:
                        implemented_count += 1
                        
                        # Validate field value against spec
                        field_value = scorecard_data[field_name]
                        
                        if field_name == 'experimental_risk_score':
                            # Validate type and range for experimental_risk_score
                            if not isinstance(field_value, (int, float)):
                                field_validation_errors.append(f"{rulebook_id}.{field_name}: expected float, got {type(field_value).__name__}")
                            elif not (0.0 <= field_value <= 1.0):
                                field_validation_errors.append(f"{rulebook_id}.{field_name}: value {field_value} outside range [0.0, 1.0]")
                        
                        elif field_name == 'ml_confidence_prediction':
                            # Validate dict structure for ml_confidence_prediction
                            if not isinstance(field_value, dict):
                                field_validation_errors.append(f"{rulebook_id}.{field_name}: expected dict, got {type(field_value).__name__}")
                            else:
                                required_keys = ['predicted_accuracy', 'confidence_interval']
                                for key in required_keys:
                                    if key not in field_value:
                                        field_validation_errors.append(f"{rulebook_id}.{field_name}: missing required key '{key}'")
                                    elif not isinstance(field_value[key], (int, float)):
                                        field_validation_errors.append(f"{rulebook_id}.{field_name}.{key}: expected float, got {type(field_value[key]).__name__}")
                                    elif not (0.0 <= field_value[key] <= 1.0):
                                        field_validation_errors.append(f"{rulebook_id}.{field_name}.{key}: value {field_value[key]} outside range [0.0, 1.0]")
                        
                        elif field_name == 'cross_rulebook_similarity':
                            # Validate dict structure for cross_rulebook_similarity
                            if not isinstance(field_value, dict):
                                field_validation_errors.append(f"{rulebook_id}.{field_name}: expected dict, got {type(field_value).__name__}")
                            else:
                                required_keys = ['most_similar', 'similarity_score', 'similarity_basis']
                                for key in required_keys:
                                    if key not in field_value:
                                        field_validation_errors.append(f"{rulebook_id}.{field_name}: missing required key '{key}'")
                                
                                # Validate most_similar is not self and is valid rulebook_id
                                if 'most_similar' in field_value:
                                    most_similar = field_value['most_similar']
                                    if most_similar == rulebook_id:
                                        field_validation_errors.append(f"{rulebook_id}.{field_name}.most_similar: cannot be self-referential")
                                    elif most_similar != "none" and most_similar not in rulebook_ids:
                                        field_validation_errors.append(f"{rulebook_id}.{field_name}.most_similar: '{most_similar}' not a valid rulebook_id in corpus")
                                
                                # Validate similarity_score range
                                if 'similarity_score' in field_value:
                                    score = field_value['similarity_score']
                                    if not isinstance(score, (int, float)):
                                        field_validation_errors.append(f"{rulebook_id}.{field_name}.similarity_score: expected float, got {type(score).__name__}")
                                    elif not (0.0 <= score <= 1.0):
                                        field_validation_errors.append(f"{rulebook_id}.{field_name}.similarity_score: value {score} outside range [0.0, 1.0]")
                                
                                # Validate similarity_basis matches expected method
                                if 'similarity_basis' in field_value:
                                    basis = field_value['similarity_basis']
                                    if basis != 'cosine(classification_distribution)':
                                        field_validation_errors.append(f"{rulebook_id}.{field_name}.similarity_basis: expected 'cosine(classification_distribution)', got '{basis}'")
                        
                except json.JSONDecodeError:
                    # Already caught in Tier 0
                    pass
        
        field_implementation_status[field_name] = {
            'implemented': implemented_count,
            'total': total_count,
            'spec': field_spec
        }
    
    # Generate concise roadmap summary
    unimplemented_fields = []
    roadmap_summary = []
    
    for field_name, status in field_implementation_status.items():
        impl_count = status['implemented']
        total_count = status['total']
        spec = status['spec']
        
        if impl_count == 0:
            unimplemented_fields.append(field_name)
        
        roadmap_summary.append(
            f"  {field_name}: {impl_count}/{total_count} implemented "
            f"(type: {spec['expected_type']}, range: {spec['expected_range']})"
        )
    
    # Report field validation errors as Tier 2 warnings
    if field_validation_errors:
        error_details = "\n".join([f"    {error}" for error in field_validation_errors])
        _add_tier_2_failure(results, "exploratory_field_validation_errors", 
                           f"TIER 2 EXPLORATORY (VALIDATION): Field validation errors found:\n{error_details}\n"
                           f"These are warnings for exploratory fields and do not block CI.")
    
    # TIER 2 failures are warnings only - do not block CI
    if unimplemented_fields:
        roadmap_details = "\n".join(roadmap_summary)
        _add_tier_2_failure(results, "exploratory_fields_roadmap", 
                           f"TIER 2 EXPLORATORY (ROADMAP): Exploratory fields implementation status:\n{roadmap_details}\n\n"
                           f"Unimplemented: {unimplemented_fields}\n"
                           f"This is expected and does not block CI. Fields will be promoted to Tier 1 when promotion criteria are met.")
    else:
        _add_success(results, "exploratory_fields_implemented", "All exploratory fields implemented", 2)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 3:
        print("Usage: python phase_8_d2_invariants.py <analytics_dir> <qa_dir>")
        sys.exit(1)
    
    analytics_dir = Path(sys.argv[1])
    qa_dir = Path(sys.argv[2])
    
    results = validate_phase_8_d2_scorecards(analytics_dir, qa_dir)
    
    # Enhanced CI signal quality
    print(f"Phase 8 D2 Validation: {'PASSED' if results['passed'] else 'FAILED'}")
    print()
    
    # Report by tier for clarity
    for tier in [0, 1, 2]:
        tier_checks = [c for c in results["checks"] if c.get("tier") == tier]
        if tier_checks:
            tier_name = {0: "FOUNDATIONAL", 1: "ANALYTICAL", 2: "EXPLORATORY"}[tier]
            print(f"=== TIER {tier} ({tier_name}) ===")
            
            for check in tier_checks:
                status = "✅" if check["passed"] else "❌"
                print(f"{status} {check['name']}")
                if not check["passed"]:
                    print(f"    {check['message']}")
            print()
    
    # Summary
    tier_0_failures = len(results["tier_failures"]["tier_0"])
    tier_1_failures = len(results["tier_failures"]["tier_1"])
    tier_2_failures = len(results["tier_failures"]["tier_2"])
    
    print(f"Summary:")
    print(f"  Tier 0 (Foundational): {tier_0_failures} failures")
    print(f"  Tier 1 (Analytical): {tier_1_failures} failures")
    print(f"  Tier 2 (Exploratory): {tier_2_failures} warnings")
    print()
    
    if tier_0_failures > 0:
        print("❌ TIER 0 FAILURES: Foundational invariants violated. These are immutable Phase 8 D1 requirements.")
    if tier_1_failures > 0:
        print("❌ TIER 1 FAILURES: Analytical invariants violated. Phase 8 D2 implementation incomplete.")
    if tier_2_failures > 0:
        print("⚠️  TIER 2 WARNINGS: Exploratory features not implemented. This does not block CI.")
    
    # Exit code: fail only on Tier 0 or Tier 1 failures
    sys.exit(0 if results["passed"] else 1)