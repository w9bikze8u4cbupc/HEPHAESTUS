#!/usr/bin/env python3
"""
G7.1: Reference-based recall evaluation harness for MOBIUS extraction.

Evaluates MOBIUS extraction quality against reference images using:
- Perceptual hashing (pHash/dHash) for primary matching
- ORB feature matching as fallback for difficult cases
"""

import argparse
import json
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Set
import numpy as np

try:
    import cv2
    import imagehash
    from PIL import Image
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Install with: pip install opencv-python pillow imagehash")
    exit(1)

# Try to import scipy for Hungarian algorithm
try:
    from scipy.optimize import linear_sum_assignment
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    print("Warning: scipy not available, using greedy assignment only")


def imread_unicode(path: str) -> Optional[np.ndarray]:
    """
    Unicode-safe image loading for Windows.
    
    OpenCV's imread() fails on Windows paths with non-ASCII characters.
    This helper uses numpy to read the file bytes first, then decodes.
    
    Args:
        path: Path to image file (can contain Unicode characters)
    
    Returns:
        Image as numpy array (BGR format) or None if loading fails
    """
    try:
        data = np.fromfile(str(path), dtype=np.uint8)
        img = cv2.imdecode(data, cv2.IMREAD_COLOR)
        return img
    except Exception as e:
        print(f"Warning: Failed to load image {path}: {e}")
        return None


def classify_tier(image_path: Path) -> str:
    """
    Classify image into ICON/MID/BOARD tier based on dimensions.
    
    Args:
        image_path: Path to image file
    
    Returns:
        Tier classification: "ICON", "MID", or "BOARD"
    """
    img = imread_unicode(str(image_path))
    if img is None:
        return "MID"  # Default fallback
    
    h, w = img.shape[:2]
    area = h * w
    min_dim = min(h, w)
    
    # ICON: small components (icons, tokens, small cards)
    if min_dim < 140 or area < 25000:
        return "ICON"
    
    # BOARD: large components (board sections, large cards)
    if area >= 250000 or min_dim >= 600:
        return "BOARD"
    
    # MID: medium components (standard cards, mid-size elements)
    return "MID"


def compute_fallback_similarity(img1_path: Path, img2_path: Path) -> float:
    """
    Compute ICON-safe fallback similarity for low-texture images.
    
    Uses normalized MAE on 64x64 grayscale thumbnails.
    Works well for flat/low-texture icons where ORB fails.
    
    Args:
        img1_path: Path to first image
        img2_path: Path to second image
    
    Returns:
        Similarity score (0.0-1.0), higher is more similar
    """
    img1 = imread_unicode(str(img1_path))
    img2 = imread_unicode(str(img2_path))
    
    if img1 is None or img2 is None:
        return 0.0
    
    # Convert to grayscale
    gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
    
    # Resize to 64x64 for fast comparison
    thumb1 = cv2.resize(gray1, (64, 64), interpolation=cv2.INTER_AREA)
    thumb2 = cv2.resize(gray2, (64, 64), interpolation=cv2.INTER_AREA)
    
    # Normalize to [0, 1]
    thumb1 = thumb1.astype(np.float32) / 255.0
    thumb2 = thumb2.astype(np.float32) / 255.0
    
    # Compute MAE (mean absolute error)
    mae = np.mean(np.abs(thumb1 - thumb2))
    
    # Convert to similarity (1.0 = identical, 0.0 = completely different)
    similarity = 1.0 - mae
    
    return similarity


def compute_phash(image_path: Path) -> str:
    """Compute perceptual hash (pHash) for an image."""
    img = Image.open(image_path)
    return str(imagehash.phash(img))


def compute_dhash(image_path: Path) -> str:
    """Compute difference hash (dHash) for an image."""
    img = Image.open(image_path)
    return str(imagehash.dhash(img))


def hamming_distance(hash1: str, hash2: str) -> int:
    """Compute Hamming distance between two hashes."""
    return sum(c1 != c2 for c1, c2 in zip(hash1, hash2))


