"""
Phase 8 Invariants: QA Scorecard Generation

Validates that QA scorecards are generated correctly from Phase 7 analytics.
"""

import json
from pathlib import Path
from typing import Dict, Any


def validate_phase_8_scorecards(analytics_dir: Path, qa_dir: Path) -> Dict[str, Any]:
    """Validate Phase 8 QA scorecard generation."""
    
    results = {
        "phase": "8",
        "validation_type": "qa_scorecards",
        "checks": [],
        "passed": True,
        "summary": {}
    }
    
    # Load corpus analytics
    analytics_file = analytics_dir / "corpus_analytics.json"
    if not analytics_file.exists():
        results["checks"].append({
            "name": "corpus_analytics_exists",
            "passed": False,
            "message": f"corpus_analytics.json not found in {analytics_dir}"
        })
        results["passed"] = False
        return results
    
    with open(analytics_file, 'r') as f:
        corpus_data = json.load(f)
    
    rulebooks = corpus_data['rulebook_analytics']
    rulebook_ids = [rb['identity']['rulebook_id'] for rb in rulebooks]
    
    results["summary"]["expected_rulebooks"] = len(rulebook_ids)
    
    # Check QA directory structure
    qa_rulebooks_dir = qa_dir / "rulebooks"
    if not qa_rulebooks_dir.exists():
        results["checks"].append({
            "name": "qa_directory_structure",
            "passed": False,
            "message": f"qa/rulebooks directory not found"
        })
        results["passed"] = False
        return results
    
    # Check each rulebook has both JSON and MD files
    missing_files = []
    invalid_json = []
    missing_required_fields = []
    
    for rulebook_id in rulebook_ids:
        json_file = qa_rulebooks_dir / f"{rulebook_id}.json"
        md_file = qa_rulebooks_dir / f"{rulebook_id}.md"
        
        # Check JSON file exists and is valid
        if not json_file.exists():
            missing_files.append(f"{rulebook_id}.json")
        else:
            try:
                with open(json_file, 'r') as f:
                    scorecard_data = json.load(f)
                
                # Check required fields
                required_fields = ['rulebook_id', 'source_pdf', 'total_images', 
                                 'success_rate', 'failure_rate', 'analytics_source']
                for field in required_fields:
                    if field not in scorecard_data:
                        missing_required_fields.append(f"{rulebook_id}.json missing {field}")
                
            except json.JSONDecodeError:
                invalid_json.append(f"{rulebook_id}.json")
        
        # Check MD file exists
        if not md_file.exists():
            missing_files.append(f"{rulebook_id}.md")
        else:
            # Check MD has required sections
            with open(md_file, 'r', encoding='utf-8') as f:
                md_content = f.read()
            
            required_sections = ["# QA Scorecard:", "## Summary Metrics", "## Evidence Anchors"]
            for section in required_sections:
                if section not in md_content:
                    missing_required_fields.append(f"{rulebook_id}.md missing section: {section}")
    
    # Record results
    results["checks"].extend([
        {
            "name": "all_scorecard_files_exist",
            "passed": len(missing_files) == 0,
            "message": f"Missing files: {missing_files}" if missing_files else "All scorecard files exist"
        },
        {
            "name": "all_json_valid",
            "passed": len(invalid_json) == 0,
            "message": f"Invalid JSON files: {invalid_json}" if invalid_json else "All JSON files valid"
        },
        {
            "name": "all_required_fields_present",
            "passed": len(missing_required_fields) == 0,
            "message": f"Missing required fields: {missing_required_fields}" if missing_required_fields else "All required fields present"
        }
    ])
    
    results["summary"]["generated_files"] = len([f for f in qa_rulebooks_dir.iterdir() if f.is_file()])
    results["summary"]["expected_files"] = len(rulebook_ids) * 2  # JSON + MD for each
    
    # Overall pass/fail
    results["passed"] = all(check["passed"] for check in results["checks"])
    
    return results


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 3:
        print("Usage: python phase_8_invariants.py <analytics_dir> <qa_dir>")
        sys.exit(1)
    
    analytics_dir = Path(sys.argv[1])
    qa_dir = Path(sys.argv[2])
    
    results = validate_phase_8_scorecards(analytics_dir, qa_dir)
    
    print(f"Phase 8 Validation: {'PASSED' if results['passed'] else 'FAILED'}")
    for check in results["checks"]:
        status = "✅" if check["passed"] else "❌"
        print(f"{status} {check['name']}: {check['message']}")
    
    print(f"\nSummary: {results['summary']['generated_files']}/{results['summary']['expected_files']} files generated")
    
    sys.exit(0 if results["passed"] else 1)
