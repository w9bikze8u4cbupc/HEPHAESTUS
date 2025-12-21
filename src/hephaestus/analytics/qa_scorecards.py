# Simple dict-based scorecard generator
import sys
sys.path.append('src')
import json
from pathlib import Path
import argparse


def write_json_deterministic(path, payload):
    """Write JSON with deterministic formatting for Phase 8 D2 compliance."""
    def normalize_floats(obj):
        if isinstance(obj, float):
            return round(obj, 6)
        elif isinstance(obj, dict):
            return {k: normalize_floats(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [normalize_floats(item) for item in obj]
        else:
            return obj
    
    normalized_data = normalize_floats(payload)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(normalized_data, f,
                 sort_keys=True,
                 indent=2,
                 ensure_ascii=False,
                 allow_nan=False)
        f.write('\n')

def generate_scorecards(analytics_file, out_dir, schema_version="8.1", verbose=False):
    # Load data as dict
    with open(analytics_file, 'r') as f:
        data = json.load(f)
    
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    rulebooks_dir = out_path / "rulebooks"
    rulebooks_dir.mkdir(exist_ok=True)
    
    files_created = []
    
    for rb in data['rulebook_analytics']:
        rulebook_id = rb['identity']['rulebook_id']
        
        # Create simple scorecard
        scorecard = {
            'rulebook_id': rulebook_id,
            'source_pdf': rb['identity']['source_pdf_path'],
            'total_images': rb['extraction_outcome']['images_attempted'],
            'success_rate': rb['extraction_outcome']['success_rate'],
            'failure_rate': rb['extraction_outcome']['failure_rate'],
            'analytics_source': f"corpus_analytics.json -> rulebook_analytics[{rulebook_id}]",
            'schema_version': schema_version
        }

        # Add Phase 8 D2 fields for schema 8.2
        if schema_version == "8.2":
            # Real computation: coverage_density from text coverage and extraction success
            text_coverage = rb.get('pdf_characteristics', {}).get('text_coverage_ratio', 0.0)
            extraction_success = scorecard['success_rate']
            scorecard['coverage_density'] = min(1.0, (text_coverage + extraction_success) / 2.0)
            
            # Real computation: classification_confidence_distribution from actual classification data
            classification = rb.get('classification_outcome', {})
            total_components = classification.get('total_components', 0)
            unknown_count = classification.get('unknown_classification_count', 0)
            
            if total_components > 0:
                known_ratio = (total_components - unknown_count) / total_components
                unknown_ratio = unknown_count / total_components
            else:
                known_ratio = 1.0
                unknown_ratio = 0.0
                
            scorecard['classification_confidence_distribution'] = {
                'known_ratio': round(known_ratio, 6),
                'unknown_ratio': round(unknown_ratio, 6)
            }
            
            # Real computation: component_type_entropy from classification distribution
            classification_dist = classification.get('classification_distribution', {})
            if total_components > 0 and classification_dist:
                # Shannon entropy calculation
                import math
                entropy = 0.0
                for count in classification_dist.values():
                    if count > 0:
                        p = count / total_components
                        entropy -= p * math.log2(p)
                # Normalize by max possible entropy (log2 of number of types)
                max_entropy = math.log2(len(classification_dist)) if len(classification_dist) > 1 else 1.0
                scorecard['component_type_entropy'] = round(entropy / max_entropy, 6)
            else:
                scorecard['component_type_entropy'] = 0.0
            
            # Tier 2: experimental_risk_score - deterministic composite risk metric
            # Weights: 0.4 unknown + 0.3 low_conf + 0.3 failure (documented, constant)
            low_conf_count = classification.get('low_confidence_count', 0)
            low_conf_ratio = low_conf_count / total_components if total_components > 0 else 0.0
            is_anomalous = classification.get('is_anomalous', False)
            
            experimental_risk = (
                0.4 * unknown_ratio +           # Unknown classification risk
                0.3 * low_conf_ratio +          # Low confidence risk  
                0.3 * scorecard['failure_rate']  # Extraction failure risk
            )
            
            # Anomaly flag adds fixed 0.1 bump with clamping to [0,1]
            if is_anomalous:
                experimental_risk = min(1.0, experimental_risk + 0.1)
            
            scorecard['experimental_risk_score'] = round(experimental_risk, 6)
            
            # Tier 2: ml_confidence_prediction - ML-ready proxy metrics
            # Deterministic computation using Phase 7 classification confidence stats
            confidence_stats = classification.get('confidence_stats', {})
            mean_confidence = confidence_stats.get('mean', 0.5)  # Default to neutral
            std_confidence = confidence_stats.get('std', 0.1)    # Default to low uncertainty
            
            # predicted_accuracy = clamp(mean_confidence - 0.5*unknown_ratio - 0.25*low_conf_ratio, 0, 1)
            predicted_accuracy = max(0.0, min(1.0, 
                mean_confidence - 0.5 * unknown_ratio - 0.25 * low_conf_ratio
            ))
            
            # confidence_interval = clamp(0.10 + std_confidence + 0.50*unknown_ratio, 0, 1)
            confidence_interval = max(0.0, min(1.0,
                0.10 + std_confidence + 0.50 * unknown_ratio
            ))
            
            scorecard['ml_confidence_prediction'] = {
                'predicted_accuracy': round(predicted_accuracy, 6),
                'confidence_interval': round(confidence_interval, 6)
            }
        
        # Write JSON
        json_file = rulebooks_dir / f"{rulebook_id}.json"
        write_json_deterministic(json_file, scorecard)
        files_created.append(json_file)
        
        # Write simple markdown
        md_content = f"""# QA Scorecard: {rulebook_id}

**Source PDF:** {scorecard['source_pdf']}

## Summary Metrics

| Metric | Value |
|--------|-------|
| Total Images | {scorecard['total_images']:,} |
| Success Rate | {scorecard['success_rate']:.1%} |
| Failure Rate | {scorecard['failure_rate']:.1%} |

## Evidence Anchors

- **Analytics Source:** {scorecard['analytics_source']}

---
*Generated by Hephaestus QA Scorecard Generator*
"""
        
        md_file = rulebooks_dir / f"{rulebook_id}.md"
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(md_content)
        files_created.append(md_file)
    
    return files_created

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Phase 8 Decision-Grade QA: Rulebook Scorecards")
    parser.add_argument("--analytics", required=True, help="Path to analytics directory or corpus_analytics.json")
    parser.add_argument("--out", required=True, help="Output directory for QA scorecards")
    parser.add_argument("--schema-version", choices=["8.1", "8.2"], default="8.1", help="QA scorecard schema version")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()
    
    # Determine input file
    analytics_path = Path(args.analytics)
    if analytics_path.is_file() and analytics_path.name == "corpus_analytics.json":
        analytics_file = analytics_path
    elif analytics_path.is_dir():
        analytics_file = analytics_path / "corpus_analytics.json"
        if not analytics_file.exists():
            print(f"Error: corpus_analytics.json not found in {analytics_path}")
            sys.exit(1)
    else:
        print(f"Error: {analytics_path} must be a directory containing corpus_analytics.json or the file itself")
        sys.exit(1)
    
    if args.verbose:
        print(f"Loading analytics from: {analytics_file}")
    
    files = generate_scorecards(analytics_file, args.out, args.schema_version, args.verbose)
    print(f"Generated {len(files)} scorecard files in {args.out}")
    
    if args.verbose:
        for f in files:
            print(f"  {f}")