def compute_orb_similarity(img1_path: Path, img2_path: Path) -> float:
    """
    Compute ORB feature-based similarity between two images.
    
    Returns:
        Similarity score (0.0-1.0), higher is more similar
    """
    img1 = imread_unicode(str(img1_path))
    img2 = imread_unicode(str(img2_path))
    
    if img1 is None or img2 is None:
        return 0.0
    
    # Convert to grayscale
    img1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
    img2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
    
    # Initialize ORB detector
    orb = cv2.ORB_create(nfeatures=500)
    
    # Detect keypoints and compute descriptors
    kp1, des1 = orb.detectAndCompute(img1, None)
    kp2, des2 = orb.detectAndCompute(img2, None)
    
    if des1 is None or des2 is None or len(des1) < 10 or len(des2) < 10:
        return 0.0
    
    # Match descriptors using BFMatcher
    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    matches = bf.match(des1, des2)
    
    # Sort matches by distance
    matches = sorted(matches, key=lambda x: x.distance)
    
    # Compute similarity score based on good matches
    good_matches = [m for m in matches if m.distance < 50]
    similarity = len(good_matches) / max(len(kp1), len(kp2))
    
    return min(similarity, 1.0)


def compute_all_candidates(
    reference_path: Path,
    extracted_dir: Path,
    ref_tier: str
) -> List[Dict]:
    """
    Compute all candidate matches for a reference image with tier-aware scoring.
    
    Args:
        reference_path: Path to reference image
        extracted_dir: Directory containing extracted components
        ref_tier: Tier classification of reference (ICON/MID/BOARD)
    
    Returns:
        List of candidates with scores: [{extracted_file, phash_dist, dhash_dist, orb_sim, fallback_sim, combined_score}]
    """
    ref_phash = compute_phash(reference_path)
    ref_dhash = compute_dhash(reference_path)
    
    candidates = []
    
    for extracted_path in extracted_dir.glob("*.png"):
        ext_phash = compute_phash(extracted_path)
        ext_dhash = compute_dhash(extracted_path)
        
        phash_dist = hamming_distance(ref_phash, ext_phash)
        dhash_dist = hamming_distance(ref_dhash, ext_dhash)
        orb_sim = compute_orb_similarity(reference_path, extracted_path)
        
        # Compute fallback similarity for ICON tier or when ORB fails
        fallback_sim = 0.0
        if ref_tier == "ICON" or orb_sim < 0.05:
            fallback_sim = compute_fallback_similarity(reference_path, extracted_path)
        
        # Tier-aware combined scoring
        # Use best hash distance as primary signal
        hash_dist = min(phash_dist, dhash_dist)
        
        # Choose feature similarity: ORB if available, else fallback
        if orb_sim >= 0.05:
            feature_sim = orb_sim
        else:
            feature_sim = fallback_sim
        
        # Combined score: weighted average (lower is better)
        # Hash distance weighted 55%, feature dissimilarity weighted 45%
        combined_score = 0.55 * hash_dist + 0.45 * (1.0 - feature_sim) * 20
        
        candidates.append({
            "extracted_file": extracted_path.name,
            "phash_dist": phash_dist,
            "dhash_dist": dhash_dist,
            "orb_sim": orb_sim,
            "fallback_sim": fallback_sim,
            "combined_score": combined_score
        })
    
    # Sort by combined score (lower is better)
    candidates.sort(key=lambda x: x["combined_score"])
    
    return candidates


def is_acceptable_match(
    candidate: Dict,
    ref_tier: str
) -> bool:
    """
    Check if a candidate meets tier-specific acceptance thresholds.
    
    Args:
        candidate: Candidate dictionary with scores
        ref_tier: Tier classification (ICON/MID/BOARD)
    
    Returns:
        True if candidate meets thresholds for the tier
    """
    # Tier-specific thresholds
    if ref_tier == "ICON":
        phash_thresh = 16
        dhash_thresh = 16
        orb_thresh = 0.08
        fallback_thresh = 0.82
    elif ref_tier == "MID":
        phash_thresh = 12
        dhash_thresh = 12
        orb_thresh = 0.12
        fallback_thresh = 0.85
    else:  # BOARD
        phash_thresh = 10
        dhash_thresh = 10
        orb_thresh = 0.15
        fallback_thresh = 0.88
    
    # Check hash thresholds
    hash_ok = (candidate["phash_dist"] <= phash_thresh or 
               candidate["dhash_dist"] <= dhash_thresh)
    
    # Check feature thresholds (ORB or fallback)
    orb_ok = candidate["orb_sim"] >= orb_thresh
    fallback_ok = candidate["fallback_sim"] >= fallback_thresh
    
    # Accept if hash is good OR feature similarity is good
    return hash_ok or orb_ok or fallback_ok


