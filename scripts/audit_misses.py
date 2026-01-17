#!/usr/bin/env python3
"""
G9.2: Audit missed references against all tier thresholds.

Tests each miss under ICON/MID/BOARD thresholds to determine
if the issue is tier labeling vs true extraction gap.
"""
import json
from pathlib import Path
from typing import Dict, List

def audit_miss_against_tiers(miss_data: Dict) -> Dict:
    """
    Test a missed reference against all tier thresholds.
    
    Returns audit results showing which tiers would match.
    """
    ref_name = miss_data['reference']
    current_tier = miss_data['tier']
    top_candidate = miss_data['top_candidates'][0] if miss_data['top_candidates'] else None
    
    if not top_candidate:
        return {
            "reference": ref_name,
            "current_tier": current_tier,
            "audit_result": "NO_CANDIDATES",
            "tier_matches": {}
        }
    
    # Define all tier thresholds
    all_tiers = {
        "ICON": {"phash": 16, "dhash": 16, "orb": 0.08, "fallback": 0.82},
        "MID": {"phash": 12, "dhash": 12, "orb": 0.12, "fallback": 0.85},
        "BOARD": {"phash": 10, "dhash": 10, "orb": 0.15, "fallback": 0.88}
    }
    
    # Test against each tier
    tier_results = {}
    
    for tier_name, thresholds in all_tiers.items():
        # Check if top candidate passes this tier's gates
        phash_ok = top_candidate['phash_dist'] <= thresholds['phash']
        dhash_ok = top_candidate['dhash_dist'] <= thresholds['dhash']
        orb_ok = top_candidate['orb_sim'] >= thresholds['orb']
        fallback_ok = top_candidate['fallback_sim'] >= thresholds['fallback']
        
        hash_ok = phash_ok or dhash_ok
        feature_ok = orb_ok or fallback_ok
        
        passes = hash_ok or feature_ok
        
        # Determine which criteria passed
        passed_criteria = []
        if phash_ok:
            passed_criteria.append(f"phash={top_candidate['phash_dist']}<={thresholds['phash']}")
        if dhash_ok:
            passed_criteria.append(f"dhash={top_candidate['dhash_dist']}<={thresholds['dhash']}")
        if orb_ok:
            passed_criteria.append(f"orb={top_candidate['orb_sim']:.3f}>={thresholds['orb']}")
        if fallback_ok:
            passed_criteria.append(f"fallback={top_candidate['fallback_sim']:.3f}>={thresholds['fallback']}")
        
        tier_results[tier_name] = {
            "passes": passes,
            "is_current_tier": tier_name == current_tier,
            "passed_criteria": passed_criteria,
            "checks": {
                "phash": {"value": top_candidate['phash_dist'], "threshold": thresholds['phash'], "passes": phash_ok},
                "dhash": {"value": top_candidate['dhash_dist'], "threshold": thresholds['dhash'], "passes": dhash_ok},
                "orb": {"value": top_candidate['orb_sim'], "threshold": thresholds['orb'], "passes": orb_ok},
                "fallback": {"value": top_candidate['fallback_sim'], "threshold": thresholds['fallback'], "passes": fallback_ok}
            }
        }
    
    # Determine audit classification
    passing_tiers = [t for t, r in tier_results.items() if r['passes']]
    
    if not passing_tiers:
        classification = "RULE_B_NO_TIER_MATCHES"
        recommendation = "True extraction gap or not present in PDF"
    elif current_tier in passing_tiers:
        classification = "UNEXPECTED_CURRENT_TIER_SHOULD_MATCH"
        recommendation = "Investigation needed - current tier should have matched"
    elif passing_tiers:
        classification = "RULE_A_WRONG_TIER"
        recommendation = f"Reference should be tier {passing_tiers[0]} not {current_tier}"
    else:
        classification = "RULE_C_THRESHOLD_MISMATCH"
        recommendation = "Would require threshold loosening (rejected)"
    
    return {
        "reference": ref_name,
        "current_tier": current_tier,
        "top_candidate": top_candidate['file'],
        "already_assigned": top_candidate['already_assigned'],
        "classification": classification,
        "recommendation": recommendation,
        "passing_tiers": passing_tiers,
        "tier_results": tier_results
    }


def main():
    # Load miss packet
    miss_packet_path = Path("test_output/g9_miss_packet/miss_packet.json")
    
    with open(miss_packet_path) as f:
        miss_packet = json.load(f)
    
    print("="*60)
    print("G9.2: TIER AUDIT FOR MISSED REFERENCES")
    print("="*60)
    print(f"Total misses to audit: {len(miss_packet['misses'])}\n")
    
    audit_results = []
    
    for miss in miss_packet['misses']:
        audit = audit_miss_against_tiers(miss)
        audit_results.append(audit)
        
        print(f"\n{'='*60}")
        print(f"Reference: {audit['reference']}")
        print(f"Current Tier: {audit['current_tier']}")
        print(f"Top Candidate: {audit['top_candidate']}")
        print(f"Already Assigned: {audit['already_assigned']}")
        print(f"\nClassification: {audit['classification']}")
        print(f"Recommendation: {audit['recommendation']}")
        print(f"\nTier Test Results:")
        
        for tier_name, result in audit['tier_results'].items():
            status = "[PASS]" if result['passes'] else "[FAIL]"
            current = " (CURRENT)" if result['is_current_tier'] else ""
            print(f"  {tier_name:6s}{current}: {status}")
            if result['passed_criteria']:
                for criterion in result['passed_criteria']:
                    print(f"    ✓ {criterion}")
            else:
                # Show why it failed
                checks = result['checks']
                print(f"    phash={checks['phash']['value']} vs {checks['phash']['threshold']}")
                print(f"    dhash={checks['dhash']['value']} vs {checks['dhash']['threshold']}")
                print(f"    orb={checks['orb']['value']:.3f} vs {checks['orb']['threshold']}")
                print(f"    fallback={checks['fallback']['value']:.3f} vs {checks['fallback']['threshold']}")
    
    # Save audit results
    audit_output_path = Path("test_output/g9_miss_packet/audit_results.json")
    with open(audit_output_path, 'w') as f:
        json.dump({
            "audit_date": "2026-01-17",
            "total_audited": len(audit_results),
            "results": audit_results
        }, f, indent=2)
    
    print(f"\n{'='*60}")
    print(f"✓ Audit complete")
    print(f"  Results saved to: {audit_output_path}")
    print(f"{'='*60}")
    
    # Summary
    print(f"\nSUMMARY:")
    classifications = {}
    for audit in audit_results:
        cls = audit['classification']
        classifications[cls] = classifications.get(cls, 0) + 1
    
    for cls, count in sorted(classifications.items()):
        print(f"  {cls}: {count}")


if __name__ == "__main__":
    main()
