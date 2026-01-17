#!/usr/bin/env python3
"""
G9.1: Generate miss packet for unmatched references.

Creates evidence folder with:
- Reference images
- Top 5 candidate images
- Detailed metrics JSON
"""
import json
import shutil
from pathlib import Path
from typing import Dict, List

def generate_miss_packet(
    eval_results_path: Path,
    reference_dir: Path,
    extracted_dir: Path,
    manifest_path: Path,
    output_dir: Path
):
    """Generate miss packet for director adjudication."""
    
    # Load evaluation results
    with open(eval_results_path) as f:
        results = json.load(f)
    
    # Load extraction manifest for bbox/DPI data
    with open(manifest_path) as f:
        manifest = json.load(f)
    
    # Create manifest lookup by filename
    manifest_lookup = {item['file_name']: item for item in manifest['items']}
    
    # Create output structure
    output_dir.mkdir(parents=True, exist_ok=True)
    
    miss_packet = {
        "generated_at": "2026-01-17",
        "evaluation_source": str(eval_results_path),
        "total_misses": results['unmatched'],
        "misses": []
    }
    
    # Process each unmatched reference
    for diag in results['unmatched_diagnostics']:
        ref_name = diag['reference']
        tier = diag['tier']
        
        print(f"\nProcessing miss: {ref_name} (tier={tier})")
        
        # Create subfolder for this miss
        miss_dir = output_dir / ref_name.replace('.png', '')
        miss_dir.mkdir(exist_ok=True)
        
        # Copy reference image
        ref_src = reference_dir / ref_name
        ref_dst = miss_dir / f"reference_{ref_name}"
        shutil.copy2(ref_src, ref_dst)
        print(f"  Copied reference: {ref_dst.name}")
        
        # Copy top 5 candidates
        candidates_info = []
        for i, cand in enumerate(diag['top_candidates'][:5], 1):
            cand_file = cand['extracted_file']
            cand_src = extracted_dir / cand_file
            cand_dst = miss_dir / f"candidate_{i:02d}_{cand_file}"
            
            if cand_src.exists():
                shutil.copy2(cand_src, cand_dst)
                print(f"  Copied candidate {i}: {cand_dst.name}")
            
            # Get manifest data for this candidate
            manifest_data = manifest_lookup.get(cand_file, {})
            
            candidates_info.append({
                "rank": i,
                "file": cand_file,
                "phash_dist": cand['phash_dist'],
                "dhash_dist": cand['dhash_dist'],
                "orb_sim": cand['orb_sim'],
                "fallback_sim": cand['fallback_sim'],
                "combined_score": cand['combined_score'],
                "already_assigned": cand['already_assigned'],
                "manifest_data": {
                    "bbox_width_in": manifest_data.get('bbox_width_in'),
                    "bbox_height_in": manifest_data.get('bbox_height_in'),
                    "render_dpi_used": manifest_data.get('render_dpi_used'),
                    "size_tier": manifest_data.get('size_tier'),
                    "page_index": manifest_data.get('page_index')
                }
            })
        
        # Tier thresholds
        tier_thresholds = {
            "ICON": {"phash": 16, "dhash": 16, "orb": 0.08, "fallback": 0.82},
            "MID": {"phash": 12, "dhash": 12, "orb": 0.12, "fallback": 0.85},
            "BOARD": {"phash": 10, "dhash": 10, "orb": 0.15, "fallback": 0.88}
        }
        
        miss_info = {
            "reference": ref_name,
            "tier": tier,
            "thresholds": tier_thresholds[tier],
            "top_candidates": candidates_info
        }
        
        # Save JSON for this miss
        miss_json_path = miss_dir / "metrics.json"
        with open(miss_json_path, 'w') as f:
            json.dump(miss_info, f, indent=2)
        print(f"  Saved metrics: {miss_json_path.name}")
        
        miss_packet["misses"].append(miss_info)
    
    # Save master miss packet JSON
    packet_json_path = output_dir / "miss_packet.json"
    with open(packet_json_path, 'w') as f:
        json.dump(miss_packet, f, indent=2)
    
    print(f"\n{'='*60}")
    print(f"✓ Miss packet generated: {output_dir}")
    print(f"  Total misses: {len(miss_packet['misses'])}")
    print(f"  Master JSON: {packet_json_path.name}")
    print(f"{'='*60}")
    
    return miss_packet


if __name__ == "__main__":
    # Paths
    eval_results = Path("test_output/g8_hungarian_eval.json")
    reference_dir = Path("acceptance_test/terraforming_mars_reference")
    extracted_dir = Path("test_output/g7_tuned/MOBIUS_READY/images")
    manifest_path = Path("test_output/g7_tuned/MOBIUS_READY/manifest.json")
    output_dir = Path("test_output/g9_miss_packet")
    
    # Generate packet
    generate_miss_packet(
        eval_results,
        reference_dir,
        extracted_dir,
        manifest_path,
        output_dir
    )