def hungarian_assignment(
    reference_images: List[Path],
    extracted_dir: Path,
    ref_tiers: Dict[str, str],
    ref_candidates_map: Dict[str, List[Dict]]
) -> Tuple[List[Dict], Set[str], Set[str]]:
    """
    Perform optimal 1:1 assignment using Hungarian algorithm (maximum-weight bipartite matching).
    
    Args:
        reference_images: List of reference image paths
        extracted_dir: Directory containing extracted components
        ref_tiers: Mapping of reference name to tier
        ref_candidates_map: Pre-computed candidates for each reference
    
    Returns:
        (matches, assigned_refs, assigned_extracted)
    """
    if not SCIPY_AVAILABLE:
        raise RuntimeError("scipy required for Hungarian assignment")
    
    # Get all extracted files (deterministic order)
    extracted_files = sorted([p.name for p in extracted_dir.glob("*.png")])
    
    # Build cost matrix (N_refs x N_extracted)
    # Use negative combined_score because linear_sum_assignment minimizes cost
    # Invalid pairs get very high cost (will never be assigned)
    INVALID_COST = 1e9
    
    n_refs = len(reference_images)
    n_extracted = len(extracted_files)
    
    cost_matrix = np.full((n_refs, n_extracted), INVALID_COST, dtype=np.float64)
    
    # Populate cost matrix
    for i, ref_path in enumerate(reference_images):
        ref_name = ref_path.name
        tier = ref_tiers[ref_name]
        candidates = ref_candidates_map[ref_name]
        
        for cand in candidates:
            # Check if this candidate passes tier gates
            if is_acceptable_match(cand, tier):
                # Find index of this extracted file
                try:
                    j = extracted_files.index(cand["extracted_file"])
                    # Use negative score (lower cost = better match)
                    cost_matrix[i, j] = -cand["combined_score"]
                except ValueError:
                    continue
    
    # Run Hungarian algorithm
    row_ind, col_ind = linear_sum_assignment(cost_matrix)
    
    # Extract valid assignments (those that aren't INVALID_COST)
    matches = []
    assigned_refs = set()
    assigned_extracted = set()
    
    for i, j in zip(row_ind, col_ind):
        if cost_matrix[i, j] < INVALID_COST:
            ref_path = reference_images[i]
            ref_name = ref_path.name
            ext_file = extracted_files[j]
            tier = ref_tiers[ref_name]
            
            # Find the candidate details
            candidates = ref_candidates_map[ref_name]
            cand = next((c for c in candidates if c["extracted_file"] == ext_file), None)
            
            if cand:
                # Determine method
                tier_thresholds = {
                    "ICON": (16, 16, 0.08),
                    "MID": (12, 12, 0.12),
                    "BOARD": (10, 10, 0.15)
                }
                phash_t, dhash_t, orb_t = tier_thresholds[tier]
                
                if cand["phash_dist"] <= phash_t and cand["dhash_dist"] <= dhash_t:
                    method = "phash" if cand["phash_dist"] < cand["dhash_dist"] else "dhash"
                    score = min(cand["phash_dist"], cand["dhash_dist"])
                elif cand["phash_dist"] <= phash_t:
                    method = "phash"
                    score = cand["phash_dist"]
                elif cand["dhash_dist"] <= dhash_t:
                    method = "dhash"
                    score = cand["dhash_dist"]
                elif cand["orb_sim"] >= orb_t:
                    method = "orb"
                    score = cand["orb_sim"]
                else:
                    method = "fallback"
                    score = cand["fallback_sim"]
                
                matches.append({
                    "reference": ref_name,
                    "matched": ext_file,
                    "score": float(score),
                    "method": method,
                    "tier": tier
                })
                
                assigned_refs.add(ref_name)
                assigned_extracted.add(ext_file)
    
    return matches, assigned_refs, assigned_extracted


