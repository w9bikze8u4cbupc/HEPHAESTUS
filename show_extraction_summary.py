#!/usr/bin/env python3
"""Show summary of MOBIUS extraction."""
import json
from pathlib import Path
from collections import Counter

manifest_path = Path("test_output/tm_final_demo/MOBIUS_READY/manifest.json")
manifest = json.load(open(manifest_path))

print("="*60)
print("TERRAFORMING MARS - MOBIUS EXTRACTION SUMMARY")
print("="*60)
print(f"\nTotal components extracted: {manifest['components_extracted']}")
print(f"Extraction mode: {manifest['extraction_mode']}")
print(f"Source: {Path(manifest.get('source_pdf', 'N/A')).name}")

# Size tier distribution
print("\n" + "-"*60)
print("SIZE TIER DISTRIBUTION")
print("-"*60)
tiers = Counter(item['size_tier'] for item in manifest['items'])
for tier, count in sorted(tiers.items()):
    pct = (count / manifest['components_extracted']) * 100
    print(f"  {tier:8s}: {count:2d} components ({pct:5.1f}%)")

# Page distribution
print("\n" + "-"*60)
print("PAGE DISTRIBUTION")
print("-"*60)
pages = Counter(item['page_index'] for item in manifest['items'])
for page, count in sorted(pages.items()):
    print(f"  Page {page:2d}: {count:2d} components")

# Sample components
print("\n" + "-"*60)
print("SAMPLE COMPONENTS (first 5)")
print("-"*60)
for i, item in enumerate(manifest['items'][:5], 1):
    print(f"\n{i}. {item['file_name']}")
    print(f"   Page: {item['page_index']}, Tier: {item['size_tier']}")
    print(f"   Size: {item['width']}x{item['height']} px")
    print(f"   Dimensions: {item['bbox_width_in']:.2f}\" x {item['bbox_height_in']:.2f}\"")
    print(f"   Edge density: {item['edge_density']:.3f}")
    print(f"   Render DPI: {item['render_dpi_used']}")

print("\n" + "="*60)
print(f"✓ All {manifest['components_extracted']} components ready for MOBIUS")
print("="*60)
