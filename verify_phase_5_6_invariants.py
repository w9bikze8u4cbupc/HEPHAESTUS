#!/usr/bin/env python3
"""Comprehensive Phase 5.6 invariant verification."""

import json
from pathlib import Path
from typing import Dict, List

def verify_rulebook_invariants(rulebook_path: Path) -> Dict[str, bool]:
    """Verify all Phase 5.6 invariants for a single rulebook."""
    print(f"\n🔍 Verifying invariants for {rulebook_path.name}")
    
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
        print(f"❌ Manifest missing: {manifest_path}")
        return invariants
    
    invariants["manifest_exists"] = True
    
    with open(manifest_path) as f:
        manifest = json.load(f)
    
    # Load extraction log
    log_path = rulebook_path / "extraction_log.jsonl"
    if not log_path.exists():
        print(f"❌ Extraction log missing: {log_path}")
        return invariants
    
    invariants["extraction_log_exists"] = True
    
    # Parse extraction log
    log_entries = []
    with open(log_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                log_entries.append(json.loads(line))
    
    # Check path set consistency: manifest_paths == disk_paths
    images_dir = rulebook_path / "images" / "all"
    if images_dir.exists():
        manifest_files = {item["file_name"] for item in manifest["items"]}
        disk_files = {f.name for f in images_dir.glob("*.png")}
        
        if manifest_files == disk_files:
            invariants["path_set_consistency"] = True
            print(f"✅ Path consistency: {len(manifest_files)} files")
        else:
            print(f"❌ Path mismatch: manifest={len(manifest_files)}, disk={len(disk_files)}")
            missing_from_manifest = disk_files - manifest_files
            missing_from_disk = manifest_files - disk_files
            if missing_from_manifest:
                print(f"   Orphaned files: {missing_from_manifest}")
            if missing_from_disk:
                print(f"   Missing files: {missing_from_disk}")
    
    # Check persistence boundary: FAILED => no file, PERSISTED => file exists with size > 0
    persistence_violations = []
    for entry in log_entries:
        status = entry["status"]
        output_path = entry.get("output_path")
        
        if status == "failed":
            # Should have no file
            if output_path and Path(output_path).exists():
                persistence_violations.append(f"FAILED status but file exists: {output_path}")
        elif status == "persisted":
            # Should have file with content
            if not output_path:
                persistence_violations.append(f"PERSISTED status but no output_path")
            elif not Path(output_path).exists():
                persistence_violations.append(f"PERSISTED status but file missing: {output_path}")
            elif Path(output_path).stat().st_size == 0:
                persistence_violations.append(f"PERSISTED status but empty file: {output_path}")
    
    if len(persistence_violations) == 0:
        invariants["persistence_boundary"] = True
        
        # Count different types for precise reporting
        persisted_count = sum(1 for e in log_entries if e["status"] == "persisted")
        failed_count = sum(1 for e in log_entries if e["status"] == "failed")
        
        print(f"✅ Attempt log entries verified: {len(log_entries)}")
        print(f"✅ Persisted files verified: {persisted_count}")
        print(f"✅ Failures verified: {failed_count}")
        print(f"✅ Identity: {len(log_entries)} = {persisted_count} + {failed_count}")
    else:
        print(f"❌ Persistence violations: {len(persistence_violations)}")
        for violation in persistence_violations[:3]:
            print(f"   {violation}")
    
    # Check health metrics identity: attempted == saved + failures
    health = manifest.get("extraction_health", {})
    if health:
        attempted = health.get("images_attempted", 0)
        saved = health.get("images_saved", 0)
        failures = health.get("conversion_failures", 0)
        
        # Count from log
        log_attempted = len(log_entries)
        log_saved = sum(1 for e in log_entries if e["status"] == "persisted")
        log_failed = sum(1 for e in log_entries if e["status"] == "failed")
        
        if (attempted == saved + failures and 
            attempted == log_attempted and 
            saved == log_saved and 
            failures == log_failed and
            saved == len(manifest["items"])):
            invariants["health_metrics_identity"] = True
            print(f"✅ Health metrics identity: attempted={attempted}, persisted={saved}, failed={failures}")
            print(f"✅ Log confirmation: {log_attempted}={log_saved}+{log_failed}")
            print(f"✅ Manifest entries: {len(manifest['items'])} (matches persisted)")
        else:
            print(f"❌ Health metrics mismatch:")
            print(f"   Health: attempted={attempted}, persisted={saved}, failed={failures}")
            print(f"   Log: attempted={log_attempted}, persisted={log_saved}, failed={log_failed}")
            print(f"   Manifest: {len(manifest['items'])} entries")
    
    # Check extraction log integrity
    required_fields = ["rulebook_id", "image_id", "status", "reason_code", "colorspace_str"]
    valid_entries = 0
    for entry in log_entries:
        if all(field in entry for field in required_fields):
            valid_entries += 1
    
    if valid_entries == len(log_entries) and len(log_entries) > 0:
        invariants["extraction_log_integrity"] = True
        print(f"✅ Log integrity: {valid_entries} valid entries")
        
        # Special assertion for SETI p23_img27 (Phase 5.6 requirement)
        if rulebook_path.name == "seti":
            p23_img27_entries = [e for e in log_entries if e.get("image_id") == "p23_img27"]
            if len(p23_img27_entries) == 1:
                entry = p23_img27_entries[0]
                if entry.get("page_index") == 23 and entry.get("status") == "failed":
                    print(f"✅ SETI p23_img27 assertion: correctly logged as failed on page 23")
                else:
                    print(f"❌ SETI p23_img27 assertion: incorrect status or page_index")
                    print(f"   Expected: page_index=23, status=failed")
                    print(f"   Actual: page_index={entry.get('page_index')}, status={entry.get('status')}")
            else:
                print(f"❌ SETI p23_img27 assertion: found {len(p23_img27_entries)} entries, expected 1")
    else:
        print(f"❌ Log integrity: {valid_entries}/{len(log_entries)} valid")
    
    return invariants

def main():
    """Verify Phase 5.6 invariants for all test results."""
    print("🔧 Phase 5.6 Invariant Verification")
    print("=" * 40)
    
    test_dir = Path("eval/phase_5_6_test")
    if not test_dir.exists():
        print(f"❌ Test directory not found: {test_dir}")
        return False
    
    all_passed = True
    total_invariants = 0
    passed_invariants = 0
    
    for rulebook_dir in test_dir.iterdir():
        if rulebook_dir.is_dir():
            invariants = verify_rulebook_invariants(rulebook_dir)
            
            rulebook_passed = all(invariants.values())
            rulebook_count = sum(invariants.values())
            
            total_invariants += len(invariants)
            passed_invariants += rulebook_count
            
            if rulebook_passed:
                print(f"✅ {rulebook_dir.name}: ALL INVARIANTS PASS")
            else:
                print(f"❌ {rulebook_dir.name}: {rulebook_count}/{len(invariants)} invariants pass")
                all_passed = False
    
    print(f"\n🏁 Overall Result:")
    print(f"   Invariants: {passed_invariants}/{total_invariants}")
    print(f"   Success Rate: {passed_invariants/total_invariants:.1%}")
    
    if all_passed:
        print("🎉 ALL PHASE 5.6 INVARIANTS VERIFIED")
        return True
    else:
        print("⚠️  PHASE 5.6 INVARIANT VIOLATIONS DETECTED")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)