def evaluate_recall(
    reference_dir: Path,
    extracted_dir: Path,
    manifest_path: Path,
    phash_threshold: int = 10,  # Deprecated, kept for CLI compatibility
    dhash_threshold: int = 10,  # Deprecated, kept for CLI compatibility
    orb_threshold: float = 0.15  # Deprecated, kept for CLI compatibility
) -> Dict:
    """
    Evaluate recall against reference images with 1:1 matching and tier-aware thresholds.
    
    Uses greedy assignment to ensure each extracted image matches at most one reference.
    Applies tier-specific thresholds (ICON/MID/BOARD) based on reference image size.
    
    Args:
        reference_dir: Directory containing reference images
        extracted_dir: Directory containing extracted components
        manifest_path: Path to MOBIUS manifest.json
        phash_threshold: Deprecated (tier-specific thresholds used instead)
        dhash_threshold: Deprecated (tier-specific thresholds used instead)
        orb_threshold: Deprecated (tier-specific thresholds used instead)
    
    Returns:
        Evaluation results dictionary
    """
    # Load manifest
    with open(manifest_path, 'r') as f:
        manifest = json.load(f)
    
    # Get reference images and classify by tier
    reference_images = sorted(reference_dir.glob("*.png"))
    total_references = len(reference_images)
    
    ref_tiers = {}
    tier_counts = {"ICON": 0, "MID": 0, "BOARD": 0}
    
    for ref_path in reference_images:
        tier = classify_tier(ref_path)
        ref_tiers[ref_path.name] = tier
        tier_counts[tier] += 1
    
    print(f"\n=== G7.2 Recall Evaluation (1:1 Matching, Tiered Thresholds) ===")
    print(f"Reference images: {total_references}")
    print(f"  ICON: {tier_counts['ICON']} (phash<=16, dhash<=16, ORB>=0.08, fallback>=0.82)")
    print(f"  MID: {tier_counts['MID']} (phash<=12, dhash<=12, ORB>=0.12, fallback>=0.85)")
    print(f"  BOARD: {tier_counts['BOARD']} (phash<=10, dhash<=10, ORB>=0.15, fallback>=0.88)")
    print(f"Extracted components: {manifest['components_extracted']}")
    
    # G10: Ceiling warning
    if manifest['components_extracted'] < total_references:
        max_possible_recall = manifest['components_extracted'] / total_references * 100
        print(f"\n⚠ CANDIDATE POOL SIZE CEILING:")
        print(f"  Extracted pool: {manifest['components_extracted']} components")
        print(f"  Reference set: {total_references} images")
        print(f"  Max possible recall (1:1): {max_possible_recall:.1f}% ({manifest['components_extracted']}/{total_references})")
    
    print()
    
    # Phase 1: Compute all candidates for all references
    print("Computing candidate matches with tier-aware scoring...")
    all_candidates = []
    ref_candidates_map = {}  # For diagnostics
    
    for ref_path in reference_images:
        tier = ref_tiers[ref_path.name]
        candidates = compute_all_candidates(ref_path, extracted_dir, tier)
        ref_candidates_map[ref_path.name] = candidates
        
        # Add acceptable candidates to global pool
        for cand in candidates:
            if is_acceptable_match(cand, tier):
                all_candidates.append({
                    "reference": ref_path.name,
                    "extracted": cand["extracted_file"],
                    "score": cand["combined_score"],
                    "phash_dist": cand["phash_dist"],
                    "dhash_dist": cand["dhash_dist"],
                    "orb_sim": cand["orb_sim"],
                    "fallback_sim": cand["fallback_sim"],
                    "tier": tier
                })
    
    # Phase 2: Greedy 1:1 assignment (best-first)
    print("Performing 1:1 greedy assignment...")
    all_candidates.sort(key=lambda x: x["score"])
    
    assigned_refs = set()
    assigned_extracted = set()
    matches = []
    matches_by_tier = {"ICON": [], "MID": [], "BOARD": []}
    
    for cand in all_candidates:
        ref = cand["reference"]
        ext = cand["extracted"]
        tier = cand["tier"]
        
        if ref not in assigned_refs and ext not in assigned_extracted:
            # Determine method
            tier_thresholds = {
                "ICON": (16, 16, 0.08),
                "MID": (12, 12, 0.12),
                "BOARD": (10, 10, 0.15)
            }
            phash_t, dhash_t, orb_t = tier_thresholds[tier]
            
            if cand["phash_dist"] <= phash_t and cand["dhash_dist"] <= dhash_t:
                method = "phash" if cand["phash_dist"] < cand["dhash_dist"] else "dhash"
                score = min(cand["phash_dist"], cand["dhash_dist"])
            elif cand["phash_dist"] <= phash_t:
                method = "phash"
                score = cand["phash_dist"]
            elif cand["dhash_dist"] <= dhash_t:
                method = "dhash"
                score = cand["dhash_dist"]
            elif cand["orb_sim"] >= orb_t:
                method = "orb"
                score = cand["orb_sim"]
            else:
                method = "fallback"
                score = cand["fallback_sim"]
            
            match_info = {
                "reference": ref,
                "matched": ext,
                "score": float(score),
                "method": method,
                "tier": tier
            }
            
            matches.append(match_info)
            matches_by_tier[tier].append(match_info)
            
            assigned_refs.add(ref)
            assigned_extracted.add(ext)
            
            print(f"  [{tier}] {ref} -> {ext} (score={score:.3f}, method={method})")
    
    # Phase 3: G8 - Hungarian Assignment (Optimal Matching)
    if SCIPY_AVAILABLE:
        print("\n=== G8: Running Hungarian Algorithm (Optimal Assignment) ===")
        hungarian_matches, hungarian_assigned_refs, hungarian_assigned_extracted = hungarian_assignment(
            reference_images,
            extracted_dir,
            ref_tiers,
            ref_candidates_map
        )
        
        # Compare greedy vs Hungarian
        greedy_count = len(matches)
        hungarian_count = len(hungarian_matches)
        delta = hungarian_count - greedy_count
        
        print(f"\nAssignment Comparison:")
        print(f"  Greedy:    {greedy_count}/{total_references} matches")
        print(f"  Hungarian: {hungarian_count}/{total_references} matches")
        print(f"  Delta:     {delta:+d} matches")
        
        if delta > 0:
            print(f"\n✓ Hungarian improved recall by {delta} match(es)")
            print("  Using Hungarian assignment as final result")
            # Use Hungarian results
            matches = hungarian_matches
            assigned_refs = hungarian_assigned_refs
            assigned_extracted = hungarian_assigned_extracted
            
            # Rebuild matches_by_tier
            matches_by_tier = {"ICON": [], "MID": [], "BOARD": []}
            for match in matches:
                matches_by_tier[match["tier"]].append(match)
        elif delta == 0:
            print("\n= Hungarian produced same result as greedy")
            print("  G8 HARD STOP: No improvement gained")
        else:
            print(f"\n! Warning: Hungarian produced fewer matches ({delta})")
            print("  Keeping greedy assignment")
    else:
        print("\nWarning: scipy not available, skipping Hungarian assignment")
    
    # Phase 4: Identify unmatched references by tier
    unmatched = [ref.name for ref in reference_images if ref.name not in assigned_refs]
    unmatched_by_tier = {"ICON": [], "MID": [], "BOARD": []}
    
    for ref_name in unmatched:
        tier = ref_tiers[ref_name]
        unmatched_by_tier[tier].append(ref_name)
    
    # Phase 5: Generate diagnostics for unmatched references
    print("\nGenerating diagnostics for unmatched references...")
    unmatched_diagnostics = []
    
    for ref_name in unmatched:
        tier = ref_tiers[ref_name]
        candidates = ref_candidates_map[ref_name][:5]  # Top 5
        
        print(f"\n[{tier}] {ref_name} - Top 5 candidates:")
        diag = {
            "reference": ref_name,
            "tier": tier,
            "top_candidates": []
        }
        
        for i, cand in enumerate(candidates, 1):
            print(f"  {i}. {cand['extracted_file']}")
            print(f"     phash={cand['phash_dist']}, dhash={cand['dhash_dist']}, orb={cand['orb_sim']:.3f}, fallback={cand['fallback_sim']:.3f}, combined={cand['combined_score']:.3f}")
            
            diag["top_candidates"].append({
                "rank": i,
                "extracted_file": cand["extracted_file"],
                "phash_dist": cand["phash_dist"],
                "dhash_dist": cand["dhash_dist"],
                "orb_sim": cand["orb_sim"],
                "fallback_sim": cand["fallback_sim"],
                "combined_score": cand["combined_score"],
                "already_assigned": cand["extracted_file"] in assigned_extracted
            })
        
        unmatched_diagnostics.append(diag)
    
    # Compute metrics
    recall = len(matches) / total_references if total_references > 0 else 0.0
    recall_pct = recall * 100
    
    # Check for false positives (components not matched to any reference)
    all_extracted = {p.name for p in extracted_dir.glob("*.png")}
    false_positives = all_extracted - assigned_extracted
    
    results = {
        "total_references": total_references,
        "total_extracted": manifest['components_extracted'],
        "matches": len(matches),
        "unmatched": len(unmatched),
        "recall": recall,
        "recall_pct": recall_pct,
        "false_positives": len(false_positives),
        "tier_counts": tier_counts,
        "matches_by_tier": {
            "ICON": len(matches_by_tier["ICON"]),
            "MID": len(matches_by_tier["MID"]),
            "BOARD": len(matches_by_tier["BOARD"])
        },
        "unmatched_by_tier": {
            "ICON": len(unmatched_by_tier["ICON"]),
            "MID": len(unmatched_by_tier["MID"]),
            "BOARD": len(unmatched_by_tier["BOARD"])
        },
        "matched_details": matches,
        "unmatched_references": unmatched,
        "unmatched_by_tier_list": unmatched_by_tier,
        "unmatched_diagnostics": unmatched_diagnostics,
        "false_positive_files": sorted(false_positives),
        "acceptance_criteria": {
            "recall_target": 0.90,
            "recall_achieved": recall >= 0.90,
            "false_positive_target": 2,
            "false_positive_achieved": len(false_positives) <= 2
        }
    }
    
    return results


def print_summary(results: Dict):
    """Print evaluation summary."""
    print("\n" + "="*60)
    print("EVALUATION SUMMARY")
    print("="*60)
    print(f"Total reference images: {results['total_references']}")
    print(f"  ICON: {results['tier_counts']['ICON']}")
    print(f"  MID: {results['tier_counts']['MID']}")
    print(f"  BOARD: {results['tier_counts']['BOARD']}")
    print(f"Total extracted components: {results['total_extracted']}")
    print()
    print(f"Matches found: {results['matches']}")
    print(f"  ICON: {results['matches_by_tier']['ICON']}/{results['tier_counts']['ICON']}")
    print(f"  MID: {results['matches_by_tier']['MID']}/{results['tier_counts']['MID']}")
    print(f"  BOARD: {results['matches_by_tier']['BOARD']}/{results['tier_counts']['BOARD']}")
    print()
    print(f"Unmatched references: {results['unmatched']}")
    print(f"  ICON: {results['unmatched_by_tier']['ICON']}")
    print(f"  MID: {results['unmatched_by_tier']['MID']}")
    print(f"  BOARD: {results['unmatched_by_tier']['BOARD']}")
    print()
    print(f"False positives: {results['false_positives']}")
    print()
    print(f"Recall: {results['recall_pct']:.1f}% ({results['matches']}/{results['total_references']})")
    print()
    
    # Acceptance criteria
    acc = results['acceptance_criteria']
    print("ACCEPTANCE CRITERIA (G7.5):")
    recall_status = "[PASS]" if acc['recall_achieved'] else "[FAIL]"
    fp_status = "[PASS]" if acc['false_positive_achieved'] else "[FAIL]"
    print(f"  Recall >=90%: {recall_status} ({results['recall_pct']:.1f}%)")
    print(f"  False positives <=2: {fp_status} ({results['false_positives']})")
    print()
    
    overall = acc['recall_achieved'] and acc['false_positive_achieved']
    if overall:
        print("[OVERALL: PASS]")
    else:
        print("[OVERALL: FAIL]")
    
    if results['unmatched']:
        print("\nUnmatched references by tier:")
        for tier in ["ICON", "MID", "BOARD"]:
            tier_unmatched = results['unmatched_by_tier_list'][tier]
            if tier_unmatched:
                print(f"  {tier}:")
                for ref in tier_unmatched:
                    print(f"    - {ref}")
    
    if results['false_positive_files']:
        print("\nFalse positive components:")
        for fp in results['false_positive_files'][:10]:  # Show first 10
            print(f"  - {fp}")
        if len(results['false_positive_files']) > 10:
            print(f"  ... and {len(results['false_positive_files']) - 10} more")


def main():
    parser = argparse.ArgumentParser(description="G7.1 MOBIUS Recall Evaluation")
    parser.add_argument("--reference-dir", type=Path, required=True,
                        help="Directory containing reference images")
    parser.add_argument("--extracted-dir", type=Path, required=True,
                        help="Directory containing extracted components")
    parser.add_argument("--manifest", type=Path, required=True,
                        help="Path to MOBIUS manifest.json")
    parser.add_argument("--output", type=Path,
                        help="Output JSON file for results")
    parser.add_argument("--phash-threshold", type=int, default=10,
                        help="pHash Hamming distance threshold (default: 10)")
    parser.add_argument("--dhash-threshold", type=int, default=10,
                        help="dHash Hamming distance threshold (default: 10)")
    parser.add_argument("--orb-threshold", type=float, default=0.15,
                        help="ORB similarity threshold (default: 0.15)")
    parser.add_argument("--generate-miss-packet", type=Path,
                        help="G9: Generate miss packet to specified directory")
    parser.add_argument("--audit-misses", action="store_true",
                        help="G9: Run tier audit on unmatched references")
    
    args = parser.parse_args()
    
    # Validate paths
    if not args.reference_dir.exists():
        print(f"Error: Reference directory not found: {args.reference_dir}")
        exit(1)
    if not args.extracted_dir.exists():
        print(f"Error: Extracted directory not found: {args.extracted_dir}")
        exit(1)
    if not args.manifest.exists():
        print(f"Error: Manifest not found: {args.manifest}")
        exit(1)
    
    # Run evaluation
    results = evaluate_recall(
        args.reference_dir,
        args.extracted_dir,
        args.manifest,
        args.phash_threshold,
        args.dhash_threshold,
        args.orb_threshold
    )
    
    # Print summary
    print_summary(results)
    
    # Save results
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to: {args.output}")
    
    # G9: Generate miss packet if requested
    if args.generate_miss_packet and results['unmatched'] > 0:
        print(f"\n{'='*60}")
        print("G9: Generating miss packet...")
        print(f"{'='*60}")
        
        from scripts.generate_miss_packet import generate_miss_packet
        generate_miss_packet(
            args.output if args.output else Path("temp_results.json"),
            args.reference_dir,
            args.extracted_dir,
            args.manifest,
            args.generate_miss_packet
        )
    
    # G9: Run audit if requested
    if args.audit_misses and results['unmatched'] > 0:
        print(f"\n{'='*60}")
        print("G9: Running tier audit on misses...")
        print(f"{'='*60}")
        
        # Note: Audit requires miss packet to exist
        print("Note: Run with --generate-miss-packet first to create audit inputs")


if __name__ == "__main__":
    main()
